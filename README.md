# DeskAI 屏幕助手 v1

<p align="center">
  <img src="https://raw.githubusercontent.com/michaelz9436/DeskAI/main/assets/title.gif" alt="Gemini Screen Helper Icon" style="max-width:100%;">
</p>

<div align="center">
  <table>
    <tr>
      <td align="center">
        <img src="icon/gemini1.png" width="100px" alt="Gemini Idle"/>
        <br />
        <sub><b>Gemini (待机)</b></sub>
      </td>
      <td align="center">
        <img src="icon/gemini2.png" width="100px" alt="Gemini Session"/>
        <br />
        <sub><b>Gemini (会话)</b></sub>
      </td>
      <td align="center">
        <img src="icon/openai1.png" width="100px" alt="OpenAI Idle"/>
        <br />
        <sub><b>OpenAI (待机)</b></sub>
      </td>
      <td align="center">
        <img src="icon/openai2.png" width="100px" alt="OpenAI Session"/>
        <br />
        <sub><b>OpenAI (会话)</b></sub>
      </td>
    </tr>
    <tr>
      <td align="center">
        <img src="icon/claude1.png" width="100px" alt="Claude Idle"/>
        <br />
        <sub><b>Claude (待机)</b></sub>
      </td>
      <td align="center">
        <img src="icon/claude2.png" width="100px" alt="Claude Session"/>
        <br />
        <sub><b>Claude (会话)</b></sub>
      </td>
      <td align="center">
        <img src="icon/deepseek1.png" width="100px" alt="DeepSeek Idle"/>
        <br />
        <sub><b>DeepSeek (待机)</b></sub>
      </td>
      <td align="center">
        <img src="icon/deepseek2.png" width="100px" alt="DeepSeek Session"/>
        <br />
        <sub><b>DeepSeek (会话)</b></sub>
      </td>
    </tr>
  </table>
</div>

欢迎使用 DeskAI 屏幕助手！本工具可以通过自定义快捷键，快速截屏或使用剪贴板内容，或将文件/文本拖至悬浮球，调用 AI 大模型进行文字识别、翻译或任何你指定的任务。本项目支持自定义记忆库，帮助你更个性化地完成工作！   

目前支持 Gemini，openai，Claude，Deepseek 多种模型的 API 调用！  

**程序已开放下载！** --见 `release` 最新链接。

---
## ✨ 功能演示

#### 场景一：使用悬浮球拖拽分析文件/文本/快速开启会话
![Reading Demo](https://raw.githubusercontent.com/michaelz9436/DeskAI/main/assets/demo12.gif)

#### 场景二：使用快捷键截图/剪贴板内容进行翻译/识别/代码任务
![Reading Demo](https://raw.githubusercontent.com/michaelz9436/DeskAI/main/assets/demo11.gif)

#### 场景三：保存/修改记忆库，以个性化聊天
![Reading Demo](https://raw.githubusercontent.com/michaelz9436/DeskAI/main/assets/demo13.gif)

---

## ✨ 核心特性

*   **智能悬浮球**: 您的桌面AI伙伴，可自由拖动，右键唤出功能菜单。
*   **多模态拖放**: 将图片、文本、PDF、Word、PPT等文件直接拖拽到悬浮球上，即可快速分析与处理。
*   **全局快捷键**: 自定义全局快捷键，随时随地触发截图识别或剪贴板处理。
*   **记忆库设置**：保存你的个人记忆库，使每次聊天都有对你的记忆：个人信息，偏好，任务...。
*   **图形化设置**: 在直观的设置菜单中，轻松管理您的API Key、代理、快捷键和所有AI指令。
*   **系统托盘集成**: 可将悬浮球最小化到系统托盘，保持桌面整洁。

---

## 🚀 首次运行设置 (必读！)

为了让程序正常启动，您**只需要在第一次运行时**手动编辑一次配置文件来填入您的API Key。

1.  **打开config**: 找到和exe相同目录的 `config.json`，用任意文本编辑器打开它 。

2.  **填入 API Key**: 找到 `"api_keys"` 字段的 `"google_gemini"` ，并填入你自己的 Gemini API Key。
    > 其他 API key 可以留空，但是如果下方模型选择了其他模型，请填入对应的 API key。
    > 你可以从 Google AI Studio 免费获取 gemini 的 API: <https://aistudio.google.com/app/apikey>

3.  **启动程序**: 保存config，启动程序使 API 生效。
    > 你可以将程序快捷方式添加到开机启动，不用每次手动运行。

**🎉 恭喜！您只需要完成这一步就能召唤gemini！之后的所有设置都可以在程序内的图形化“设置”菜单中轻松完成。**

---

## 🕹️ 主要功能与使用方法

#### 1. 悬浮球 (The Floating Ball)
这是程序的主入口。
*   **拖动**: 按住鼠标左键可以将其拖动到屏幕的任何位置。
*   **右键菜单**: 右键点击悬浮球，会弹出主功能菜单。

#### 2. 右键菜单 (The Right-Click Menu)
*   **开始新对话**: 快速打开一个聊天窗口，开始与AI的临时对话。
*   **记忆库**: 打开记忆库，存储你的身份/任务/喜好信息。
*   **使用说明**: 打开本帮助文档。
*   **设置**: 打开图形化的设置窗口，管理所有配置。
*   **隐藏悬浮球**: 将悬浮球最小化到系统右下角的托盘区。
*   **退出**: 关闭应用程序。

#### 3. 拖放识别 (Drag & Drop)
将以下内容直接拖到悬浮球上即可触发相应的AI分析：
*   **选中的文本**: 快速翻译、解释或总结。
*   **图片文件**: (`.png`, `.jpg` 等) 描述图片内容。
*   **文档文件**: (`.txt`, `.pdf`, `.docx`, `.pptx` 等) 总结文档核心要点。

#### 4. 全局快捷键 (Global Hotkeys)
在后台随时通过您自定义的快捷键触发特定功能（默认为截图和剪贴板处理）。

---

## ⚙️ 设置菜单详解

通过**右键菜单 -> 设置**打开。在这里，您可以直观地管理所有配置。

#### 1. 通用设置
*   **模型选择**：选择您需要使用的供应商和模型名称，需要填写对应的 API key 才能正常使用。
*   **API Key**: 您的 API 密钥。
*   **代理 URL**: 您的本地网络代理地址。
    *   **留空 (推荐)**: 程序会自动检测系统代理，适应大多数网络环境。
    *   **手动填写**: 如果自动检测失败，请填写完整的代理地址，例如 `http://127.0.0.1:7890`。

#### 2. 快捷键动作
此区域管理通过**快捷键**触发的功能。
*   **快捷键**: 定义触发的按键组合，如 `shift+win+d`。
*   **提示词 (Prompt)**: 定义当该快捷键被触发时，发送给AI的初始指令。

#### 3. 拖放动作
此区域管理**拖放文件**触发的功能。
*   **文件类型**: 以文件扩展名（如 `.pdf`, `.py`）作为标识。
*   **提示词 (Prompt)**: 定义当对应类型的文件被拖放时，发送给AI的初始指令。

> **重要提示**: API Key、代理URL 和快捷键的任何更改，都需要通过**右键菜单 -> 退出**来使新设置生效。

---

## ❓ 常见问题 (FAQ)


**Q: 快捷键按了没反应？**
A: 1. 请检查设置的快捷键是否与系统或其他软件的快捷键冲突。 2. 修改快捷键后，必须**重启**程序才能生效。

**Q: 悬浮球不见了？**
A: 请检查屏幕右下角的系统托盘区，程序图标可能被隐藏在那里。右键点击托盘图标可以选择“显示悬浮球”。

**Q: 提示网络错误或请求超时？**
A: 请检查：1. 您的网络连接是否正常。 2. 您的代理是否开启且设置正确。 3. 您的 API Key 是否有效。

**Q: 无法获取结果？**
A: 请像检测网络和API key是否填写，并关注对话栏报错信息，如果是API配额/支付相关问题，请前往下方官方网站进行支付。

## 🤖 推荐模型选择

不同供应商的模型在 API 使用限制和收费方面有所不同，详情请参考官方文档：

- **Google Gemini**
  - [文档：使用限制](https://ai.google.dev/gemini-api/docs/rate-limits?hl=zh-cn)
  - API Key 获取：[AI Studio](https://aistudio.google.com/app/apikey)

- **DeepSeek**
  - [文档：快速入门与定价](https://api-docs.deepseek.com/quick_start/pricing)

- **OpenAI**
  - [文档：定价说明](https://platform.openai.com/docs/pricing)

- **Claude**
  - [文档：API 概览](https://docs.claude.com/en/api/overview)

> 💡 **新手推荐**：可以先从 Google Gemini API 开始，方便获取免费额度进行尝试。

## 🔒 安全与隐私声明

请在使用本工具前了解以下信息：

1.  **截图内容上传**: 为了实现识别和翻译功能，您截取的屏幕区域图像将会被上传至 供应商 的 模型 API 服务器进行处理。请避免截取包含密码、个人隐私或任何敏感信息的区域。

2.  **全局快捷键监听**: 本程序会在后台监听您的键盘输入，以便响应您设置的全局快捷键。本程序**不会**记录或上传除快捷键组合之外的任何键盘活动。

3.  **杀毒软件警告**: 由于本程序需要监听全局键盘快捷键，部分杀毒软件（包括 Windows Defender）可能会将其标记为潜在风险程序（如 "Keylogger" 或 "监控工具"）。这是一个正常的误报，因为杀毒软件无法区分善意的快捷键功能和恶意的键盘记录。如果您信任本程序的源代码和功能，请选择“允许”或将本程序添加到信任列表。

4.  **配置文件安全**: 您的 API Key 存储在您本地的 `config.json` 文件中，不会被上传或分享。请妥善保管此文件，不要泄露给他人。

**本项目为开源工具，旨在提升效率。我们鼓励您审查源代码以确保其安全性。**