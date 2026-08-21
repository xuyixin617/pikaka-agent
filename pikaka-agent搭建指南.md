# pikaka-agent 项目搭建指南

> 作者仓库：[ShenSeanChen/waku-agent](https://github.com/ShenSeanChen/waku-agent)（本项目为其改名 + LangGraph 版）
> 你的本地位置：`D:\pikaka-agent`（已跑通）
> 模型：智谱 GLM（`glm-5.2` + `glm-5-turbo`）

---

## 一、这个项目是什么

**Pikaka** 是一个「本地优先的个人助手」，但它本质是一个**教学仓库**——作者（Sean，YouTube 频道「Sean's AI Stories」）用它来演示一个**真正的 Agent** 背后到底有什么。

它把 Agent 拆成四个支柱，每一根支柱都能独立读懂：

| 支柱 | 英文 | 解决什么问题 | 对应代码 |
|---|---|---|---|
| 1. 网关（Harness） | Harness | Agent 从哪接收消息、把回复送到哪 | `pikaka/gateway/` |
| 2. 循环（Loop） | Loop | 大脑怎么「思考→行动→再思考」直到完成 | `pikaka/loop/agent.py` |
| 3. 记忆（Memory） | Memory | 怎么记住事实、对话、技能 | `pikaka/memory/` |
| 4. 评测（Eval / LLM-Ops） | Eval | 怎么证明它「做对了」 | `evals/` + `pikaka/ops/` |

**它和 ChatGPT / Claude Desktop 的区别**：那些是「产品」，你只能*使用*；Pikaka 是「代码」，你*拥有*它——循环、记忆表结构、检索门、评测框架，全都能读、能改。读懂这个仓库，你就懂了那些产品底层在做什么。

对比其他开源助手（OpenClaw、Hermes）：**同样的架构，1/100 的代码量**。作者的口号是「一个下午能读完的、诚实的代码」。

---

## 二、核心架构（一张图看懂）

```
                    ┌─────────────────────────────────┐
                    │  网关 Gateway（cli/语音/Telegram）│  ← 只负责搬运文字
                    └───────────────┬─────────────────┘
                                    │ 用户消息
                    ┌───────────────▼─────────────────┐
                    │  工作记忆 Working Memory          │
                    │  = SOUL.md + 记忆 + 聊天历史       │  ← session.py 每次组装
                    └───────────────┬─────────────────┘
                                    │
   ┌────────────────┐   ┌──────────▼──────────┐
   │  记忆 Memory    │◄──│  循环 The Loop        │  ← agent.py 约 95 行
   │  state.db      │   │  思考→调工具→观察→重复 │
   │  SQLite+FTS5   │   └──────────┬──────────┘
   └────────────────┘              │ 回复
                    ┌──────────────▼─────────────────┐
                    │  评测/可观测 Ops                 │
                    │  trace → eval → gate            │
                    └────────────────────────────────┘
```

**数据流转（一次完整对话）：**

1. 你在 CLI / 网页输入一句话 → 网关收到
2. `session.py` 组装「工作记忆」= 人设（SOUL.md）+ 当前时间 + **按需检索的记忆** + 聊天历史
3. `loop/agent.py` 把工作记忆发给 LLM，LLM 决定：直接回复？还是调用工具？
4. 如果要调工具（比如 `create_event`），就执行工具、把结果喂回 LLM，继续循环
5. LLM 不再要工具了 → 回复你，结束
6. 这轮对话被存进 `state.db`，每 N 轮后「整合」成长期事实

---

## 三、搭建步骤（你的环境实录）

### 1. 下载

```bash
git clone https://github.com/ShenSeanChen/waku-agent.git
cd pikaka-agent
```

### 2. 配置 `.env`（关键）

复制模板，填模型密钥：

```bash
copy .env.example .env
```

你用的是**智谱 GLM**，`.env` 里改这三处：

```ini
PIKAKA_PROVIDER=glm
ZHIPU_API_KEY=你的智谱key
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/anthropic
```

> **要点**：pikaka 的 glm 走的是智谱的 **Anthropic 兼容端点**（`/api/anthropic`），不是你之前 `zhipuai` SDK 用的 `/api/paas/v4`。但 key 是同一个智谱 key。
>
> ⚠️ 这个端点**只支持 glm-4.5 及以上**（4.5 / 4.6 / 4.7 / glm-5 / glm-5-turbo / 5.1 / 5.2 / 5.3），**没有 glm-4**。pikaka 默认模型 `glm-5.2` + `glm-5-turbo` 正好命中，无需额外配置。

### 3. 安装依赖

```bash
uv venv                    # 创建虚拟环境
uv pip install -e .        # editable 安装（改代码即时生效）
```

核心依赖非常少：`anthropic`、`openai`、`python-dotenv`、`rich`。

### 4. ⚠️ 中文路径的坑（你踩过的）

你的 Windows 用户名是中文「徐奕欣」，只要项目在 `C:\Users\徐奕欣\...`，`editable install` 生成的 `.pth` 文件就指向含中文的路径，Python 启动时直接崩：

```
UnicodeDecodeError: 'gbk' codec can't decode byte 0xa5
```

实测 `-X utf8` 和 `PYTHONUTF8=1` **都救不了**。**唯一解法：把项目放到无中文路径**。

所以项目现在在 **`D:\pikaka-agent`**。

> **经验法则**：以后凡是需要 `pip install -e .` 的项目，一律放无中文路径（如 `D:\`）；直接 `python 脚本.py` 跑的项目不受影响，可继续放中文路径。

---

## 四、怎么运行

```bash
cd D:\pikaka-agent

# 方式一：终端聊天（默认）
uv run pikaka

# 方式二：浏览器驾驶舱（推荐，可视化看 Agent 运行）
uv run pikaka dashboard        # 打开 http://localhost:7777

# 其他入口
uv run pikaka voice            # 语音（需 [voice] 扩展）
uv run pikaka telegram         # Telegram 机器人（需 TELEGRAM_BOT_TOKEN）
uv run pikaka brief            # 晨间简报
uv run pikaka gather           # 图工作流版简报
```

`make` 命令是等价别名（`make run` = `python -m pikaka`）。

**第一次可以试这几句**（看四大支柱各自亮起来）：

| 试这句 | 演示什么 |
|---|---|
| *"Schedule a tennis game with Raj this Saturday at 8am"* | Loop 调 `create_event` |
| *"What's on my calendar today?"* | 读日程 `list_events` |
| *"what's 12 × 8?"* 然后 *"When am I meeting Alex?"* | 检索门（retrieve vs skip） |
| *"Remember that Raj prefers evening games"* | 记忆自管理 `save_note` |

---

## 五、核心机制深入（详细了解的重点）

### 5.1 The Loop（`loop/agent.py`，约 95 行）

所有 Agent 框架本质都是这个 `while` 循环：

```python
while not done:
    response = llm(messages, tools)   # 思考：让 LLM 决定下一步
    if response 要调工具:
        results = run(tool_calls)     # 行动：执行工具
        messages += results           # 观察：结果喂回工作记忆
    else:
        done                          # 结束：回复人类
```

**两个退出条件（护栏）**：
1. 模型不再要工具 → 自然结束，返回回复
2. 达到 `max_iterations`（默认 10）→ 硬停，绝不无限循环

**多工具链式调用**是 loop 的精彩处。一句 *"搜索世界杯剩余比赛并加入日历"* 会让 Agent 在 `search_web` 和 `create_event` 之间循环多次（`iter 4`、`iter 5`…），这就是「loop 工程」。

### 5.2 Working Memory（`runtime/session.py`）

每个回合都会**从零组装**「工作记忆」，用完就扔。它 = 四样东西：

```
系统提示词 SOUL.md          ← Pikaka 是谁（人设）
+ 当前时间                    ← 让它知道「30分钟后」是什么时候
+ 按需检索的长期记忆           ← 经过检索门筛选
+ 当前聊天历史                 ← 这一轮对话
+ 用户新消息
```

- `SOUL.md` 是**可编辑的人设文件**，首次运行自动创建在 `.pikaka/SOUL.md`，改它 = 改你的 Pikaka。
- 只保留最近 `PIKAKA_HISTORY_TURNS`（默认 12）轮进工作记忆，防止长对话把上下文撑爆。

### 5.3 检索门 Retrieval Gate（**Hero Moment #1**）

大多数 Agent 每轮都去查记忆库——**又慢又会把无关记忆带偏答案**。

Pikaka 的做法：先用**便宜的小模型**回答一个问题——*「这条消息需要记忆吗？」*

```
你 > what's 2+2?
  gate · skip      —— 纯数学，跳过检索
你 > when am I meeting Alex?
  gate · retrieve  —— 引用了用户计划，去检索
```

代价是几百 token 的小模型调用，收益是「只在需要时检索」。而且**失败时 fail-open**（门自己出错就检索，宁可给旧记忆也不丢记忆）。

### 5.4 记忆三支柱（`pikaka/memory/`）

记忆分三种，存 SQLite（`state.db`，SQLite + FTS5 全文搜索）：

| 支柱 | 存什么 | 例子 | 存储 |
|---|---|---|---|
| **语义记忆** Semantic | 持久事实、档案 | 「Raj 喜欢晚上打球」 | `facts` 表 + FTS5 |
| **情景记忆** Episodic | 带日期的对话/事件 | 「昨天约了 Alex」 | `episodes` 表 + FTS5 |
| **程序记忆** Procedural | 「怎么做」的技能 | 可复用的工作流 | `skills/*.md`（SKILL.md） |

- 记忆是**可查询的数据库** + **可读的镜像**：每轮后会把 `facts`/`episodes` 重新生成一份 `.pikaka/MEMORY.md` 方便人看。
- **整合 Consolidation**：每 `PIKAKA_CONSOLIDATE_EVERY`（默认 6）轮对话，把聊天蒸馏成 durable facts。
- Agent 有记忆自管理工具：`manage_memory`（更正/遗忘事实）、`update_soul`（存偏好）、`create_skill`（存技能）。

### 5.5 工具清单（`pikaka/tools/`）

核心工具（默认注册）：

| 工具 | 作用 |
|---|---|
| `create_event` | 创建日程（写本地日历 + ICS） |
| `list_events` | 读日程 |
| `search_web` | 网页搜索（免费走 DuckDuckGo，或用 Tavily） |
| `save_note` | 存一条事实到记忆 |
| `send_message` | 发消息（draft 到本地 outbox） |
| `manage_memory` | 更正 / 遗忘事实 |
| `update_soul` | 保存长期偏好到 SOUL.md |
| `create_skill` | 保存可复用工作流 |
| `github_read` | 只读 PR / issue（需 `gh` 登录） |
| `delegate_task` | 派编码任务给 pi 子代理（实验性，`PIKAKA_EXPERIMENTAL=1`） |

### 5.6 两类评测（`evals/`）——**Hero Moment #2**

Agent 最常见的评测错误是把两类问题混为一谈：

```bash
make eval        # 确定性评测：「做对了没？」——0 或 1，纯 pytest，无模型打分
make eval-judge  # LLM 当裁判：「回答有用吗？」——打分百分比，需 key
make gate        # 发布门：两类都得过
```

- **确定性**（`evals/deterministic/`）：像单元测试，比如「是否创建了正确的日历事件」。
- **裁判**（`evals/judge/`）：用 DeepEval，比如「回复是否有帮助」，设阈值打分。

### 5.7 可观测性（`pikaka/ops/`）

- **Tracing 永远开启**：每轮追加到 `.pikaka/traces/<日期>.jsonl`，就是「按顺序发生了什么」。
- **Spend 永久记账**：每次 LLM 调用的 token 追加到 `.pikaka/usage.jsonl`（只增不减的账本），dashboard 的 Ops 页显示历史总成本。
- **Dashboard**：localhost:7777，一个 tab 一根支柱，能看 loop、memory、tools、数据库、评测的实时状态。

---

## 六、`.env` 配置速查

| 变量 | 含义 | 默认 | 你的值 |
|---|---|---|---|
| `PIKAKA_PROVIDER` | 模型供应商 | `anthropic` | `glm` |
| `ZHIPU_API_KEY` | 智谱 key | — | 已填 |
| `ZHIPU_BASE_URL` | 智谱端点 | `api.z.ai`（国际） | `open.bigmodel.cn`（国内） |
| `PIKAKA_MODEL` | 主模型 | `glm-5.2` | 可留空 |
| `PIKAKA_SMALL_MODEL` | 小模型（gate/总结用） | `glm-5-turbo` | 可留空 |
| `PIKAKA_HOME` | 状态目录（state.db 等） | `.pikaka` | 默认 |
| `PIKAKA_MAX_ITERATIONS` | 循环硬停上限 | `10` | 默认 |
| `PIKAKA_MAX_TOKENS` | 单次输出上限 | `8192` | 默认 |
| `PIKAKA_HISTORY_TURNS` | 工作记忆保留轮数 | `12` | 默认 |
| `PIKAKA_CONSOLIDATE_EVERY` | 每 N 轮整合记忆 | `6` | 默认 |
| `PIKAKA_GRAPH_WORKFLOWS` | 开启图工作流 | 关 | `1` 开启 |
| `PIKAKA_EXPERIMENTAL` | 实验工具 | 关 | `1` 开启 |
| `TAVILY_API_KEY` | 网页搜索（可选） | — | 可不填 |

> 支持 11 个供应商：`anthropic` / `openai` / `openrouter` / `gemini` / `deepseek` / `minimax` / `kimi` / `glm` / `xai` / `opencode_zen` / `opencode_go`。换供应商只需改 `PIKAKA_PROVIDER` + 填对应 key。

---

## 七、踩坑记录

1. **中文路径崩溃**（最关键）：Windows 中文用户名 + `pip install -e` → `.pth` 指向中文路径 → GBK 解码崩溃。解法：项目放无中文路径（`D:\pikaka-agent`）。
2. **智谱 Anthropic 端点无 glm-4**：`/api/anthropic` 只支持 glm-4.5+，glm-4 只在 `/api/paas/v4`。pikaka 默认 glm-5.2 正好可用。
3. **不填 key 直接跑**：会报 404/401（作者提交记录里写过 `fix: the openai default 404s`）。务必先配 `.env`。
4. **CLI 输出乱码**：Windows 终端 GBK 显示 emoji 时出现 `��`，不影响功能。

---

## 八、学习路径建议（结合你的课程）

你之前做的是「多智能体 + LangGraph + MCP 运维」，Pikaka 恰好补齐了**底层原理**这一块：

1. **先跑起来**：`uv run pikaka dashboard`，用第五节那几句「试这句」看四大支柱。
2. **读循环**：`pikaka/loop/agent.py` 只有 95 行，先读懂它——这是所有 Agent 的核心。
3. **读检索门**：`pikaka/memory/retrieval_gate.py`，理解「为什么不要每轮都检索」。
4. **对比 LangGraph**：Pikaka 的 loop 是「无框架的 while 循环」，而你课程里的 LangGraph 是「显式图编排」——两者是互补的（Pikaka 里也有 `pikaka/graph/` 讲「图工作流」，fail-open 到 loop）。
5. **读评测**：`evals/deterministic/` vs `evals/judge/`，理解「做对了没」和「回答好不好」为什么不能混。

**关键认知**：Pikaka 作者强调「清晰、诚实、可读」——每个支柱独立可读，不加复杂度。这是你在做生产级 Agent 时最该保留的品质。
