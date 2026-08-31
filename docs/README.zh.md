# docs —— 这里有什么

> 本文是 [`README.md`](README.md) 的中文翻译。以英文原稿为准；如有出入，以原文为准。

十二个文件没有顺序，就是一个没人会读的文件夹。分成三组。

## 参考 —— 系统如何运作

| 文件 | 它回答的问题 |
|---|---|
| [architecture.md](architecture.md) | 四大支柱，以及哪个文件对应图上的哪个框 |
| [loop-vs-graph.md](loop-vs-graph.md) | 什么时候一轮需要形状，以及为什么循环永不改变 |
| [agent-graphs-design.md](agent-graphs-design.md) | 图引擎的设计和它的 fail-open 规则 |
| [memory-backends-playbook.md](memory-backends-playbook.md) | 在每个提供方自己的控制台里看你的记忆 |
| [benchmarks.md](benchmarks.md) | 测了什么，以及怎么测 |
| [integrations.md](integrations.md) | 语音、Telegram、Apple、Google Calendar、MCP——全是 opt-in |

## 专题文章 —— 一个主题，讲清楚

| 文件 | 它是什么 |
|---|---|
| [kimi-k3-explained.md](kimi-k3-explained.md) | K3 模型，以及竞技场发现了什么 |
| [pi-agent.md](pi-agent.md) | 把编程工作委托给 pi |
| [stack-report.md](stack-report.md) | 这个仓库构建在什么之上、为什么 |

## notes/ —— 工作材料，不是参考

拍摄清单、分镜脚本和 prompt——包括
[memory-video-rundown.md](notes/memory-video-rundown.md)，那是记忆层对比的逐镜头
脚本。有用、带日期，但**不是**学习任何东西怎么运作的地方——它们默认你已经懂了。

## 白板

[whiteboards/](whiteboards/) 存放视频里那些可编辑的 `.excalidraw` 板子。它们由
`pikaka/ops/whiteboard/build_*.py` 生成，这样才能和手绘母版一致；改构建脚本，别改
JSON。

相关、且刻意**不**放在 `docs/` 里的：[../examples/](../examples/) 是可运行的教学材料
——每个主题一个文件夹，`pikaka/` 下没有任何东西 import 它。见 `CLAUDE.md` 里保证它
诚实的四条规则。
