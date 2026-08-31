# MCP 接入指南（pikaka-agent）

> 记录 pikaka-agent 如何接入 Model Context Protocol（MCP）外部工具，以及「加任意 MCP 服务器」的完整操作流程。
> 官方简介见 [`integrations.md`](integrations.md) 的 *Connect MCP servers* 一节；本文是实操 playbook + 踩坑记录。

## 一、原理（30 秒版）

- MCP 工具被「翻译」成和内置工具一模一样的 `Tool` 对象，注册进**同一个** `ToolRegistry`，模型端零感知差异。
- 命名规则：**`<服务器名>_<工具名>`**（如 `weather_get_forecast`、`github_search_code`）。
- **懒加载**：工具要等第一次聊天构建 agent 时才真正注册——重启后光刷新页面，Tools 页还看不到，得先发一条消息。
- 关键文件：
  - `pikaka/tools/mcp_client.py` —— `MCPBridge`（异步桥：起后台 asyncio 事件循环，spawn 子进程 → `list_tools()` → 包成 `Tool`）
  - `pikaka/tools/__init__.py` —— `build_registry()` 里的 MCP 分支（`mcp.json` 存在才连接）

## 二、通用操作流程（加任意 MCP）

### 筛选三问（先过，再动手）

1. **能 stdio 启动吗**？`command` 必须是一条命令行（`npx` / `uvx` / `python -m`），远程 HTTP/SSE 地址**不支持**。
2. **要 key 吗**？免 key 优先（能立刻跑通）；要 key 的知道去哪拿、放哪。
3. **包名对吗**？先 WebSearch 查证，别凭记忆写。

### 执行五步

**① 查环境**（提前排除坑）

```bash
command -v npx uvx node gh python   # 确认都在 PATH
# 接浏览器类（puppeteer）还要确认有没有 Chrome/Edge
```

**② 写配置** —— 往 `.pikaka/mcp.json` 的 `servers` 数组加一个块，四个字段：

```json
{
  "name": "别名",            // 工具会注册成 别名_工具名
  "command": "npx",          // 或 uvx / python 绝对路径
  "args": ["-y", "包名"],     // 要传参放这里（如 --repository 路径）
  "env": { "KEY": "..." }     // 要 key 放这里；免 key 留 {}
}
```

> Windows 路径反斜杠要写成 `\\`（如 `"D:\\pikaka-agent\\workspace"`）。

**③ 连接测试**（关键一步，能提前暴露「包名错 / token 错」）

```bash
cd D:\pikaka-agent
.venv/Scripts/python -c "
from pathlib import Path
from pikaka.tools.mcp_client import MCPBridge
b = MCPBridge(Path('.pikaka/mcp.json'), timeout=60.0)
tools = b.start()
for t in tools:
    print(t.name)
"
```

- 看服务器**自报**的工具清单（动态问出来的，不是硬编码）。
- **要 key 的**：再多调一个只读工具验 token，比如 `b.call('github', 'search_repositories', {'query': 'xxx', 'per_page': 1})`——「能启动」≠「token 对」。

**④ 重启 dashboard**（MCP 懒加载，重启才让下次构建读到）

```powershell
$p = (Get-NetTCPConnection -LocalPort 7777 -State Listen -ErrorAction SilentlyContinue).OwningProcess
if ($p) { Stop-Process -Id $p -Force }
Start-Process -FilePath "D:\pikaka-agent\.venv\Scripts\python.exe" `
  -ArgumentList "-m","pikaka.ops.dashboard" -WorkingDirectory "D:\pikaka-agent" `
  -WindowStyle Hidden -RedirectStandardOutput "D:\pikaka-agent\_dashboard.log" `
  -RedirectStandardError "D:\pikaka-agent\_dashboard.err.log"
```

**⑤ 验证**

```bash
.venv/Scripts/python -c "import json,urllib.request;print(json.loads(urllib.request.urlopen('http://127.0.0.1:7777/api/data').read())['tools']['mcp']['servers'])"
# 预期：列表里出现新名字。再在网页发一条消息，Tools 页出现 别名_* 工具。
```

## 三、当前已接入的 6 个服务器

| 服务器 | 包 | 启动 | key | 工具数 | 作用 |
|---|---|---|---|---|---|
| weather | `@dangahagan/weather-mcp` | npx | 否 | 6 | 天气/预报/预警 |
| fs | `@modelcontextprotocol/server-filesystem` | npx | 否 | 14 | 读写 `workspace/` 文件 |
| fetch | `mcp-server-fetch` | uvx | 否 | 1 | 抓网页全文 |
| memory | `@modelcontextprotocol/server-memory` | npx | 否 | 9 | 知识图谱记忆（实体-关系） |
| time | `mcp-server-time` | uvx | 否 | 2 | 当前时间/时区换算 |
| github | `@modelcontextprotocol/server-github` | npx | **是** | 26 | PR/issue/代码搜索/仓库 |

共 **58 个工具**。配置文件 `.pikaka/mcp.json`（已 gitignore，含 GitHub token，勿外泄）：

```json
{
  "servers": [
    { "name": "weather", "command": "npx", "args": ["-y", "@dangahagan/weather-mcp@latest"], "env": {} },
    { "name": "fs", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "D:\\pikaka-agent\\workspace"], "env": {} },
    { "name": "fetch", "command": "uvx", "args": ["mcp-server-fetch"], "env": {} },
    { "name": "memory", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"], "env": {} },
    { "name": "time", "command": "uvx", "args": ["mcp-server-time"], "env": {} },
    { "name": "github", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "github_pat_<你的token>" } }
  ]
}
```

GitHub token 获取：<https://github.com/settings/tokens> → Generate new token → 建议 fine-grained，权限只读（Contents / Issues / Pull requests = Read-only）。

## 四、踩过的坑

1. **`mcp` 包必须 `<2.0`**：mcp 2.0 把 `Tool.inputSchema` 改名了，导致「连上了但注册失败」（报 `'Tool' object has no attribute 'inputSchema'`）。已在 `pyproject.toml` 锁 `mcp>=1.0,<2.0`（当前装 1.29.0）。
2. **一个服务器挂起会拖崩全部**：`MCPBridge` 是顺序连接，某个服务器卡住（如 puppeteer 下载 Chromium）会让整个 `start()` 超时，连累其它服务器也注册不上。别把会卡的东西放进去。
3. **MCP 懒加载**：工具要第一次聊天才注册（见第一节）。
4. **token 安全**：要 key 的 token 放 `.pikaka/mcp.json`（`.gitignore` 已忽略），别贴进聊天、别提交 git；泄露即 Revoke 重新生成。
5. **Windows 路径**：`mcp.json` 里的路径反斜杠要 `\\`。

## 五、演示台词

- 天气：*「明后两天上海天气怎么样？有雨提醒我别骑车」*
- 文件：*「把 workspace 里所有 .md 的待办汇总成一份」*
- 记忆：*「帮我记住 Alice 在 Acme 工作，她是产品经理」→「Alice 在哪工作？」*
- 时间：*「东京现在几点？」*
- GitHub：*「看看 ShenSeanChen/waku-agent 最近有哪些 issue」* / *「搜索 waku-agent 里用到 LangGraph 的代码」*
