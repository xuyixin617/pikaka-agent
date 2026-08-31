# 在每个提供方自己的控制台里看你的记忆

> 本文是 [`memory-backends-playbook.md`](memory-backends-playbook.md) 的中文翻译。以英文原稿为准；如有出入，以原文为准。

Arena 的 **Memory** 标签页通过 Pikaka 的 `FactStore` 读每个后端，所以它给所有后端显示
同样的六个方法。那是契约的意义——也正是它的盲点。每个提供方在底层存的东西*不一样*，
而看它们对你的句子到底做了什么，唯一的办法是打开它们自己的控制台。

这是那个指南：数据落在哪、你会在那里看到什么 Pikaka 视图抹平掉的东西、以及一次基准
运行之后怎么清理。

| 后端 | 控制台 | Pikaka 的视图藏了什么 |
|---|---|---|
| Mem0 | [app.mem0.ai](https://app.mem0.ai) → Memories | 它的抽取决策、每条记忆的历史 |
| Zep | [app.getzep.com](https://app.getzep.com) → 你的项目 → Graph | 实体/边图和有效性区间 |
| LangMem | **没有——它是库，不是服务** | 没有；没有服务器可看 |
| Supabase | 你的项目 → Table editor → 向量表 | 原始行和嵌入 |
| sqlite | Pikaka 自己的 **Memory** 页，或 `.pikaka/state.db` | 没有——这个已经完全可见 |

---

## 动手之前：你在看哪个账户、哪个用户？

每个托管后端按用户 id 分区，而 Pikaka 在一个稳定的默认值下写，这样单用户安装就不会把
记忆散到每次运行一个新分区里。

| 后端 | 环境变量 | 默认 |
|---|---|---|
| Mem0 | `MEM0_USER_ID` | `pikaka` |
| Zep | `ZEP_USER_ID` | `pikaka` |
| LangMem | *（命名空间固定在代码里）* | — |

如果控制台看起来是空的，先查这个。按错误的用户 id 过滤，看起来和「什么都没存」完全一样，
而这两件事意思是相反的。

---

## Mem0 —— [app.mem0.ai](https://app.mem0.ai)

1. 用拥有 `.env` 里 `MEM0_API_KEY` 的那个账户登录。
2. 打开 **Memories**，按用户 `pikaka` 过滤。

**看什么。** Mem0 的产品是决定什么值得记，所以把你说的句子和它留下的行对照——通常不是
同一段文本。那是特性，不是 bug。

**一个会改变你怎么读一场比赛的提醒。** Pikaka 的适配器用 `infer=False` 调 `add()`，因为
`FactStore` 契约说一次写入必须总是存储。那刻意关掉了 Mem0 的抽取，所以一个 Arena 结果
测的是它的**检索**，不是它的抽取。如果你想看抽取在运转，通过 Mem0 自己的 playground
加记忆，而不是通过 Pikaka。

---

## Zep —— [app.getzep.com](https://app.getzep.com)

1. 登录，选 key 在 `ZEP_API_KEY` 里的那个项目。
2. **Users** → `pikaka` → **Graph** 看可视化，或 **Episodes** 看你发的原始文本。

**看什么——这个最值得拍。** Zep 不存行，它建一个时序知识图谱：实体、它们之间的边、以及
*有效性区间*。问它发布时间，它不会给两个竞争事实排序；旧的边在某时间点被标记为 superseded
（被取代）。这和列表里每一个基于行的存储都是真正不同的设计，而图视图正是你能看到它的
地方。

**两件如果没人说会把你搞糊涂的事：**

- **摄取是异步的。** `graph.add()` 约 0.2s 返回，带 `processed=False`。你刚写的数据可能
  一分多钟都无法搜索。Pikaka 的适配器会轮询直到 Zep 报 `processed=True`（受
  `ZEP_MAX_WAIT_SECONDS` 封顶，默认 120），正是为了让一场比赛不会把 Zep 评成「忘了它还
  在归档的东西」。
- **Episodes ≠ 你拿回来的东西。** 搜索返回的是 Zep 对一条边或节点的渲染，不是你发的那句
  话。答案读起来和其他后端不同，即使同样正确。

---

## LangMem —— 没有控制台

LangMem 是一个**库**，不是一个托管服务，而这一点会绊倒人，因为它和两个带 dashboard 的
产品坐在同一张列表里。

- **没有** `PIKAKA_LANGMEM_POSTGRES`，它跑 LangGraph 的 `InMemoryStore`——记忆在 Python
  进程内。dashboard 一重启，它就没了。没什么可打开，也没什么可清理。
- **有** `PIKAKA_LANGMEM_POSTGRES=postgresql://…`，它用 `PostgresStore`，而「看你的记忆」
  意味着直接查那个数据库。

这也是为什么 Arena 的 store 卡把 LangMem 显示为「不可读」而不是「0 条事实」——每一次读
都会构造一个全新的空 store，把它报成零，就是对空 store 说了一句假话，而不是对「不可读」
说了一句真话。

---

## Supabase —— 你项目的表编辑器

打开项目 → **Table editor** → 由 `SUPABASE_TABLE` 命名的表。行直接可见，包括嵌入。它是
托管选项里最透明的：你看到的就是适配器写进去的。

---

## 一次基准运行之后：清理

**Arena 参赛者跑在一次性的 home 里**，所以一场比赛从不碰 `.pikaka/state.db`。但*托管*
后端没有这种隔离——Mem0 和 Zep 在你的真实账户、用户 `pikaka` 下写，而那些记忆在运行后
持续存在。

两种把基准数据挡在你真实账户外的办法：

1. **把 arena 指到别处**——比赛前设 `MEM0_USER_ID=pikaka-bench` 和
   `ZEP_USER_ID=pikaka-bench`，你的日常记忆就留在 `pikaka` 分区。
2. **用完在每个控制台删除那个基准用户。**

拍之前就做。一张显示你真实记忆的 store 卡会把你的地址和你同事的名字放上屏幕——Arena
按设计读实时数据，它不知道哪一部分你宁愿不公开。

---

## 一旦你在看全部时，该比较什么

有意思的问题不是「谁分高」。而是**每一个选择保留了什么**：

- 给它们同样一句句子，比较存储形式。Mem0 改写它，Zep 把它分解成图，sqlite 几乎逐字保留。
- 说一句和更早事实矛盾的话，然后看旧的发生了什么。行存储让它原样躺着，同样可检索。Zep
  标记它为 superseded。
- 然后用另一种语言、或换一种说法问那个问题，看哪个 store 仍能找到它。

最后那个正是 Pikaka 自己的 FTS5 store 最弱、向量支撑的服务最强的地方——在镜头前声称
任何事之前值得知道。
