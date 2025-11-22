# Workflow Orchestrator 插件使用说明

## 概览
- 插件类型：hybridservice（direct）
- 功能：从 AgentAssistant 注册名单中选择总指挥与参与者，定义/调整多 Agent 工作流，执行时调度各 Agent 协作，并将状态、日志、错误反馈给用户。
- 关键能力：
  - 自动读取 `Plugin/AgentAssistant/config.env` 的 Maid 列表（AA Agents）。
  - AdminPanel 可视化配置页面（Workflow Orchestrator 编辑）。
  - 工作流定义持久化到 `workflows.json`，实例状态持久化到 `runtime_state/*.json`。
  - 运行时支持重试、fallback agent 调试提示、动态 `WORKFLOW_OVERRIDE` 插入/跳过/改角色、同层并行执行、调试日志写入 `dailynote/WorkflowDebugLogs`。

## 管理接口（Admin API）
以下接口已在 `routes/adminPanelRoutes.js` 暴露（均以 `/admin_api` 为前缀）：
- `GET /workflow-orchestrator/agents`：列出 AA 注册的 Agent。
- `GET /workflow-orchestrator/workflows`：读取当前 workflow 配置。
- `POST /workflow-orchestrator/configure`：快速生成/更新工作流。Body 示例：
  ```json
  {
    "workflow_name": "MyFlow",
    "commander_agent": "灏忓悏",
    "participant_agents": ["策略代码手", "错误调试顾问"],
    "stages_text": "阶段1：优化任务\n阶段2：拆解并分配\n阶段3：执行\n阶段4：审核\n阶段5：总结输出"
  }
  ```
- `POST /workflow-orchestrator/reload`：重载 `workflows.json`。

插件命令（可通过 TOOL_REQUEST 或 /v1/human/tool 调用）：
- `StartWorkflow`：启动工作流实例（params: workflow_name, user_task, session_id?）。
- `GetWorkflowStatus`：查询实例状态（params: workflowInstanceId）。
- `ListWorkflows` / `ListAAAgents` / `ConfigureWorkflow` / `UpdateWorkflows` / `ReloadWorkflows`（供管理用）。

## AdminPanel 可视化配置
在 AdminPanel 导航中新增“Workflow Orchestrator 编辑”，页面文件：
- `AdminPanel/workflow_orchestrator_editor.html`
- `AdminPanel/workflow_orchestrator_editor.js`

页面功能：
- 自动加载 AA Agent 列表，选择总指挥，下方勾选参与者。
- 输入工作流名称与阶段文本（每行一阶段，总指挥在运行时可进一步细化/调整）。
- 按钮：刷新 Agent、保存/配置工作流（调用 configure 接口）、重载配置。
- 右侧显示当前 workflows.json 内容。

## 工作流执行要点
- 执行入口：`StartWorkflow`。内部采用就绪队列，同层并行，依赖死锁会失败并写日志。
- 重试：每步按 workflow 或全局配置重试；可设置 fallback agent 生成调试提示再重试。
- 动态调整：支持在子 Agent 输出中加入 `<<WORKFLOW_OVERRIDE>> ... <<END_WORKFLOW_OVERRIDE>>` 插入/跳过/改角色。
- 状态：通过 WebSocket `pushVcpInfo` 推送 `WORKFLOW_STATUS`；实例状态持久在 runtime_state/*.json，供 `GetWorkflowStatus` 查询。
- 日志：`dailynote/WorkflowDebugLogs` 写入 Markdown，记录步骤状态、结果、错误。

## AA 工具调用修复
- AgentAssistant 插件改用 `/v1/chatvcp/completions`，保证工具调用链（含子 Agent 工具）会执行并返回结果；超时提升到 300 秒。

## 手工文件
- `Plugin/WorkflowOrchestrator/workflows.json`：工作流定义（可被 AdminPanel 管理接口读写）。
- `Plugin/WorkflowOrchestrator/config.env`：重试/调试/日志目录配置。
- `Plugin/WorkflowOrchestrator/runtime_state/`：实例状态快照（重启后自动加载）。

## 快速示例（TOOL_REQUEST 启动）
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」WorkflowOrchestrator「末」,
command:「始」StartWorkflow「末」,
workflow_name:「始」GenericTaskFlow「末」,
user_task:「始」请审查项目 README 并输出改进建议「末」
<<<[END_TOOL_REQUEST]>>>
```

## 注意
- 若 AdminPanel 看不见新入口，刷新静态资源（清缓存）并确认后端已重启加载更新文件。
- 若只存在压缩包而无插件目录，需解压到 `Plugin/WorkflowOrchestrator/` 后重启。 
