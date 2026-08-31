# pi —— 完整讲解 / 完整讲解

> 本文是 [`pi-agent.md`](pi-agent.md) 的中文翻译。以英文原稿为准；如有出入，以原文为准。

**拍片就照这一个文件来。** 按图表从左→右、上→下走。每个框：它是什么、**它在磁盘上的
实际位置**、以及要说的那句台词。

锁定：**pi 0.82.0** · 源码读自 `~/Developer/pi` @ `24e5cc0`（2026-07-24）· 演示实机
验证于 2026-07-25。每个 `[tested]` 都在本机跑过。

视频回答的那一个问题：**上下文归谁——厂商，还是你？** pi 的答案：*归你。*

图表：`~/Developer/Excalidraw/26.07.25 pi agent.excalidraw`

---

## 0 · 三种作用域——你加的任何东西能活在哪

这张表是后半段全部的思维模型。**一个东西放在哪，决定了谁拿到它。**

| 作用域 | 路径 | 谁拿到它 |
|---|---|---|
| **你**，到处 | `~/.pi/agent/` | 只有你，在每一个项目里 |
| **这个仓库** | `<repo>/.pi/` · `<repo>/.agents/skills/` | 任何 clone 它的人 |
| **全世界** | 一个 package → `pi install npm:… / git:…` | 任何安装它的人 |

```
~/.pi/agent/
├── sessions/<cwd-slug>/<timestamp>_<uuid>.jsonl   对话树
├── skills/                                        你的全局技能
├── settings.json · auth.json · trust.json         配置、密钥、受信目录
└── models-store.json                              本地价格/模型表
```

**中文:** 东西放在哪，决定谁能用到：`~/.pi/agent/` 只有你、`<repo>/.pi/` 全队、package
全世界。作用域就是这一课。

---

## 1 · 主干——走一遍图表

### FACES——一个大脑，四副面孔

| 命令 | 它是什么 |
|---|---|
| `pi` | **TUI**——你终端里的交互式应用 |
| `pi -p "task"` | **CLI**——答一次，退出。脚本就是这么嵌入它的 |
| `pi --mode json` | stdout 上的**事件流**，一行一个 JSON ← *pikaka 从这里接入* |
| `pi --mode rpc` | 给其他程序用的长驻管道 |

四个面孔消费**同一个事件流**——循环永远不知道谁在看。

> **说：**「Claude Code 也有同样三副面孔——`claude` 是 TUI，`claude -p` 是 CLI，桌面
> 应用是 GUI。界面是衣服，不是 agent。」

可以在镜头前跑的双命令演示：
```bash
claude -p "Reply with exactly: pikaka pikaka"   # 答完，退出
claude    "Reply with exactly: pikaka pikaka"   # banner、状态、等你
```

### CONTEXT——整个状态

`user prompt` + `当前会话` + `AGENTS.md` + 一个**不到 1k token 的 system prompt**
= 一份纯 JSON 消息列表。

- 位置：`~/Developer/pi/packages/coding-agent/src/core/system-prompt.ts`（162 行）
- **AGENTS.md ≠ SOUL.md。** `AGENTS.md` 属于*仓库*（约定、测试命令——你的 `CLAUDE.md`
  正是这个，pi 两者都读）。`SOUL.md` 属于*agent*（身份、性格）。pi **没有** SOUL.md——
  它不想要性格，它是承包商。pi 沿着目录树*向上*走，拼接它找到的每一个 `AGENTS.md`——
  那是项目作用域，不是身份。

> **说：**「这是系统的全部状态。除了你放进去的，什么都进不来。而且因为它是纯 JSON，
> 一个不同的脑袋能在对话进行到一半时接手。」

### THE LOOP——`agent-loop.ts`，792 行

```bash
wc -l ~/Developer/pi/packages/agent/src/agent-loop.ts     # → 792
```

图表上的三个符号，每一个在代码里都有真实位置：

**◇ `tools?`** — [`agent-loop.ts:203`](../../pi/packages/agent/src/agent-loop.ts)
```typescript
const toolCalls = message.content.filter((c) => c.type === "toolCall");
if (toolCalls.length > 0) { … }
```
那就是整个菱形。模型的回复要么包含工具请求，要么不包含。**没有 → 这一轮结束 → REPLY。**
有 → 跑它们，把结果喂回去，再问一次。*这是循环唯一的退出条件。*

**□ `read · write · edit · bash`** — 四个文件：
```
~/Developer/pi/packages/coding-agent/src/core/tools/
├── read.ts  write.ts  edit.ts  bash.ts      ← 四个内置
└── find.ts  grep.ts   ls.ts                 ← 可选额外
```
一个工具 = 一个名字 + 一段描述 + 一个参数 schema + 一个函数。模型从不碰你的磁盘；它只能
*请求*其中一个。默认**并行**跑（`agent-loop.ts:425`），当某个工具要求时顺序跑。

**◇ `allowed?`** — 扩展关卡。
[`extensions/types.ts:1065`](../../pi/packages/coding-agent/src/core/extensions/types.ts)：
```typescript
export interface ToolCallEventResult {
  block?: boolean;
  reason?: string;
}
```
任何工具运行前，pi 问每一个已加载的扩展*「这就要发生了——反对吗？」*如果有一个返回
`{block: true, reason: "…"}`，`runner.ts:932` 就拦住它。**不加载任何扩展时，什么都拦不住**
——这个菱形是*你的*插入点。这就是为什么图表的箭头从 EXTENSIONS 指向这个菱形。

**「blocked → 作为一个工具结果返回」**——`reason` 字符串被喂回**一个成功工具结果本该
占据的同一个槽位**。在模型看来它和其他工具输出一样，所以它去适应而不是崩溃。这就是
`reason` 挨着 `block` 的原因：一个布尔只能叫停；一个字符串能*教*。

> **说：**「拒绝是以工具结果的形式回来的。模型读到*为什么*，然后绕着它干。大多数骨架
> 只会崩溃。」

### TWO EXITS

- **REPLY**（绿色）——模型不再请求工具。
- **SESSION**（teal）——一棵**树，不是日志**。一个 JSONL 文件，每一行
  `{id, parentId, message}`。`/fork` **就地**分支，`/tree` 时间旅行，甚至*切换模型*
  也是一个节点。
  `~/.pi/agent/sessions/<cwd-slug>/<timestamp>_<uuid>.jsonl`

> **说：**「对话的 git。」

---

## 2 · 乐队——让 pi 变强的四种方式，最省上下文优先

**顺序本身就是论点。**

### ① `bash` + 一个 README  （替代 MCP 的那个东西）

pi 的模型已经有 `bash`，而 bash 能跑**你机器上的每一个程序**。所以能力已经在那了——
唯一缺的是*知道怎么用它*。在工具旁边放一个 README；模型在**需要的时候**读它。

- **谁调它？模型调**，通过 `bash` 工具，在 pi 的循环内部。
- **成本：** 一个 MCP 服务器在启动时把每个工具的 JSON schema 粘进上下文——大的一个约
  13.7k token，**每一轮，用没用都算。** 一个 CLI + README 在**使用的那一刻之前**成本是
  **0 token。**
- 本机已有一个活例子：`~/.pi/agent/skills/pi-skills/brave-search/`——一个 CLI 加一个
  `SKILL.md`。网页搜索，无服务器、无协议、无每轮税。

### ② SKILLS——模型*读*的知识

一个文件夹 + `SKILL.md`。**Markdown，没有代码。** 启动时 pi 只读每个技能的*名字和描述*；
正文在任务匹配时按需加载——**渐进披露**，直接来自 pi 的文档。用 `/skill:name` 强制加载。

位置：`~/.pi/agent/skills/`（你）· `<repo>/.pi/skills/` 或 `.agents/skills/`（团队）

### ③ EXTENSIONS——模型*调用*的一个动词

**一个 TypeScript 文件**，热加载，约 30 个生命周期钩子。两件活：**加一个动词**
（`registerTool`）或**守一个动词**（`on("tool_call")`）。唯一能改变循环行为的层。

位置：`~/.pi/agent/extensions/*.ts` · `<repo>/.pi/extensions/*.ts`
79 个随源码发布的例子：`~/Developer/pi/packages/coding-agent/examples/extensions/`

> **说：**「十行就是一个可用的权限系统。」

### ④ PACKAGES——发货箱

一个 npm 或 git 的 skills + extensions + prompts + themes 捆绑包，声明在 `package.json`
的 `"pi"` 键下。`pi install npm:… / git:…`。已发布 2100+。

> **说：**「Extension = 应用。Package = App Store 的货架条目。」

**要落地的三组对比：**
1. **Skill vs extension**——一份模型读、并自己驱动 bash 的菜谱，对比一个它工具列表里
   真实带类型的、跑你代码的工具。
2. **Extension vs package**——你*写* extension；你*发* package。
3. **Extension vs MCP**——同一个思路（模型调用的工具），但本地、进程内、上下文中只有
   *你的*工具，而且它还能守调用、画 UI。无服务器、无每轮 schema 税。

---

## 3 · 刻意拒绝

| 拒绝 | 改用 |
|---|---|
| MCP | 任意 CLI + 它的 README |
| 子代理 | 派生更多 pi（tmux——或 pikaka 的 `delegate_task`） |
| plan 模式 / todos | `PLAN.md`、`TODO.md`——你能打开的文件 |
| 权限 | 把它跑进容器里 |
| **记忆 · 评估** | **编排者的活**——pi 的「记忆」只是原始会话 |

> **说：**「这些拒绝不是洞，是重定向。而且每一次拒绝都变成了别人的 package——这就是
> 为什么有 2100 个。」

---

## 4 · pikaka × pi——协作命题

```
pikaka loop → delegate_task → subprocess → pi -p --mode json
     pi's events → 竞技场卡片（实时迷你终端）
     pi's tokens → pikaka 的用量账本（编程运行不是免费的）
```

接线：[`pikaka/tools/experimental.py`](../pikaka/tools/experimental.py)——每一次被委托的
pi 运行都继承本仓库自己的 extensions 和 skills：

```python
def _project_pi_flags() -> list[str]:
    root = Path(__file__).resolve().parents[2]
    flags = []
    for ext in sorted((root / ".pi" / "extensions").glob("*.ts")):
        flags += ["--extension", str(ext)]
    skills = root / ".agents" / "skills"
    if skills.is_dir():
        flags += ["--skill", str(skills)]
    return flags
```

> **说：**「pi 拒绝构建子代理——这正是它作为子代理可嵌入的原因。记忆和评估归编排者；
> 工具归专家。」

---

## 5 · 实机演示——训练师之旅 / 养成大师

四种加能力的方式，作为一条「菜鸟→冠军」的弧线。PokeAPI 是公开的（无 key）。

**开拍前，镜头外：**
```bash
cd ~/Developer/pikaka-agent
git stash                       # 干净仓库——见第一个坑
set -a; source .env; set +a
```

| 阶段 | 节拍 | 层 | 位置 |
|---|---|---|---|
| 0 | 1 号路，赤手空拳 | **ANY CLI** | 无——bash 直接跑它 |
| 1 | 大木博士的图鉴 | **SKILL** | `.agents/skills/pokedex/` |
| 2 | 招式 + 道馆规则 | **EXTENSION** | `.pi/extensions/pokemon-battle.ts` |
| 3 | 赢得徽章 | **PACKAGE** | `examples/pi-pokedex/` |
| 4 | 联盟 | **pikaka × pi** | `delegate_task` |

### 阶段 0——bash 已经是个工具
```bash
curl -s https://pokeapi.co/api/v2/pokemon/pikachu | head -c 200
```

### 阶段 1——SKILL  **[tested]**
```bash
./.agents/skills/pokedex/pokedex.sh charizard
#  Charizard #6 · fire, flying · HP 78 / Atk 84 / Def 78 / SpA 109 / SpD 85 / Spd 100

pi --skill .agents/skills/pokedex --provider anthropic --model claude-haiku-4-5 \
   -a --no-session -p "Use the pokedex skill to look up snorlax and report its base stats."
#  Snorlax (#143) — HP 160, Atk 110, Def 65, Spd 30 …
```
`SKILL.md` 是指令卡；`.sh` 是它跑的工具。**两者合起来才是技能。**

### 阶段 2——EXTENSION  **[tested]**
```bash
# 2a — 加一个动词
pi -e .pi/extensions/pokemon-battle.ts --provider anthropic --model claude-haiku-4-5 \
   -a --no-session -p "Call type_matchup with attacker=fire, then say what fire beats."
#  → Fire is super-effective against grass, ice, bug, and steel.

# 2b — 守一个动词（一次性目录，带一个 dummy 的 .pikaka）
pi -e .pi/extensions/pokemon-battle.ts … -p "Run: rm -rf .pikaka"
#  → "…blocked by a safety guard. The .pikaka directory is protected…"
#  → .pikaka 存活了。拒绝以工具结果的形式回来，模型去适应——
#    提出备份 / 收窄路径——而不是崩溃。
```
**那就是 `allowed?` 菱形，实机上演。**

### 阶段 3——PACKAGE  **[tested]**
```bash
# -ne 禁用自动发现：这个仓库在 .pi/ 和 .agents/ 里还有散装的拷贝，
# 两者都加载会注册两次 type_matchup → 硬错误。
pi -ne -e ./examples/pi-pokedex --provider anthropic --model claude-haiku-4-5 -a --no-session \
   -p "What single type beats Charizard? Use the pokedex, then type_matchup. One word."
#  → Rock   （pokedex: Fire/Flying → type_matchup → Rock 两样都克）

pi install ./examples/pi-pokedex   &&   pi list   &&   pi remove ./examples/pi-pokedex
```
Skill + extension **可组合**。冲突本身就是一课：skills 警告并保留第一个；extension 工具
**硬报错**——一个动词有两份拷贝是歧义，所以 pi 拒绝而不是瞎猜。

### 阶段 4——pikaka × pi
```bash
PIKAKA_EXPERIMENTAL=1 make run        # + make dashboard (:7777)
# 问 pikaka："delegate to pi: what beats Charizard? use the pokedex + type_matchup"
```
看竞技场卡片实时流式子代理的工具。

> **说：**「我们升级了承包商，却没动编排者的脑子。」

---

## 6 · 坑——最好的教学时刻

- **pi 裸跑模型，它会跑偏。** 有一次运行里，haiku 无视「fire 克什么？」而去跑了
  `git add`，报告「已暂存，可提交」。原因：pi 从仓库加载 `AGENTS.md`/`CLAUDE.md`，
  而 pikaka 的写着*「每个里程碑都提交」*。看到一个脏仓库，模型服从了环境规则而非
  那个琐碎 prompt。4 次里 3 次正确。**干净仓库 + 明确的 prompt。**
- **知识截止时刻。** 一个 Gemini 会话在 pi *自己的*文档里读到 `gpt-5.6`，认定它是
  「模拟时间线里的虚构例子」——它的训练截止在和眼前证据抬杠。没有骨架去垫它。
  *「Claude Code 让每个模型都显得聪明，因为骨架托着它。pi 是一台显微镜。」*
- **Extension 工具名必须唯一**——散装文件 + package 一起 = 硬错误。用 `-ne`，或一次只
  用一种作用域。

## 7 · 五句金句

1. 「上下文窗口就是全部状态——除了你放进去的，什么都进不来。」
2. 「MCP 每一轮都粘它的 schema；一个 CLI + README 在你用到之前一文不花。」
3. 「十行就是一个可用的权限系统。」
4. 「Extension = 应用；package = App Store 的货架条目。」
5. 「记忆和评估归编排者；工具归专家。」

## 8 · 镜头前的代码路径

```bash
wc -l ~/Developer/pi/packages/agent/src/agent-loop.ts            # 792
ls    ~/Developer/pi/packages/coding-agent/src/core/tools/       # 四个
ls    ~/Developer/pi/packages/coding-agent/examples/extensions/  # 79 个例子
ls    ~/.pi/agent/sessions/                                      # 你自己的树
```

---

*来源：pi 源码本地读于 `24e5cc0` · [mariozechner.at，「构建一个极简编程 agent 我学到了
什么」](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/) ·
[earendil-works/pi](https://github.com/earendil-works/pi) · 本机实机测试，pi 0.82.0，
2026-07-24/25 · 图表 prompt：[whiteboards/pi-chart-prompt.md](whiteboards/pi-chart-prompt.md)
· @ShenSeanChen*
