# Obsidian 用户配置清单

修改仓库内容前执行本阶段。只向用户说明缺少的操作，禁止使用 computer-use、浏览器控制、Chrome 控制或其他界面自动化代替用户操作。

## 检查项目

1. 确认所选仓库已经生成 `.obsidian`。
2. 仅在社区插件尚未启用时，提示用户打开“设置 → 第三方插件”并关闭受限模式。
3. 检查 Claudian 是否已安装并启用。它是唯一必需插件；根据插件清单名称识别，同时接受当前 ID `realclaudian` 和旧 ID。
4. 显示当前机器检测到的 Codex CLI 绝对路径。该路径必须通过版本和 app-server 探测，拒绝不可访问的 WindowsApps 包路径。
5. 禁止新建 Claudian 对话、读取模型列表或发送测试请求。服务商兼容性不属于初始化条件。

禁止编辑插件 JSON 文件。已经完成的项目不再向用户显示。

## 通过条件

- 仓库包含 `.obsidian`；
- Claudian 已启用；
- Codex CLI 版本与 app-server 探测通过；
- 存在经过验证的 Codex CLI 路径；
- 仓库中未写入 API Key 或登录信息。
