# Agent 图——系统设计

> 本文是 [`agent-graphs-design.md`](agent-graphs-design.md) 的中文翻译。以英文原稿为准；如有出入，以原文为准。

状态：阶段 1–3 已发布（引擎 + triage 图工作流，在 `PIKAKA_GRAPH_WORKFLOWS` + dashboard
Graph 标签页后面）。内容工作流（§4.2）和 AutoManus 移植（§5）仍是未来工作。相对本文档的
两处已发布偏差：triage 没有 `search_memory` 扇出节点（完整路径的检索门已经覆盖它——
一个并行预取会双重检索），而且 router 前有一个 `gather` 扇入节点，让它等两条并行分支。
范围：第五个候选支柱——**Graph**——坐在 Harness、Loop、Memory、Eval 旁边。

## 1. 我们加什么、为什么

`pikaka/loop/agent.py` 是一轮 agent：一个 while 循环，模型挑工具直到停下。那覆盖了每一个
对话任务。它表达不了的：

- **并行工作**——本可以同时跑的三次研究调用一次接一次地跑。
- **显式路由**——「如果 X 走这边，否则走那边」埋在 prompt 文本里，不在可检查的结构里。
- **多步管道**——生成 → 检查（几个同时）→ 发布或修改，是有形状的；单个循环轮次把它压平
  成一段长长的转录。

一个**图**让那个形状成为一等公民：节点（一个函数、一次 LLM 调用、或一整轮 `run_loop`）
由边连接，有些条件、有些并行。循环保持聊天默认路径；图按工作流 opt-in。

**与子代理/蜂群的关系**（写进文档）：图是*结构*，不是一种 agent。一个节点*可以*是一个
子代理（一次限定作用域的 `run_loop` 调用），但大多数节点是普通函数或单次 LLM 调用。
没有 agent 间点对点消息、没有蜂群——执行确定性地沿着边走。那个确定性正是重点：你能
追踪它、评估它、在白板上解释它。

## 2. 决策：不用 LangGraph

在仓库内建一个小引擎。用 Pikaka 的话说，原因：

1. **不加新依赖**规则——核心保持 stdlib + anthropic/openai。
2. 教学标杆：「每根支柱单独可读。」一个 ~200 行、你能读懂的引擎，胜过你必须信任的框架。
   和 `loop/agent.py` 同一个套路：把整个机制放在一个文件里展示。
3. 我们的需要是：扇出/扇入、条件边、有界循环、追踪。那是一个拓扑排序加一个线程池——
   不是一个框架的体量。

只有当图变成重心（跨进程的 checkpoint/resume、分布式节点）时才重新考虑。现在不。

## 3. 引擎——`pikaka/graph/`

```
pikaka/graph/
  engine.py       # Graph、Node、run_graph——整个机制，一个文件
  nodes.py        # 节点工厂：llm_node、tool_node、agent_node、router 助手
  workflows/      # 每个真实工作流一个文件（triage.py、content.py、…）
```

### 3.1 核心模型（engine.py）

```python
NodeFn = Callable[[GraphState], dict]      # 读状态，返回要合并的键
RouteFn = Callable[[GraphState], str]      # 读状态，返回下一个节点名

@dataclass
class Node:
    name: str
    fn: NodeFn
    max_visits: int = 1        # 只有坐在一个有意循环里的节点才 >1

class Graph:
    def add_node(self, node: Node) -> None
    def add_edge(self, src: str, dst: str) -> None            # 无条件
    def add_router(self, src: str, route: RouteFn,
                   targets: dict[str, str]) -> None           # 条件
    # 特殊名：START、END

def run_graph(graph: Graph, state: dict,
              observer: Observer | None = None,
              max_steps: int = 25) -> GraphState
```

- **状态是单个 dict**（黑板）。每个节点收到整个状态，返回一组要合并的键。没有带类型的
  channel、没有 reducer——新人在任何点 `print(state)` 都能看懂这次运行。并行分支写
  **不相交的键**（强制执行：合并一个别的活跃分支已写的键会抛异常——冲突是图 bug，不是
  一场静默丢失的竞态）。
- **执行**：DAG 上的就绪队列。一个节点在其所有入边都触发后就绪。就绪节点在
  `ThreadPoolExecutor` 上**并发**跑（stdlib；整个代码库是同步的——asyncio 会为了零收益
  迫使重写工具和模型）。
- **路由器**是状态上的普通 Python 函数——默认不是 LLM 调用。当决策需要模型时，router
  *之前*的节点做 LLM 调用并写比如 `state["score"]`；router 只读它。这让路由可以用 0/1
  评估来测试。
- **循环**：只通过一个显式的、指向后方的 router 边允许，双重守护：每节点 `max_visits`
  和全局 `max_steps`——和 `run_loop` 的自然停止 + max_iterations 是同一个双护栏模式。
- **错误**：节点异常写进 `state["errors"][node]`，并通过一个可选的 `on_error` 目标路由到
  END——呼应 `ToolRegistry.execute` 的「浮出表面而非崩溃」规则。

### 3.2 节点类型（nodes.py）——工厂，不是类

一切都是一个 `NodeFn`；这些助手只构建常见的那几个：

| 工厂 | 包裹 | 典型用途 |
|---|---|---|
| `tool_node(fn, in_keys, out_key)` | 普通函数 | DB 查询、FTS5 搜索、ICS 读取 |
| `llm_node(prompt_template, out_key, small=True)` | 一次模型调用，无工具 | 分类、打分、抽取 |
| `agent_node(system, tools, out_key)` | 一整轮 `run_loop`，带一个**限定作用域的 ToolRegistry** | 一个确实需要多步工具使用的步骤 |
| `human_node(question, out_key)` | 暂停；网关提问，答案恢复 | 审批关卡（阶段 2+） |

`agent_node` 就是子代理的故事：同一个循环、同样的追踪，只是一个更窄的工具子集和它自己
的工作记忆。图不替换循环——它安排对循环的调用。

### 3.3 可观测性

`run_graph` 采用与 `run_loop` **相同的 `Observer` 签名**，并发出：`graph_start`、
`node_start`、`node_end`（带时长 + 写入的状态键）、`route`（router 名 + 选中的目标）、
`graph_end`。在 `agent_node` 内部，内层循环的 `llm`/`tool` 事件带着 `node=` 字段穿过。
trace 落进同一份 JSONL → dashboard 以后能得到图时间线视图，而不用动引擎。

### 3.4 评估

- `evals/deterministic/test_graph_engine.py`——纯函数节点，无 LLM：拓扑顺序、扇出并行跑
  （断言墙钟 < 总和）、扇入等所有分支、router 选对边、不相交键强制抛异常、循环停在
  max_visits、错误路径路由到 on_error、max_steps 硬停止。
- 每个已发布工作流得到自己的确定性评估，LLM 节点被 stub（注入假的 `NodeFn`），加上对
  真实端到端输出做裁判评估，用在打分模糊（内容质量）的地方。

关卡规则不变：任何 push 前 `make gate`；线上 bug → 修复 + 回归用例。

## 4. Pikaka 里的工作流（用例 2 和 3）

### 4.1 `workflows/triage.py`——入站消息分流（阶段 2）

对经 telegram/discord 网关到达的消息：在主循环为一个消息花一个大模型轮次之前，快速、
并行地决定它需要什么。

```
START
  ├─ classify_intent   (llm_node, 小模型: question/task/urgent/social)
  ├─ search_memory     (tool_node: FTS5 语义存储)
  └─ check_calendar    (tool_node: calendar.ics 里今天的事件)
        ↓ (扇入)
  route(intent, urgency):
      social/trivial → quick_reply   (llm_node, 小模型)             → END
      task/question  → full_agent    (agent_node: 普通循环，
                                      预载记忆+日历上下文)            → END
      urgent         → notify_now    (tool_node: send_message)       → END
```

相对今天的价值：三次上下文抓取同时跑，琐碎消息永远不碰大模型。这是把检索门的想法从一个
门推广成一个结构。

### 4.2 `workflows/content.py`——草稿 → 并行检查 → 发布/修改（阶段 3）

```
START → draft (agent_node: 写作工具)
  ├─ check_tone       (llm_node, 小)
  ├─ check_facts      (agent_node: 仅搜索工具)
  └─ check_length     (tool_node: 纯函数)
        ↓ (扇入) → aggregate (tool_node: 分数最小值 + 收集的反馈)
  route(score):
      pass            → save_note → END
      fixable         → revise (llm_node, 拿到反馈) → 回到检查   [max_visits=2]
      unsalvageable   → human_node → END
```

在一个低风险的个人任务里展示有界循环和人工关卡——引擎两个最危险的特征。

## 5. AutoManus——线索资格认定（用例 1）

不同的仓库，不同的约束。这里设计，单独构建。

- **在哪**：FastAPI 后端（`app-backend-AutoManus`），**不是** Next.js 前端——「AI agent 住
  在后端」规则。本会话没有 clone 后端仓库，所以这一节是一份规格。
- **怎么做**：把 ~200 行的引擎模式移植进 `ai_utils/graph/`（复制，别共享一个包——仓库保持
  独立；引擎小到 fork 比共享依赖更便宜）。
- **端点**：`POST /api/v1/leads/qualify`（verify_token + 通常的业务作用域）。

```
START (contact_id, business_id)
  ├─ fetch_history     (Supabase: whatsapp_messages 按 agent_id 过滤, deals)
  ├─ research_company  (LLM + web/公司补充信息)
  └─ recent_activity   (最后接触的新近度、渠道、响应延迟)
        ↓ (扇入) → score (LLM 节点 → {score, reasons})
  route(score):
      hot  (≥0.8)      → draft_followup (现有跟进计划机制) → END
      warm (0.5–0.8)   → add_to_nurture → END
      cold (<0.5)      → tag_and_skip   → END
```

- **扣费**：在 LLM 节点之前通过信用服务扣费，按仓库约定。
- **前端**：一个 hook（`useLeadQualification`）调端点；结果渲染在 deal 上——前端完全没有
  图引擎。
- **输出契约**：`{score, band, reasons[], action_taken, drafted_message?}`，这样 UI 和每日
  「该追谁」简报消费同一个形状。

## 6. 分阶段

| 阶段 | 交付物 | 证明 |
|---|---|---|
| 1 | `graph/engine.py` + `nodes.py` + 完整确定性评估套件 | 机制，零 LLM 花费 |
| 2 | `workflows/triage.py` 接在开关后面 + 追踪事件 | 在真实助手上产生真实价值 |
| 3 | `workflows/content.py` | 循环 + 人工关卡 |
| 4 | AutoManus 后端移植 + `/leads/qualify` | 模式可迁移 |

每个阶段一个 PR（topic 分支 → 关卡 → squash-merge），可单独发布。

## 7. 已做的决策（在阶段 1 前标记分歧）

1. **不用 LangGraph**——仓库内引擎，仅 stdlib。
2. **线程，不是 asyncio**——匹配同步代码库；并行是 I/O 密集（API 调用），所以 GIL 无关。
3. **带不相交键写入的 dict 黑板**——而非带类型状态/reducer；可读性赢，冲突大声失败。
4. **路由器是代码，不是 LLM 调用**——模型产出状态，函数读它。
5. **图是循环周围的 opt-in 结构**——`run_loop` 不动；`agent_node` 组合它。循环支柱的文件
   不改变。
6. **把引擎复制进 AutoManus**，而不是提取共享库。
