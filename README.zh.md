# pikaka-agent

Pikaka 是一个 **local-first（本地优先）的个人助理**。它把每一个「严肃的 agent」背后的
四大块拆开、摊平、写清楚：

- **Harness（网关）** —— 多入口、一个大脑
- **Loop（循环）** —— 模型和工具之间怎么一轮轮转
- **Memory（记忆）** —— 怎么记住你、又在对的时候想起来
- **Eval / LLM-Ops（评估）** —— 怎么客观知道它好不好用

没有框架把有意思的部分藏起来。核心循环就是一段普通 Python，你可以单步调试它。

- **本地优先。** 你的记忆就是一个 SQLite 文件。打开它、读它、它是你的。
- **记忆是主角。** 语义 + 情景 + 程序三种记忆——外加一个「检索门」判断*要不要*记、
  一个「巩固」决定*留什么*。
- **循环极简。** 一个手写的 Python `while` 循环，没有黑箱控制流。
- **看着它思考。** 一个本地 dashboard 把每条消息流经系统的过程点亮给你看。
- **评估内建。** 确定性测试和 LLM 裁判并排存在，外加一道发布门禁。

> 系统设计白板见 [docs/architecture.md](docs/architecture.md)，每个框都映射到具体代码文件。

---

## 一句话解释「这是什么」

它是**一个你拥有的代码库**，不是「一个你使用的产品」。ChatGPT / Claude Desktop 是产品，
你只能*用*；pikaka 是代码，你拥有循环、记忆 schema、检索门、评估体系，全部可读、可改。
看懂这个仓库，你就看懂了那些产品在底层到底做了什么。

---

## 快速开始

只是想跑起来：

```bash
pip install pikaka-agent
pikaka                                    # 在终端里和它对话
pikaka dashboard                          # …或者打开浏览器驾驶舱 → localhost:7777
```

第一次运行会告诉你要配哪个 key。想**读代码**（这个仓库的意义所在）或参与开发，clone 下来：

```bash
git clone <仓库地址> && cd pikaka-agent
uv venv && uv pip install -e .           # 建环境 + 安装 `pikaka` 命令
cp .env.example .env                     # 选一个模型供应商，粘贴一个 key
uv run pikaka                             # 终端对话
uv run pikaka dashboard                   # 浏览器驾驶舱 → localhost:7777
```

**用你已经付费的模型。** Anthropic（默认）、OpenAI、Gemini、DeepSeek、MiniMax、Kimi、GLM、
OpenRouter（一个 key，几百个托管模型）——设 `PIKAKA_PROVIDER=`，粘贴 key，完事。循环里只有
一种方言，一个约 60 行的适配器（`pikaka/loop/models.py`）处理其余。

---

## 看着系统跑起来 —— dashboard

```bash
pikaka dashboard          # 起一个本地服务器 → http://localhost:7777
```

一个你自己拥有的小 web 服务器（`127.0.0.1`，不联网）。浏览器只是 UI——跑每一轮的就是这个
进程本身。这是**最快理解整个系统**的方式。

每个标签页对应一块（支柱），链接到真实文件：

| 标签页       | 你看到什么                                                                   |
| ------------ | ---------------------------------------------------------------------------- |
| **Overview** | 成本、延迟、检索门「检索/跳过」分布、可点击的架构图                          |
| **Gateway**  | 一条跨所有频道的对话，每条消息标注来源（dashboard / telegram / voice / cli） |
| **Loop**     | 每一轮的门决策、工具调用、token、成本                                        |
| **Graph**    | 图工作流：实时 triage 拓扑（从引擎自身画出）+ 每轮走的是哪条路               |
| **Memory**   | 每个记忆支柱的子标签——语义事实、情景、可编辑技能 + SOUL、巩固                |
| **Tools**    | agent 可用的工具（按来源分组）、结果、MCP 连接器                             |
| **Data**     | 一个实时 SQLite 浏览器：每表标签、schema、只读 SQL 控制台（查 `state.db`）   |
| **Ops**      | 评估结论 + 历史、门决策、最慢的轮次、内联 JSONL trace                        |

---

## 核心：循环 —— 推理 → 行动 → 重复

是的，有一个真正的 agent 循环，而且是普通 Python（`pikaka/loop/agent.py`），
没有 LangGraph、没有隐藏的控制流：

```
while not done:
    response = llm(messages, tools)      # 推理
    if response 想要工具:
        results = run(tool_calls)        # 行动
        messages += results              # 观察
    else:
        done                             # 回复人类
```

两道护栏结束每一轮：模型不再要求工具（自然结束），或撞上 `max_iterations`（硬停——永远
不会无限转圈）。这就是「循环工程」：退出条件、工具往返、把结果喂回工作记忆。

**多工具循环（最精彩的部分）。** 一个工具是一条循环；*串联*多个工具才是循环工程真正发力
的地方。试试：

> _「搜索还有哪些世界杯比赛没踢，每一场都加进我的日历。」_

agent 在两个工具之间循环：`search_web` 读网页 → 推理 → 对每一场比赛调用一次
`create_event`——一轮里迭代好几次。

---

## 记忆 —— 三种支柱 + 一个门 + 一个巩固器

pikaka 的记忆不是黑箱，分三层：

| 支柱                       | 存什么                           | 例子                    |
| -------------------------- | -------------------------------- | ----------------------- |
| **语义记忆（semantic）**   | 关于你、你朋友、你项目的持久事实 | 「Alex 喜欢早上开会」   |
| **情景记忆（episodic）**   | 带日期、发生过的事               | 「上周和 Raj 约了网球」 |
| **程序记忆（procedural）** | 怎么做（SKILL.md）               | 「每周简报的流程」      |

**检索门（retrieval gate）**：大多数 agent 每轮都去撞记忆库——慢，而且更糟的是**无关记忆
会带偏回答**。这里先用一个便宜模型回答一个问题：_这条消息到底需不需要记忆？_

```
you > 2+2 是多少？
  gate · skip —— 纯数学，跳过记忆
you > 我什么时候和 Alex 见面？
  gate · retrieve —— 引用了用户的计划，去查
```

**巩固器（consolidation）**：不是每条消息都当场提炼，而是「聊够 N 轮」才把对话蒸馏成
事实和情景。异步于回复路径，且**失败不丢数据**（聊天日志保持未巩固状态）。

---

## 两个「主角时刻」

**1. 检索门。** 见上——把「要不要记」从「记什么」里分离出来。

**2. 确定性评估 vs LLM 裁判。** *「它有没有创建正确的日历事件？」*是一个单元测试——0 或 1，
不用模型评判（`make eval`）。*「回复有没有用？」*是一个带阈值的打分（`make eval-judge`）。
把两者搞混是评估里最常见的错误；这里它们是两套可以 diff 的独立套件。`make gate` 把两者
一起作为发布门禁跑。

---

## 评估、追踪 & 抓 bug

三条命令，两类评估——系统的 LLM-Ops 半边：

```bash
make eval          # 确定性：「该调的工具调了吗？」——0 或 1，不用模型评判
make eval-judge    # LLM 裁判：「回复有没有用？」——打分百分比，需要 key
make gate          # 发布门禁：确定性必须 100% 过，裁判必须过阈值
```

确定性测试是 `evals/deterministic/` 里普通 pytest；裁判测试用 `evals/judge/` 里的 DeepEval。
**把它们分开是全部要点**——混淆「做了没」（单元测试）和「做得好不好」（打分判断）是最常见
的评估错误。

**花费是永久的**：每次 LLM 调用的 token 追加到 `.pikaka/usage.jsonl`——一个只追加的账本，
demo 重置也抹不掉。**追踪永远开着**：每轮把可读行追加到 `.pikaka/traces/<date>.jsonl`
（零配置）——trace 就是「按顺序发生了什么」。

> 更详细的评估讲解见 [docs/benchmarks.md](docs/benchmarks.md)。

---

## 图工作流 —— 当一轮需要「形状」时

循环是一次 agent 轮次：模型挑工具直到停，覆盖聊天场景。但有些工作有**形状**——可以
*同时*跑的步骤，以及显式的「如果这样，走这里」路由。**图工作流**把形状变成一等公民。

它是循环支柱的**扩展，不是替代**：`loop/agent.py` 一行没改——图在它周围*安排调用、调度它*。
而且依然无框架：整个引擎是一个可读文件（`pikaka/graph/engine.py`）。

**随仓库发布的例子：triage。** 设 `PIKAKA_GRAPH_WORKFLOWS=1`，每条消息先进 triage 图。
一个小模型在**并行加载今日日历的同时**给消息分类；「谢谢！」走小模型快速回复，从不吵醒
大模型；「周六约个游泳」路由进和以前一模一样的循环（作为一个节点跑）。**任何一处失败
——分类器、引擎、任何地方——都 fail-open 回退到普通循环**，所以这个开关只会省时间省 token。

> 深入讲见 [docs/loop-vs-graph.md](docs/loop-vs-graph.md)。

---

## 连接你的生活

语音、Telegram、Apple 日历和邮件、Google 日历、MCP 服务器——每一个都是 opt-in，各自在
自己的 extra 后面，都不改循环。全部配置见 [docs/integrations.md](docs/integrations.md)。

---

## 它管理自己的记忆

agent 有让自己保持有用的工具——没有黑箱：

- **manage_memory** —— 当你说某条事实错了，纠正或忘掉它。
- **update_soul** —— 存下你给它的一个长期偏好（存进 `SOUL.md`）。
- **create_skill** —— 当你教它一个可重复的流程，它提议存成技能。

你也可以在 dashboard 的 Memory 标签页手工编辑任何这些（编辑/删除事实、重写 `SOUL.md`），
或在 Settings 里切换 provider/模型、粘贴 key（BYOK，存在本地 `.env`，绝不发给浏览器）。

---

## 每条命令

| 命令               | 做什么                                      |
| ------------------ | ------------------------------------------- |
| `pikaka`           | 终端对话                                    |
| `pikaka dashboard` | localhost:7777 的实时驾驶舱                 |
| `pikaka voice`     | 语音对话（免提「pikaka pikaka」或按键说话） |
| `pikaka telegram`  | 用手机给它发消息                            |
| `pikaka brief`     | 从日历 + 邮件 + 记忆做晨间简报              |
| `make trace`       | 深 trace 瀑布图（Phoenix）localhost:6006    |
| `make eval`        | 确定性评估（0/1，无裁判）                   |
| `make eval-judge`  | LLM 裁判评估（打分 %）                      |
| `make gate`        | 发布门禁——两套评估都必须过                  |

---

## 子代理 —— 委托编程任务给 pi

`delegate_task` 把编程任务交给 [pi](https://github.com/earendil-works/pi)（Mario Zechner 的
极简开源编程 agent），通过它的无头打印模式（`pi -p "task"`）。Pikaka 保持编排者角色（记忆、
上下文、评估）；pi 是专家承包商（read/bash/edit/write）。

> 分工哲学一句话：**「记忆和评估归编排者；工具归专家。」** 见
> [docs/pi-agent.md](docs/pi-agent.md)。

---

## 升级路径（当你超出默认值时）

| 默认（零配置）            | 升级                       | 怎么切                                                  |
| ------------------------- | -------------------------- | ------------------------------------------------------- |
| SQLite FTS5 关键词记忆    | Supabase pgvector 语义搜索 | `PIKAKA_SEMANTIC_STORE=supabase`                        |
| Mock 日历（ICS + SQLite） | Apple / Google 日历        | `PIKAKA_APPLE_CALENDAR=1` 或 `PIKAKA_GOOGLE_CALENDAR=1` |
| 手建记忆支柱              | mem0 / Zep / LangMem       | `pip install -e '.[arena]'` 后在 Arena 里赛跑           |

每一层都是「一个无聊但可靠的默认值 + 一条记录在案的升级路径」——默认值保证 clone 下来
零配置就能跑，升级路径保证你想认真用时有路可走。

---

## 数据存在哪

全部是本地普通文件，没有数据库服务器：

- **`./.pikaka/state.db`** —— 一个 SQLite 文件，装下所有记忆（`facts` / `episodes` /
  `chat_log` / `calendar_events`），配 FTS5 关键词搜索。
- **`./.pikaka/usage.jsonl`** —— 永久花费账本。
- **`./.pikaka/traces/`** —— 每轮的追踪记录。
- **`./.pikaka/MEMORY.md`** —— 人类可读的记忆镜像。

自己打开随时看：`sqlite3 .pikaka/state.db '.tables'`。

---

## 许可证

MIT —— 见 [LICENSE](LICENSE)。本项目基于
[ShenSeanChen/waku-agent](https://github.com/ShenSeanChen/waku-agent) 二次开发，
原作者署名保留。
