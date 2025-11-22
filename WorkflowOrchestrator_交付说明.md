## 交付包概览
- 管理面板更新包：`WorkflowOrchestrator_AdminPanel_Update.zip`
  - 覆盖文件：`AdminPanel/index.html`、`AdminPanel/script.js`、`AdminPanel/workflow_orchestrator_editor.html`、`AdminPanel/workflow_orchestrator_editor.css`、`AdminPanel/workflow_orchestrator_editor.js`
- 插件包：`WorkflowOrchestrator_Plugin.zip`
  - 路径：`Plugin/WorkflowOrchestrator/*`（含 manifest、核心 JS、示例 workflows.json、config/env 等）

## 部署步骤
1. 备份现有 AdminPanel 与 Plugin/WorkflowOrchestrator 目录（可选，便于回滚）。
2. 解压 `WorkflowOrchestrator_AdminPanel_Update.zip`，覆盖到服务器的 AdminPanel 目录。
   - `index.html` 已加入导航入口和 iframe。
   - `script.js` 支持工作流页 iframe 重载。
   - 工作流编辑器 HTML/CSS/JS 已修复乱码，内置示例兜底，首屏即显示 `GenericTaskFlow`。
3. 解压 `WorkflowOrchestrator_Plugin.zip` 到 `Plugin/WorkflowOrchestrator/`，覆盖同名文件。
4. 重启或热重载后端（确保新静态文件被加载，插件重新初始化）。
5. 打开 AdminPanel → “AA 工作流编排”：
   - 首屏应立即出现示例工作流与示例 Agents；若后端接口可用，会自动替换为真实数据。
   - 如仍空白/卡加载，请在浏览器控制台检查 `admin_api/workflow-orchestrator/*` 请求是否 401/超时；需要确保面板请求带上管理凭证。

## 变更要点（便于测试）
- UI：暗色统一风格，通用 Prompt/阶段描述文本域已扩大并适配主题。
- JS：增加请求超时（6s）与初始化兜底（8s），接口异常时自动切换内置示例；日志输出更清晰。
- 导航：侧边栏新增“AA 工作流编排”，内容区新增 iframe section，切换时自动重载。

## 验收检查清单
- [ ] AdminPanel 侧边栏显示“AA 工作流编排”并可切换。
- [ ] 进入页面即能看到 `GenericTaskFlow` 示例，Commander/参与者列表可勾选。
- [ ] “刷新列表 / 重新加载 / 保存配置”按钮有状态提示且无前端报错。
- [ ] 后端接口可用时，示例被真实数据替换；接口异常时仍可编辑示例并保存（会报错提示）。
