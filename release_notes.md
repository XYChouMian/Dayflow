## Dayflow v1.5.2

### 🛠 Issue 修复版本

本版本主要整理并发布了近期针对 issue 的修复内容。

### ✅ 已修复

- 修复部分 OpenAI / Gemini 兼容代理返回结构导致的解析报错
- 增强 dxcam 初始化兼容性，降低部分机器上录制启动失败的问题
- 优化文件名 / 页面名线索提取，提升活动分析的具体度
- 新增多显示器手动选择录制屏幕（设置页可配置）
- 修复 Windows 控制台下打包脚本可能出现的编码报错

### 📦 安装说明

1. 下载 `Dayflow-v1.5.2-windows.zip`
2. 解压到任意目录
3. 运行 `Dayflow.exe`
4. 请保留同目录下的 `_internal` 文件夹

### 💡 API 配置

支持任意 OpenAI 兼容接口：
- OpenAI: `https://api.openai.com/v1`
- DeepSeek: `https://api.deepseek.com/v1`
- 心流 API: `https://apis.iflow.cn/v1`
- Ollama: `http://localhost:11434/v1`
