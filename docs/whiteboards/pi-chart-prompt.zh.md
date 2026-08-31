# Prompt——构建 pi 系统设计图

> 本文是 [`pi-chart-prompt.md`](pi-chart-prompt.md) 的中文翻译。以英文原稿为准；如有出入，以原文为准。

把栅栏之间的所有内容粘进 Claude Code（VS Code 扩展）或任何能输出 SVG/Excalidraw 的模型。
事实已针对 pi 0.80.10 于 2026-07-24 实机核实；这些数字是承重的，别让模型编造新的。

配套：[pi-agent.md](../pi-agent.md)——这张图所图解的那份讲解。

---

```
Draw a horizontal system-design chart of the "pi" coding agent
(github.com/earendil-works/pi, MIT, by Mario Zechner). Landscape, meant to be
filmed on a 16:9 screen, then hand-redrawn on Excalidraw.

STYLE
- Hand-drawn whiteboard feel. Excalifont if available, else any marker font.
- Two font sizes only: 14px for box titles, 12px for everything else.
- Color grammar, follow it strictly:
    green  = human text in/out, and "act" decisions
    pink   = a MODEL thinking (ellipse only — nothing else is an ellipse)
    orange = the loop boundary
    blue   = interfaces and outside-chapters
    purple = extensions / the plugin family
    teal   = storage
    red    = the harness boundary, real file paths, and refusals
- Diamonds are decisions. Ellipses are models. Rectangles are everything else.
- Sentence case. No emoji. Keep boxes sparse: title + 2-4 short lines each.
- Nothing may overlap; arrows must not cross a box. If it doesn't fit, shrink
  the text before you let two things collide.

LAYOUT — one spine across the top, one band below, two footers.

TOP SPINE, left to right, four stages joined by labelled arrows:

  1. FACES (blue) — "one brain, four costumes"
       pi              -> TUI, interactive
       pi -p "task"    -> answers once, exits (how scripts embed it)
       pi --mode json  -> event stream on stdout   <- mark: pikaka enters here
       pi --mode rpc   -> long-lived pipe
     note: all four consume the SAME event stream; the loop never knows who
     is watching.

  2. CONTEXT (grey outline) — the working memory
       user prompt + session so far + AGENTS.md + system prompt (<1k tokens)
       = one plain-JSON message list
     note (orange): this IS the whole state — nothing enters it behind your
     back, and because it's plain JSON another brain can continue it mid-chat.

  3. THE LOOP (orange boundary, label the file: agent-loop.ts, 792 lines)
       (LLM agent)  pink ellipse, subtitle "any of 37 brains (pi-ai)"
            |
       <asked for tools?>  green diamond
            |- no  ---> exits the loop to REPLY
            |- yes ->
       <extension allows?> purple diamond
            |- blocked -> the refusal is returned AS A TOOL RESULT, so the
            |             model reads why and adapts (not a crash)
            |- yes ->
       [run tools, in parallel: read | write | edit | bash]  green
            -> results appended back into CONTEXT, loop again (curved arrow)

  4. TWO EXITS
       REPLY (green, small) — when the model stops asking for tools
       SESSION (teal) — "a tree, not a log": every line {id, parentId, message};
       /fork any moment, /tree time-travels, branches live in place, even a
       model switch is a node.
       path in red: ~/.pi/agent/sessions/<cwd-slug>/<timestamp>_<id>.jsonl

BAND BELOW — "making pi strong: four ways to add power, cheapest context first"
Four equal boxes left to right. The ordering is the argument — say so.

  SKILLS (purple)      a folder + SKILL.md, markdown, no code.
                       Only the DESCRIPTION stays in context; the body loads
                       on demand. Invoke with /skill:name.
  EXTENSIONS (purple)  one TypeScript file, hot-loaded, ~30 lifecycle hooks.
                       Add a tool, block a call, draw UI. This is what powers
                       the <extension allows?> diamond — draw a light arrow
                       from this box up to that diamond.
                       10 lines = a working permission system.
  PACKAGES (purple)    an npm or git bundle of skills + extensions + prompts
                       + themes, declared under a "pi" key in package.json.
                       pi install npm:... / git:...   2,100+ published.
  ANY CLI (green)      bash already runs it — no plugin needed. Put a README
                       beside the tool; the model reads it only when needed.
                       THIS IS WHAT REPLACES MCP.

  paths line, red: ~/.pi/agent/skills/ · ~/.pi/agent/extensions/*.ts ·
  <repo>/.pi/... for project scope · 70+ shipped examples live in
  pi/packages/coding-agent/examples/extensions/

FOOTER 1 (red) — refused, on purpose:
  MCP -> a CLI + its README (a big MCP server can cost ~13.7k tokens of tool
  schemas every turn, used or not) · sub-agents -> spawn more pi's (tmux, or
  another harness) · plan mode + todos -> PLAN.md, TODO.md · permissions ->
  run it in a container.

FOOTER 2 (blue) — pikaka x pi, the collab thesis:
  pikaka loop -> delegate_task -> subprocess -> pi -p --mode json
  pi's events -> pikaka's arena card (a live mini-terminal)
  pi's tokens -> pikaka's usage ledger (coding runs aren't free)
  "memory and evals belong to the ORCHESTRATOR; tools belong to the SPECIALIST."

FACTS THAT MUST STAY EXACT
  792 lines (packages/agent/src/agent-loop.ts) · exactly 4 built-in tools
  (read, write, edit, bash; grep/find/ls are opt-in extras) · 37 providers ·
  system prompt under 1,000 tokens · 2,100+ packages · MIT licence.
  Do not invent numbers. If unsure, leave it off the chart.
```

> 上面这段 prompt 刻意保留英文，因为它是直接喂给模型生成图的指令，翻译会破坏其中的
> 精确技术术语和数字约束。

---

## 值得要求的变体

- **`Redraw as one vertical column`**——更适合手机或高画布。
- **`Just stage 3, the loop, filling the whole canvas`**——段落 B 的特写。
- **`Output Excalidraw JSON instead of SVG`**——然后把这个文件直接拖到 excalidraw.com。
- **`Add a second column comparing each row to Claude Code`**——把它变成 vs 板。

## 镜头前的三个代码时刻

```bash
wc -l ~/Developer/pi/packages/agent/src/agent-loop.ts     # -> 792
ls ~/Developer/pi/packages/coding-agent/examples/extensions/
ls ~/.pi/agent/sessions/                                   # 你自己的树
```
