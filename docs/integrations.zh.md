# 把它接到你的生活里

> 本文是 [`integrations.md`](integrations.md) 的中文翻译。以英文原稿为准；如有出入，以原文为准。

这里的一切都是 opt-in、各自藏在各自的 extra 后面。没有一样会改变循环——网关把文本
搬进搬出，一个集成是 agent *可能*会调用的工具。这四根支柱在一样都不装的情况下也能工作。

从 README 里挪出来的——README 已经涨到 569 行，可这个项目的承诺是「一个下午能读完」。
没有重写任何东西。

## 和它说话

```bash
uv pip install -e '.[voice]'
pikaka voice        # 免提：一直听着「pikaka pikaka」
```

**默认免提。** `pikaka voice` 监听唤醒词 **"pikaka pikaka"**——一个小巧的 Whisper 模型
扫描麦克风；当它听到这句话，大模型接过来处理你的指令并说出回复。改掉或禁用它：

```bash
PIKAKA_WAKE_WORD="hey pikaka"  pikaka voice     # 任意短语，无需训练
PIKAKA_WAKE_WORD=""          pikaka voice     # 改为按键说话（Enter、说话、Enter）
```

匹配器是约 15 行透明的代码，带一个确定性评估；它接受跨脚本变体
（`"pikaka pikaka,ぴかぴか"`）。一个训练过的 openWakeWord 模型是高效的 v2 升级路径。

**一个好听的嗓音。** 开箱即用 macOS 的 `say`——Pikaka 会自动挑你机器上最好听的嗓音，
优先选已下载的 Premium/Enhanced 版（系统设置 ▸ 辅助功能 ▸ 朗读内容 ▸ 系统嗓音），
而不是机器人感的内置音。要真正的神经嗓音升级，装
[Kokoro](https://github.com/hexgrad/kokoro)——一个完全本地、离线的英式管家嗓音，
自动被识别，无需环境变量：

```bash
uv pip install '.[voice-neural]'          # 神经 Kokoro（bm_george）；会拉 torch（~2GB）
```

用 `PIKAKA_VOICE` 覆盖任一引擎（一个 `say` 嗓音名，或一个 Kokoro 嗓音，如 `bf_emma`）。

## 手机到笔记本

```bash
pip install -e '.[telegram]'
# 给 @BotFather 发消息，/newbot，把 token 放进 .env，然后：
make telegram
```

从任何地方给你的 bot 发短信，你的笔记本就跑这一轮——长轮询，所以不需要公开 URL 或
webhook。设 `TELEGRAM_ALLOWED_USER` 把它锁定到只有你。

## 给我简报一周（Apple 日历 + 邮件）

```bash
PIKAKA_APPLE_TOOLS=1 make brief      # macOS；第一次授予权限提示
```

Pikaka 读你**真实的** Calendar.app（包括邮件邀请的事件）和最近的 Apple Mail，交叉引用
你的记忆，写一份聚焦优先级的简报，带可点击的 `message://` 链接。用 cron 做晨间问候：

```
30 7 * * *  cd ~/pikaka-agent && make brief
```

它走普通骨架，所以会像任何一轮一样在 dashboard 上动起来。

## 把创建的事件镜像到 Google Calendar

本地 SQLite 数据库和 `calendar.ics` 保持权威。要同时把 `create_event` 的结果写进
Google Calendar，装上 opt-in extra 并配置
[Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc)：

```bash
pip install -e '.[gcal]'
# 把下载的客户端文件放在仓库**外面**——它只是 gcloud 的输入，
# gcloud 会把生成的凭据存进 ~/.config/gcloud/。
gcloud auth application-default login \
  --client-id-file=~/.config/pikaka/gcal-client.json \
  --scopes=https://www.googleapis.com/auth/calendar.events
PIKAKA_GOOGLE_CALENDAR=1 pikaka
```

仓库里永远不需要放任何秘密：客户端文件被 `gcloud` 读一次，它铸造的凭据落在
`~/.config/gcloud/`。（`.gitignore` 也拦截 `credentials.json` 和 `*token*.json`，作为
第二道防线。）

目标默认是登录用户的 `primary` 日历；设 `PIKAKA_GOOGLE_CALENDAR_ID` 换别的日历。
`list_events` 仍然读本地数据库。Google 失败永远不会回滚本地事件，且与会者通知被压制
（`sendUpdates=none`）。

## 连接 MCP 服务器

```bash
pip install -e '.[mcp]'
```

创建 `.pikaka/mcp.json`，任何 Model Context Protocol 服务器的工具都会出现在 agent 面前，
命名为 `<server>_<tool>`（并出现在 dashboard 的 Tools ▸ MCP 标签页）：

```json
{"servers": [{"name": "fs", "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]}]}
```

**无 Node 的演示**——仓库里自带一个极小的自包含 Python MCP 服务器：

```bash
cp examples/mcp.demo.json .pikaka/mcp.json   # 指向 examples/mcp_demo_server.py
make dashboard                               # demo_word_count / demo_reverse_text 出现在 Tools 里
```

同样的模式可扩展到任何服务器，你的或厂商的——无需改动 Pikaka 的代码。

> 更多实操细节见 [`mcp.md`](mcp.md)（中文，含踩坑记录）。
