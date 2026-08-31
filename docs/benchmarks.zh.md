# 模型对比 —— Pikaka 的基准测试套件

> 本文是 [`benchmarks.md`](benchmarks.md) 的中文翻译。以英文原稿为准；如有出入，以原文为准。

Pikaka 如何对比模型、每个测试测什么、以及如何看懂结果。
这是 **Eval / LLM-Ops** 支柱的「斜向」用法：不是给单个 agent 随时间打分，而是把**同一个任务喂给多个大脑同时跑**，然后给**结果**打分——不只是看账单。

> **诚实的定位。** Compare 竞技场（dashboard 的 `#compare`）和
> `scripts/shootout.py` 衡量的都是在**同一套共享骨架**上的实时任务求解。
> 它们**不会**复现标准排行榜（SWE-bench、τ-bench、Terminal-Bench、GPQA）——
> 那些需要各自的数据集和官方骨架。各模型已发布的排行榜数字放在
> [§6](#6-已发布的基准参考)。我们的套件是**本地、可复现的镜像**：在隔离沙盒里
> 看每个模型做同一份真实的助手工作，然后给「到底做没做成」打分。

---

## 0. 给视频用的 —— 评估与打分的叙事线

本文档兼作分镜清单。视频的主线是**评估与打分**，不是「模型 X 最好」：重点是
*你如何诚实地、有凭据地做出判断*。你会在镜头前跑的测试清单在
[§3](#3-套件的各个板块)——那就是套件，按板块分组，方便你一次拍一个板块。建议的叙事线：

1. **天真的记分板（铺垫）。** 展示竞技场让 11 个模型在同一个 prompt 上赛跑。
   速度、token、成本。然后转折：*「这只能告诉我谁又便宜又快——不能告诉我谁
   真正把活干完了。」*（正是这个缺口催生了整个视频。）
2. **打分，一个轴一个轴地来。** 引入四个轴（[§1](#1-四个轴)）：速度、成本、
   **完成度（Completion）**（工具真的触发了没 / 事件真的生成了没）、**质量
   （Quality）**（K3 当中立裁判）。强调完成度是*确定性*的——没有玄学，这就是
   τ-bench/SWE-bench 的思路在本地做一遍。
3. **硬案例（便宜模型翻车的地方）。** 跑 Battery A 的四个硬案例
   （[§3.A](#a-agentic-工具调用——助手真正的活)）——过度主动、数量精确、完整性、
   状态感知。这是最值钱的段落：一个模型答得流利却*仍然通不过清单检查*。
4. **K3 当裁判。** K3 给全场的转录文本打分，包括给它自己，并大声说出来
   （[§5](#5-裁判——一个可切换的中立仲裁者)）。赞助商的模型来当裁判是个钩子——
   诚实地摆出来，而不是藏着。
5. **揭晓——成本 vs 质量。** 帕累托散点图（[§1](#1-四个轴)）：「opus 的价格是
   gemini-flash 的 20 倍——它好 20 倍吗？」答案是一张*图*，而且它就是缩略图。
6. **（可选）编程回合。** 把一个真实的编程任务委托给 pi，跨模型跑
   （[§3.B](#b-编程——跨模型，通过-pi)）——用测试是否通过来打分。

下面全部是这条叙事线所引用的参考。

---

## 1. 四个轴

每一列比赛产生四个独立的信号。成本/速度很容易读；后两个才是收据显示不出来的
「到底有没有做成」。

| 轴 | 回答的问题 | 来源 | 计算成本 |
|------|-----------------|---------------------|-----------------|
| **速度（Speed）** | 多久跑完 | 循环里的 `latency_ms` | 免费 |
| **成本（Cost）** | 这次尝试花了多少钱 | tokens × 各模型价格表 | 免费 |
| **完成度（Completion）** | *活干完了吗？* | 对工具调用 + 沙盒状态做确定性检查，对照任务的预期结果 | 免费 |
| **质量（Quality）** | *答得有多好？* | LLM 当裁判（K3 当中立仲裁者）给转录文本打 0–10 分 + 一句理由 | 每列 1 次裁判调用 |

竞技场要讲的故事是：**把成本对照完成度/质量画出来。**「Opus 的价格是
gemini-flash 的 20 倍——它完成任务就好 20 倍吗？」两个完成度相同、成本却差 20 倍的
模型，就是整个视频的重点。

---

## 2. 一个任务怎么打分（契约）

Battery 的用例放在 `evals/dataset.jsonl` 里，一行一个 JSON 对象。同一个文件驱动三个
消费者，所以一个写好的用例在任何地方都以相同方式打分：

- 确定性评估层（`evals/deterministic/`，pytest，0/1）、
- CLI 赛跑（`scripts/shootout.py`，跨模型表格）、
- 实时竞技场的**完成度（Completion）**列。

**Completion 字段**（除 `id` + `input` 外都可选）：

| 字段 | 含义 |
|-------|---------|
| `input` | 发给每个模型的用户消息 |
| `expect_tool` | 必须触发的工具（`null` = 必须**不**调用任何工具） |
| `expect_in_args` | 必须出现在该工具参数里的子串（不区分大小写） |
| `expect_min_tool_calls` | 工具调用总数的下限（多步任务） |
| `setup_fact` | 跑之前预加载进沙盒的一条记忆 |

完成度分数 = 一个用例满足的期望数 / 总期望数（0.0–1.0）。这是确定性轴：没有裁判、
没有玄学——*该触发的工具触发对了没、参数对不对、多步任务里调用次数够不够。*

**质量（Quality）**是分开的、叠加的：裁判（§5）读最终转录文本，对照评分标准打分。
一个模型可以完成任务（完成度 1.0）却因为回答笨拙或啰嗦得到平庸的质量分——反之亦然，
一个流利却跳过了工具的回答会质量高、完成度低。把两者分开是刻意的；合在一起会恰好
掩盖我们想看到的那种失败。

---

## 3. 套件的各个板块

套件按板块分组，方便你一次赛一个板块。标记为 **[seeded]** 的用例已经在
`evals/dataset.jsonl` 里；**[proposed]** 是接下来要加的。

### A. Agentic 工具调用——助手真正的活

对 Pikaka 的旗舰工具（`create_event`、`save_note`、`send_message`、只读的
`search_web`）做多步编排。这是 K3 天生要赢的轴（它的招牌是 Terminal-Bench /
agentic 工具使用）。

| id | 任务 | 预期结果 |
|----|------|------------------|
| `schedule-basic` **[seeded]** | 「下周二早上 9 点和 Alex 喝咖啡」 | `create_event`，标题含 alex，开始时间含 09:00 |
| `schedule-applies-memory` **[seeded]** | （事实：Alex 喜欢早上）「周五和 Alex 约一次见面」 | `create_event`，应用了该事实 |
| `remember-preference` **[seeded]** | 「记住 Alex 喜欢早上的会议」 | `save_note`，内容含 morning |
| `draft-message` **[seeded]** | 「给 Alex 发消息说 demo 挪到周五了」 | `send_message`，正文含 friday |
| `pokemon-team` **[seeded]** | 「……搜配队，记住皮卡丘是我的初始宝可梦，安排两次训练」 | ≥3 次工具调用：search + save_note + 2× create_event |
| `worldcup-final` **[seeded]** | 「……搜结果，记住谁赢了，给 Raj 起草一条消息」 | ≥3 次工具调用，send_message 收件人含 raj |
| `chitchat-no-action` **[seeded]** | 「我可能哪天和 Alex 喝杯咖啡，再说吧。」 | `expect_tool: null`——碎碎念不是指令；必须**不**排日程 |
| `exact-count-sessions` **[seeded]** | 「明天早上安排三个 25 分钟的专注时段」 | ≥3 次 `create_event`——数量精确，弱模型只做一个 |
| `remember-and-book` **[seeded]** | 「记住我是素食者，然后周四 7 点和 Sam 订晚餐」 | ≥2 次调用：必须**既** save_note **又** create_event(sam) |
| `read-before-write` **[seeded]** | 「看看我下午有没有 30 分钟空闲，安排一次散步」 | ≥2 次调用：list_events（读状态）然后 create_event |

最后四个是*硬*的，各自对应一种失败模式：**过度主动**（对碎碎念也动手）、
**数量精确**（做满三个，不是一个）、**完整性**（两半都做，不只做记得住的那一半）、
**状态感知**（排日程前先读日历，而不是盲排）。这正是只测流利度的裁判会漏掉、
而完成度分数能抓住的东西。

### B. 编程——跨模型，通过 pi   **[已构建——CLI]**

Pikaka 是编排者；**pi** 是编程承包商——但要做一个*编程*基准，我们让 pi 指向每个
**参赛者**的模型，这样一套固定骨架就能给每个大脑试镜。一个编程用例先布好沙盒、
把任务交给 pi，然后**运行产出代码的 `verify` 命令**来打分——SWE-bench 风格
（测试通过、退出码 0），而不是读它的回复。

用例放在它们自己的文件里，`evals/coding.jsonl`（与 agentic 数据集分开，这样它们
永远不会走工具调用那一层），包含 `input`、可选的 `files`（布进沙盒）、以及 `verify`
（其退出码就是分数）：

| id | 任务 | verify |
|----|------|--------|
| `code-fizzbuzz` **[seeded]** | 「创建 fizzbuzz.py，里面有 fizzbuzz(n)……」 | 导入它，断言 Fizz/Buzz/FizzBuzz/str(n) |
| `code-bugfix` **[seeded]** | 布好一个 `add()` 写错的 `calc.py` → 「修好它，别动 check.py」 | 跑 `check.py` |

运行方式：
```bash
make shootout-coding RUNS="kimi:kimi-k3 anthropic:claude-opus-4-8"
```
pi 天生会说我们锁定的每个提供方（anthropic、openai、google/gemini、
**moonshotai/kimi**、xai/grok、zai/glm）——运行器把 Pikaka 的 provider id 映射到
pi 的，并用 `--api-key` 传 key，这样 K3 就能在完全相同的地基上跟全场赛跑。
已实机验证：opus-4-8 和 kimi-k3 都能解出 `code-fizzbuzz`（以真实测试执行为准）。
打分器在 [`pikaka/ops/coding_eval.py`](../pikaka/ops/coding_eval.py)。

**也在实时竞技场里——通过 LOOP，而不是绕过它：** 打开 **"coding (pi)"** 开关再赛。
这会为这场比赛注册 `delegate_task`，于是每张卡都跑**完整骨架**（关卡 → 记忆 → 工具），
模型*决定*调用 `delegate_task`，它会在**那张卡自己的模型上**派生出 pi 子代理来写代码
并运行。它是全自主的——循环跑 模型 → delegate_task → 模型收尾，中间不停——卡片显示
真实凭据：关卡徽章、`delegate_task` 工具芯片、token、成本（循环自己的；pi 内部的
token 不捕获）。自由形式的 prompt（「写个贪吃蛇然后运行它」）也能跑，因为 pi 有 bash
工具，所以「运行它」发生在被委托的子代理内部。（推理模型这里很慢——kimi-k3 当循环
大脑 + pi 可能要几分钟；拍 2-3 个模型即可。）

**代码落在哪 + 自动运行：** 临时编程任务不会消失在临时目录里——`delegate_task` 把它
存进一个带日期、自文档化的工作区（`./pikaka_workspace/<date>/<time>-<model>-<slug>/`，
已 gitignore），里面有 `MANIFEST.md`（日期、模型、任务、文件、运行结果）、pi 写的
文件、pi 的转录、以及 `run.log`。pi 跑完后，骨架会**自动运行**入口脚本（无头、捕获
输出、30 秒超时），并把结果喂回循环，让模型看到自己的代码到底跑没跑起来。配置：
`PIKAKA_WORKSPACE`（根目录）、`PIKAKA_DELEGATE_AUTORUN=0`（禁用）、
`PIKAKA_AUTORUN_TIMEOUT`。见 [`pikaka/tools/workspace.py`](../pikaka/tools/workspace.py)。

### C. 记忆与上下文

| id | 任务 | 预期结果 |
|----|------|------------------|
| `recall-across-session` **[proposed]** | 存一条事实，新会话，再问它 | 事实被检索进工作记忆 |
| `retrieval-gate-negative` **[proposed]** | 存了一条事实后问无关问题 | 关卡**没有**把该事实拉出来（hero-1 行为） |

### D. 推理 / 知识——仅裁判

没有工具；用 K3 裁判给答案本身打分。几个 GPQA 风格的、或「精确解释 X」的 prompt，
打 0–10 分。它们的存在是为了展示质量轴独立于完成度轴而动。

---

## 4. 子代理派生——已经建好（`delegate_task` → pi）

是的，Pikaka 已经做了 Hermes / Claude-Code 风格的子代理派生。它在
[`pikaka/tools/experimental.py`](../pikaka/tools/experimental.py) 里，叫
`delegate_task`，**默认关闭**——设 `PIKAKA_EXPERIMENTAL=1` 才注册。

- **它是什么：** 架构白板上「Sub-Agents」那个框，真正接线了。它把编程任务交给
  **pi**（Mario Zechner 的极简开源编程 agent，`github.com/earendil-works/pi`），通过
  它的无头打印模式（`pi -p "task"`）。
- **分工是教学重点：** Pikaka 是编排者（记忆、工作记忆组装、人的上下文、发布关卡）；
  pi 是专家承包商（read / bash / edit / write）。Pikaka 雇人；pi 写码；Pikaka 的关卡
  检查活。
- **诚实契约：** 工具的返回字符串明确说明发生了什么（done / failed / timed-out /
  pi-not-installed）；完整的 pi 转录进 `.pikaka/outbox/delegate-*.log`。
- **需要：** `npm install -g --ignore-scripts @earendil-works/pi-coding-agent`。
- **这是 Battery B 的底子**——每个编程用例都是一次 `delegate_task`，用 pi 的输出是否
  通过测试来打分。

三个姊妹框仍然是诚实的骨架（返回「coming soon」）：`run_command`（终端）、
`browse_web`（浏览器）、`schedule_task`（定时）——每一个在上线前都需要真实的沙盒 +
  安全面。

*v2 想法已经记在源码里：* 用 `pi --mode json` 跑，把它的每轮事件流式灌进 dashboard
的 Loop 页，这样一次被委托的编程运行就能像普通循环一样动起来。

---

## 5. 裁判——一个可切换的中立仲裁者

质量轴通过 [`pikaka/ops/judge.py`](../pikaka/ops/judge.py) 给每一条回复打 0–10 分 +
一句理由。仲裁者**可以从竞技场切换**（「grade」开关旁边的下拉框），默认是
**gpt-5.6-sol**。

**为什么不用 K3 当裁判：** 你不能用 K3 来测 K3——一个参赛者给自己的回合打分没有
可信度，而且（我们实机踩过）K3 也在*赛跑*，同时给每列打分会把它自己的端点压到 429，
把大多数评分清空。仲裁者应该是一个**不在赛跑**的模型。gpt-5.6-sol 是自然之选：一个
强的推理模型，在这里当*参赛者*很糟糕（它没法在 chat 端点上调工具），但当*裁判*很好
（打分是纯文本）。任何提供方都行——Pikaka 的 OpenAI 兼容客户端给了裁判和 anthropic
线相同的接口。

**分数意味着什么（镜头前这么说）：** 0–10 表示回复对请求的满足程度——正确、诚实、
简洁。9–10 完全解决；5–8 有少量缺口；0 幻觉或声称做了它没做的事。

**真正要紧的公平性修正：** 裁判只看到回复*文本*，于是一句诚实的「我保存好了」看起来
像幻觉、被打 0 分，尽管 `save_note` 真的触发了。现在裁判会拿到**实际跑过的工具清单**
作为 ground truth，这样有真实工具调用支撑的真实动作就能正确得分（已验证：同一条回复
→ 没有工具上下文时 0 分，有工具上下文时 10 分）。

这对应的最佳实践：开放质量用 MT-Bench / Chatbot-Arena 风格的 LLM 裁判，任何有可检查
终态的东西用程序化结果检查（τ-bench / SWE-bench 风格）。我们两者并排都做了。

---

## 6. 已发布的基准参考

每个锁定模型的标准化排行榜数字，作为背景——中立地框定，不做我们自己的排名。来源是
第三方追踪器 + 厂商卡；镜头前引用前请核实。

**Kimi K3**（2.8T 参数，1M 上下文，$3/$15 每 Mtok）：
- Terminal-Bench 2.1：**88.3** · Program Bench：**77.8** · FrontierSWE：**81.2**
  （KimiCode 骨架）· DeepSWE：**67.5**
- GPQA Diamond：**93.5%**（已发布的开源权重里最好）· BrowseComp：**91.2%**
- 综合 agentic 工具使用排名约 #4 / 119，平均 66.6

*（等我们逐个确认其他锁定模型——Opus 4.8、GPT-5.6 Sol、Gemini 3.1 Pro、Grok 4.5——
把它们的卡加到这里，用同样的来源纪律。）*

来源：BenchLM、NxCode、OfficeChai、Trilogy AI（链接见聊天日志）。这些是**外部**
基准；我们的套件（§3）是可复现的本地补充，不是替代品。

---

## 7. 如何运行

```bash
# CLI 赛跑——跨模型的确定性完成度，打印 markdown 表格
make shootout RUNS="kimi:kimi-k3 anthropic:claude-opus-4-8"
#   → 同时写一份带时间戳的 .md + .json 到 .pikaka/shootout/

# 实时竞技场——让每个锁定模型在同一个 prompt 上赛跑，看它流式输出
make dashboard            # localhost:7777 → Arena 标签页

# 有裁判的回答质量（永远别让参赛者给自己打分）
make eval-judge
```

**读记分板：** 累计表把成本 / 时间 / Token 跨场次累加，并（一旦建好）显示每个模型的
完成度和质量。点任意列排序重排；通常有意思的是「最便宜且真的完成了」那一行，而不是
最便宜的（一个每场都报错的模型是 $0.00，毫无用处）。

---

## 8. 最佳实践，以及我们还欠什么

**在市面上**，agentic 模型对比分成两族，严肃的团队两族都用：

1. **程序化结果检查**——给*终态*打分，而不是给文笔打分。SWE-bench（补丁能打上且测试
   通过吗）、τ-bench（工具 agent 有没有把数据库留在正确状态）、Terminal-Bench、BFCL
  （函数调用准确率）。客观、可复现、便宜。→ **我们的完成度轴。**
2. **LLM 当裁判 + Elo**——针对没有单一正确答案的开放质量。MT-Bench、Chatbot Arena。
   主观但可扩展。→ **我们的质量轴。**

**Pikaka 已经有的：** 用例格式（`dataset.jsonl`）、确定性打分、跨模型 CLI
（`shootout.py`）、裁判骨架、以及一个实时竞技场测 速度/成本/Token。

**还欠的（本文档点名的缺口）：**
- ~~完成度列接入实时竞技场~~——**已完成**：在已知 battery 用例上赛跑现在会给每列实时
  打分（绿色「solved」/ 红色「failed · 原因」徽章 + 「solved」记分板列），通过
  [`pikaka/ops/scoring.py`](../pikaka/ops/scoring.py) 里的同一个打分器，与
  `shootout.py` 共享。
- ~~Battery B（编程）+ 跨模型 pi~~——**已完成，CLI *和*实时竞技场**：`make shootout-coding`
  出表格；在竞技场里，「coding (pi)」开关让每张卡用自己的模型跑 pi，终端实时流式，
  用测试打分。
- ~~质量列（K3 当裁判）进竞技场~~——**已完成**：「grade with K3」开关给每条回复打 0-10
  分（[`pikaka/ops/judge.py`](../pikaka/ops/judge.py)）；每列徽章 + 「K3 grade」记分板列。
- ~~成本 vs 质量可视化~~——**已完成**：记分板顶部是成本-vs-（质量|完成度）散点图——
  又便宜又好的是左上角。
- 剩余：竞技场里的编程列；随着视频脚本确定，加更多 battery 用例。

---

## 9. 干跑——开拍前把整件事模拟一遍

对每个轴做一次完整彩排。把每个 prompt **逐字**复制进竞技场的消息框——竞技场按精确
文本匹配到它的 battery 用例并自动打分（打错字 → 它照样赛跑但完成度显示「—」）。

### 准备
1. `make dashboard` → 打开 `localhost:7777` → **Compare** 标签页。
2. 挑你要拍的模型（点芯片）。要全场，就 11 个全上。
3. 点记分板的 **clear** 从零开始。
4. 打开 **"grade with K3"**（右上角，Race 旁边），这样每列也会得到质量分。
  （每次比赛多花一次 K3 调用——符合预期。）

### 第一幕——简单用例（每个人都该过）
逐个粘贴，点 Race，看列填满：

- `Schedule a coffee with Alex next Tuesday at 9am`
- `Remember that Alex prefers morning meetings`
- `Send Alex a message that the demo moved to Friday`
- `What is the capital of France?`  ← 诚实的**无工具**用例：好模型会**不**调工具地
  回答（绿色「solved」= 它正确地保持不动手）

### 第二幕——硬用例（便宜模型翻车的地方——最值钱的段落）
- `I might grab coffee with Alex sometime, we'll see.`  ← 必须**不**排日程（过度主动陷阱）
- `Block three 25-minute focus sessions tomorrow morning`  ← 必须做**三个**事件
- `Remember that I'm vegetarian, then book dinner with Sam this Thursday at 7pm`  ← 必须**两个都**做
- `Check my calendar for a free 30 minutes this afternoon and schedule a short walk`  ← 必须**先读**再写

观察：一个模型答得流利却得到红色 **「failed · <原因>」** 徽章。那就是整个论点上了屏幕。

### 第三幕——多工具展示
- `Build me a Kanto starter team around Pikachu: search current competitive picks for a balanced six, remember that Pikachu is my starter, and schedule two team-training sessions this week`
- `Search for the result of the Spain vs Argentina World Cup final, remember who won, and draft a message to Raj about watching the highlights together`

### 第四幕——揭晓
滚到 **Scoreboard**：顶部的成本-vs-质量**散点图**（又便宜又好 = 左上角），然后是表格
——点表头按 **solved**、**K3 grade** 或 **total cost** 排序。这就是「opus 贵 2 倍、
好 2 倍吗？」的镜头。

### 第五幕——编程回合（终端，还不是 dashboard）
```bash
make shootout-coding RUNS="kimi:kimi-k3 anthropic:claude-opus-4-8 gemini:gemini-3.5-flash"
```
每个模型的 pi 写真实代码，用测试通过来打分。报告存到 `.pikaka/shootout/coding-*.md`。

### 可选——可复现的 CLI 表格（全部 agentic 用例、全部模型）
```bash
make shootout RUNS="kimi:kimi-k3 anthropic:claude-opus-4-8 gemini:gemini-3.5-flash openai:gpt-5.3-chat-latest xai:grok-4.5"
```
`--trials 3` 得到稳定的**通过率**（工具调用是非确定性的）；保存 markdown + json 报告到
`.pikaka/shootout/`，任何人都能用他们自己的 key 复现。

### 要彩排到的坑
- **gpt-5.6-sol** 每场都故意报错（推理模型，没法在 /v1/chat 上调工具）——留着它展示
  诚实的报错，或者去掉它的芯片。
- **grok** 需要 xAI 额度，否则 403。
- 一次给全场打分可能把 K3 端点压到 429；某列可能显示「—」当质量分（内置了一次重试）。
  需要上镜就重赛那一列。
- **kimi-k3 很慢**（推理）——它的列最后才完成；记分板随每个模型落地逐个折叠进来，
  所以看板不会为了等它而冻结。

---

## 10. 指标——每个记分板列意味着什么（以及确切的数学）

镜头前的图例。每个数字都在一个地方、用一种方式算出，并且**对照手算验证过**
（下面的工作示例——所有字段都对得上）。

| 列 | 含义 | 确切公式 | 好 = |
|--------|---------------|---------------|--------|
| **solved** | 完成度——它真的做成任务了吗 | `passed / scored`，按用例清单（工具对、参数对、调用次数够） | 尽量接近 `scored/scored` |
| **K3 grade** | 质量——回复有多好 | 对已打分的回复取 kimi-k3 的 0-10 分**均值** | 越高越好（7+ 算强） |
| **races** | 这个模型跑了多少次 | 该模型跨所有场次的行数 | —（分母） |
| **ok** | 没报错的场次占比 | `ok / races`（报错 = 一个连跑都跑不起来的模型） | `races/races` |
| **total time** | 累计墙钟时间 | 对**成功**场次 Σ `latency_ms` | 越低越好 |
| **in tok / out tok** | 累计 prompt / completion token | 对成功场次 Σ `tokens_in`、Σ `tokens_out` | — |
| **total tok** | 输入 + 输出 | `in tok + out tok` | 同样工作下越低越好 |
| **rate $/M** | 模型的标价 | 每百万 token 的 `$in / $out`（按模型，已核实） | —（参考） |
| **total cost** | 累计美元 | 对成功场次 Σ `(tokens_in × rate_in + tokens_out × rate_out) / 1,000,000` | 同样质量下越低越好 |

### 决定边界情况的规则（镜头前大声说出来）

- **成本每次读取都从 token 重算**，所以一次定价修正也会修正过去的场次——数字永远
  不过时。
- **输出 token 比输入贵 3-5 倍**——这就是为什么输入/输出分开。一个「便宜」但啰嗦的
  模型可能比一个更贵却简洁的模型花费更多。
- **报错的场次计入 `races`、拉低 `ok`，但对 token、成本、完成度毫无贡献。** 一个只会
  报错的模型是 `$0.00`——而且没用。读「最便宜且真的*完成了*的」，不是最便宜的。
- **只有已知 battery 用例的 prompt 才得到 `solved` 分数**（精确文本匹配）；自由形式的
  prompt 会赛跑但显示 `—`。
- **`K3 grade` 只在「grade with K3」开着时才出现**；没打分的场次显示 `—`。

### 工作示例（这是计算的复核）

两场比赛、两个模型、已知 token 数：

| 模型（费率） | 比赛 1 | 比赛 2 | → solved | K3 grade | total tok | total cost |
|---|---|---|---|---|---|---|
| kimi-k3（$3/$15） | 1000 in / 500 out · 通过 · q8 | 2000 in / 1000 out · 失败 · q6 | **1/2** | **7.0** = (8+6)/2 | **4500** | **$0.0315** = (3000·3 + 1500·15)/1M |
| gemini-3.5-flash（$1.5/$9） | 1000 in / 200 out · 通过 · q5 | **报错** | **1/1**（报错场次不打分） | **5.0**（只有比赛 1 打了分） | **1200** | **$0.0033** = (1000·1.5 + 200·9)/1M |

对这些输入跑 `aggregate()` 能精确复现每一个加粗数字——记分板的数学是对的。
（随时可以用加这一节的那个 commit 里的工作示例脚本再验证。）
