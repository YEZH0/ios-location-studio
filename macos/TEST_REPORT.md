# macOS 验证记录 · 2026-11-17

实际执行者：本聊天 AI Agent；开发自测，不是独立 QA / 审计通过结论。
环境：macOS 27.0.1 (26A434), arm64, Python 3.13.14, uv 0.13.8。

## 内部核验

- `uv sync --locked` 成功；独立 macos 虚拟环境与锁文件。
- `QT_QPA_PLATFORM=offscreen uv run --no-sync pytest -q`：48 passed。
- 其中上游 37 项，新增 11 项覆盖坐标边界、ACK 与人工验证分离、Qt 界面离线状态、
  模拟设备事件、错误脱敏、重复启动阻断、SIGINT 停止、超时与认证子进程清理。
- 26 个上游 tracked 文件与固定版本逐字节一致。
- Qt 离屏界面实际渲染并检查：主窗口、坐标选择、状态与验证按钮可见。
  原生 macOS 缩放 / VoiceOver 及不同屏幕尺寸尚未完整验证。
- PyInstaller 首次生成 arm64 .app；打包工作进程成功执行设备检测。
  首次源码归档因 HEAD 尚不包含新文件失败，已调整为提交源码后重建。
- 沙箱工作进程当前无设备时正确拒绝启动 probe，没有发送坐标。
- 完整 Qt 安装与依赖构建较大；后续可评估仅使用 Essentials 精简发行体积。

## 实机范围

老板提供：此前上游 CLI 同一聊天完成纽约坐标测试，并确认恢复真实定位。
该记录不替代新 Mac 应用验收。新应用不自动据此标记验证成功。
本轮新应用 Engine（Qt 控制器 + 受沙箱限制的上游 worker）实机记录：
- iPhone 15 / iOS 27.0.1：重新插拔后 USB/CarKit、识别、认证成功。probe 正常退出，坐标发送 0。
- send：40.7128, -74.0060，180 秒，95 个定位包 ACK，正常到期退出，退出码 0。
- 老板两次反馈仍在真实位置，且确认已经切换定位服务仍未改变：本轮位置采纳验证不通过。
- 停止后进程扫描未见 worker/helper 残留；未变更系统配置或核心协议。
- 独立 GUI 操作全流程和打包版真机定位尚未验收；不得把引擎测试称作整个 GUI 通过。
- 老板已确认断开 USB，苹果地图真实位置正常。

## 发布门禁

源码只在 macos/ 和指定 Mac workflow。Windows、根公共文件未修改。
未完成独立 QA、安全 / 法律 / 依赖源码发行审查、Developer ID 签名、公证、Intel 测试。
CI workflow 已提供；本次观察到 Mac PR workflow 被取消，不能计为通过。
本地最终 PyInstaller 构建成功，约 186 MB；codesign 显示 ad-hoc、无 TeamIdentifier。
打包目录扫描 .p7b/.pk8 数量为 0。仅草稿 PR，不代表可正式发布。
Git HTTPS 缺少本机凭据，使用已连接 GitHub 插件上传分支；本地与远程代码树保持一致。
