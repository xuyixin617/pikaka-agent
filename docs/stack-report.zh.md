# 技术栈报告 —— 核实于 2026-07-10

> 本文是 [`stack-report.md`](stack-report.md) 的中文翻译。以英文原稿为准；如有出入，以原文为准。

简报（§7）要求在构建前做一轮「先研究后核实」。结果：下面每一层都装进了同一个 venv
（Python 3.13、uv），并做了端到端冒烟测试。

## 选定的技术栈（以及被否决的）

| 层 | 选择 | 核实的版本 | 否决 & 原因 |
|---|---|---|---|
| 循环 / 骨架 | 在 Anthropic SDK 上手写 ~150 行循环 | `anthropic 0.116.0` | PydanticAI（很好，但会藏起我们正在教的循环）；smolagents（HF 实验梯队）；PocketFlow（图抽象，不是循环）；launch-DeepResearch-Backend 的 LangGraph（拖进整个 LangChain 技术栈——见下） |
| 记忆 | 在 SQLite + FTS5（stdlib）上手建 3 支柱 | Python 3.13 stdlib，FTS5 已确认 | mem0 / Letta / Zep-Graphiti 恰好把视频要教的东西（巩固 + 检索门控）黑箱化。在 README 里列为生产替代品 |
| 向量升级路径 | Supabase pgvector 适配器（取自 launch-agentic-rag） | 可选 extra `[supabase]` | Chroma/Qdrant：又多一个要跑的服务；sqlite-vec：仍是 v1 前的 alpha |
| 评估——确定性 | 对工具调用做纯 pytest 断言 | `pytest 9.1.1` | —（这一侧必须**不用** LLM；这正是重点） |
| 评估——LLM 当裁判 | DeepEval（GEval），pytest 原生 | `deepeval 4.0.8` | promptfoo：断言强但 YAML 驱动 + Node CLI，在 Python 仓库里可教性差一些 |
| 追踪 / LLM Ops | 每次运行一份 JSONL trace + OTel spans → 本地 Arize Phoenix | `arize-phoenix 17.23.0`，OTLP gRPC | Langfuse v3 自托管需要 ~6 个容器（web、worker、Postgres、ClickHouse、Redis、MinIO）——对 clone-and-run 太重。Langfuse **云** 仍可通过同一个 OTel 环境开关使用 |
| 网关 | CLI REPL 默认；Telegram 长轮询可选 | extra `[telegram]`（`python-telegram-bot >=21`） | WhatsApp：Meta Business Cloud API 需要企业认证 + 公开 webhook——推迟为社区贡献 |

## 跑过的冒烟测试（全部通过）

1. **SQLite FTS5**：虚拟表 + `MATCH` 排序查询在 stdlib `sqlite3` 里可用——无需安装。
2. **Phoenix + OTel**：`python -m phoenix.server.main serve` 约 1 秒在 `localhost:6006`
   起来；一棵假的 `agent_run → retrieval_gate → tool.create_event` span 树通过 OTLP
  （`localhost:4317`）导出，并出现在 Phoenix API 里（`traceCount: 1`）。
3. **DeepEval**：自定义确定性 `BaseMetric`（不用 LLM）测量并通过；`GEval` 可干净导入，
   用于裁判套件。
4. **Anthropic SDK**：0.116.0 可导入。实时的工具使用往返待 `.env` 里有
  `ANTHROPIC_API_KEY`（刻意不从其他仓库的 secret 里取）。

## 为什么不扩展 launch-DeepResearch-Backend 的循环（简报问的）

深入探索过：它是 `open_deep_research` 的 LangGraph `StateGraph` fork——supervisor
扇出、研究专用状态和 prompt、硬 LangChain 耦合。值得保留的*模式*（按名索引的 tools
dict、用 `asyncio.gather` 并行派发、安全执行包装器）在这里用纯 Python 重新实现于
`pikaka/loop/agent.py`。
