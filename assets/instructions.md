GeminiHelper 使用说明

欢迎使用 GeminiHelper！这是一款由 Gemini AI 驱动的桌面效率工具。

## 核心功能

*   悬浮球: 程序的常驻入口，可拖动，右键可唤出主菜单。
*   快捷键: 在悬浮球 设置菜单或`config.json` 中自定义全局快捷键，随时随地触发 AI 功能。
*   多模态识别: 支持截图、剪贴板文本、拖拽文件（图片、文本、PDF、docx、pptx等）进行智能分析。
*   图形化设置: 通过设置菜单，轻松管理 API Key、代理、快捷键和各种操作的提示词。

## 模型选择与速率限制

下面表格列出了 Gemini 模型的部分参数。选择合适的模型可以在成本和性能之间取得平衡。

*   TPM: 每分钟允许的最大请求数 (Tokens Per Minute)。
*   RPD: 每天允许的最大请求数 (Requests Per Day)。

更详细的信息可以参考官方文档：Gemini API 速率限制 (https://ai.google.dev/pricing)

型号	                每千次展示收入	 TPM	      RPD
--------------------------------------------------------
Gemini 2.5 Pro	        5	           250,000	    100
Gemini 2.5 Flash	    10	           250,000	    250
Gemini 2.5 Flash-Lite	15	           250,000  	1000
Gemini 2.0 Flash	    15	           1,000,000	200
Gemini 2.0 Flash-Lite	30	           1,000,000	200

注意: 表格内容仅供参考，请以Google官方文档为准。

## 常见问题

Q: 为什么快捷键没反应？
A: 请确保没有和其他应用的快捷键冲突。尽量使用 `Shift`, `Alt`, `Win/Cmd` 组合的、不常用的快捷键。修改快捷键后需要重启程序。

Q: 提示 API Key 错误或请求超时怎么办？
A: 请检查设置菜单中的 API Key 是否正确，并重启程序。网络问题或代理设置不正确也可能导致请求超时。

---
祝您使用愉快！
请关注我的github仓库：https://github.com/michaelz9436/GeminiScreenHelper