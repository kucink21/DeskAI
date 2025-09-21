# Gemini 屏幕助手 v1

<p align="center">
  <img src="https://raw.githubusercontent.com/michaelz9436/GeminiScreenHelper/main/assets/google-gemini-icon.ico" alt="Gemini Screen Helper Icon" width="100">
</p>

欢迎使用 Gemini 屏幕助手！本工具可以通过自定义快捷键，快速截屏或使用剪贴板内容，并调用 Google Gemini 模型进行文字识别、翻译或任何你指定的任务。  
程序已开放下载！ --见 `release`

---
## ✨ 功能演示

#### 场景一：使用快捷截图进行翻译/识别/代码
![Reading Demo](https://raw.githubusercontent.com/michaelz9436/GeminiScreenHelper/main/assets/merged_demo1.gif)

#### 场景二：使用剪贴板内容快捷翻译/识别
![Coding Demo](https://raw.githubusercontent.com/michaelz9436/GeminiScreenHelper/main/assets/merged_demo2.gif)

---

## 🚀 快速上手指南

1.  **编辑配置文件**:
    在程序目录下找到 `config.json` 文件，并使用记事本或任何文本编辑器打开它。

2.  **填入 API Key**:
    将 `"api_key"` 字段的值替换成你自己的 Gemini API Key。
    > 你可以从 Google AI Studio 免费获取: <https://aistudio.google.com/app/apikey>

3.  **检查代理配置**:
    通常情况下，程序会自动检测代理端口。如果运行时出现报错，请检测`log.txt`

4.  **设置快捷键**:
    在 `config.json` 文件中设置你喜欢的组合键，用于随时调用截图和剪贴板工具。

5.  **运行程序**:
    双击运行 `GeminiHelper.exe`。程序会静默在后台运行。按下你设定的快捷键即可开始使用！
    > **提示**: 你可以将程序的快捷方式放入系统的“启动”文件夹，实现开机自启。

---

## ⚙️ 配置文件 (`config.json`) 详解

`config.json` 文件包含以下可配置项：

#### 1. `"api_key"` (必需)
你的 Google Gemini API 密钥。这是程序的核心，必须填写。
- **示例**: `"AIzaSy...你的真实密钥..."`

#### 2. `"proxy_url"` (可选)
你的本地网络代理地址。设置为空字符串 `""`时，程序会自动寻找代理端口，通常能适应一般的vpn环境。
如果代理出问题，请检查log.txt，并尝试手动设置代理端口，如：`"http://127.0.0.1:7890"` <- 确认这个端口

#### 3. `"hotkey"` (必需)
触发截图和发送剪贴板的全局快捷键。
- 使用 `+` 连接按键。
- 支持的修饰键: `shift`, `ctrl`, `alt`, `cmd` (Win键)。
- 普通按键请使用单个小写字母或数字，如 `d`, `q`, `1`。
- **示例**: `"shift+cmd+d"`

#### 4. `"model_name"` (必需)
指定程序调用的 Gemini 模型。不同的模型在性能、速度和免费配额上有所不同。请从下方的推荐模型中选择一个填入。
- **建议**: 使用 `"gemini-2.5-flash-lite"` 以获得最佳的免费额度和速度。
- **示例**: `"gemini-2.5-flash-lite"`

#### 5. `"initial_prompt"` (必需)
每次截图后，发送给模型的初始指令。你可以根据自己的需求随意修改！
- **示例 (翻译)**: `"将图中的文本信息提取出来，并翻译成中文。"`
- **示例 (代码解释)**: `"提取图中的代码，并用中文解释它的功能和逻辑。"`
- **示例 (识别万物)**: `"详细描述这张图片里的内容。"`

---

## 🤖 推荐模型选择

下面表格列出了 Gemini 模型的部分参数。  

- **TPM**: 每分钟允许的最大请求数（Transactions Per Minute）。  
- **RPD**: 每天允许的最大请求数（Requests Per Day）。  

模型选择可以参考官方文档：[Gemini API 速率限制](https://ai.google.dev/gemini-api/docs/rate-limits?hl=zh-cn)。

| 型号 | 每千次展示收入 | TPM | RPD |
|------|----------------|-----|-----|
| Gemini 2.5 Pro       | 5   | 250,000 | 100   |
| Gemini 2.5 Flash     | 10  | 250,000 | 250   |
| Gemini 2.5 Flash-Lite| 15  | 250,000 | 1000  |
| Gemini 2.0 Flash     | 15  | 1,000,000 | 200  |
| Gemini 2.0 Flash-Lite| 30  | 1,000,000 | 200  |

---

## 🛠️ 故障排查
-   如果程序启动时报错，请首先检查 `config.json` 的格式是否正确（例如，逗号、引号是否完整）。
-   如果快捷键无响应，请确保没有其他程序占用了相同的快捷键。
-   如果API调用失败，请检查 API Key 是否正确、网络代理是否开启并设置正确。

---

## 🔒 安全与隐私声明

请在使用本工具前了解以下信息：

1.  **截图内容上传**: 为了实现识别和翻译功能，您截取的屏幕区域图像将会被上传至 Google 的 Gemini API 服务器进行处理。请避免截取包含密码、个人隐私或任何敏感信息的区域。

2.  **全局快捷键监听**: 本程序会在后台监听您的键盘输入，以便响应您在 `config.json` 中设置的全局快捷键。本程序**不会**记录或上传除快捷键组合之外的任何键盘活动。

3.  **杀毒软件警告**: 由于本程序需要监听全局键盘快捷键，部分杀毒软件（包括 Windows Defender）可能会将其标记为潜在风险程序（如 "Keylogger" 或 "监控工具"）。这是一个正常的误报，因为杀毒软件无法区分善意的快捷键功能和恶意的键盘记录。如果您信任本程序的源代码和功能，请选择“允许”或将本程序添加到信任列表。

4.  **配置文件安全**: 您的 Gemini API Key 存储在您本地的 `config.json` 文件中，不会被上传或分享。请妥善保管此文件，不要泄露给他人。

**本项目为开源工具，旨在提升效率。我们鼓励您审查源代码以确保其安全性。**