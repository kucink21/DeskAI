DeskAI 使用说明

欢迎使用 DeskAI！这是一款支持多种 AI 大模型的桌面效率工具。

## 核心功能

*   悬浮球: 程序的常驻入口，可拖动，右键可唤出主菜单。
*   快捷键: 在悬浮球 设置菜单或`config.json` 中自定义全局快捷键，随时随地触发 AI 功能。
*   多模态识别: 支持截图、剪贴板文本、拖拽文件至悬浮球（图片、文本、PDF、docx、pptx等）进行智能分析。
*   记忆库：支持用户自定义记忆，每次开始会话时 AI 会拥有保存的记忆。
*   图形化设置: 通过设置菜单，轻松管理 API Key、代理、快捷键和各种操作的提示词。

## 模型选择与速率限制

不同供应商的不同模型对 API 使用率的限制和收费水准不同，详情请参考各个官方文档：

https://ai.google.dev/gemini-api/docs/rate-limits?hl=zh-cn
https://api-docs.deepseek.com/quick_start/pricing
https://platform.openai.com/docs/pricing
https://docs.claude.com/en/api/overview

对于新手，建议从 google gemini API 开始，
你可以从 https://aistudio.google.com/app/apikey 获取免费使用的 API key 。

## 常见问题

Q: 为什么快捷键没反应？
A: 请确保没有和其他应用的快捷键冲突。尽量使用 `Shift`, `Alt`, `Win/Cmd` 组合的、不常用的快捷键。修改快捷键后需要重启程序。

Q: 提示 API Key 错误或请求超时怎么办？
A: 请检查设置菜单中的 API Key 是否正确，并重启程序。网络问题或代理设置不正确也可能导致请求超时。
仔细阅读错误信息，由于 API 订阅和限额问题请前往官方网站进行查询/付费。

---
祝您使用愉快！

本项目开源在：
请关注我的github仓库：https://github.com/michaelz9436/GeminiScreenHelper
欢迎大家讨论和提出问题！