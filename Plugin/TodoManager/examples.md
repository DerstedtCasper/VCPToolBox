# TodoManager 插件使用示例

## 基础使用示例

### 1. 添加日常任务
```
AI: 帮我添加一个待办事项：明天下午完成周报
```
AI会调用：
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」TodoManager「末」,
command:「始」AddTodo「末」,
title:「始」完成周报「末」,
description:「始」明天下午完成「末」,
priority:「始」medium「末」,
dueDate:「始」2025-08-09「末」,
tags:「始」工作「末」
<<<[END_TOOL_REQUEST]>>>
```

### 2. 查看今天的任务
```
AI: 显示我今天需要完成的待办事项
```
AI会调用：
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」TodoManager「末」,
command:「始」ListTodos「末」,
status:「始」pending「末」,
sortBy:「始」priority「末」
<<<[END_TOOL_REQUEST]>>>
```

### 3. 标记任务完成
```
AI: 我已经完成了周报，请标记为完成
```
AI会调用：
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」TodoManager「末」,
command:「始」CompleteTodo「末」,
title:「始」完成周报「末」
<<<[END_TOOL_REQUEST]>>>
```

## 高级使用示例

### 1. 项目管理场景
```
AI: 帮我为新项目创建几个待办事项
```
AI会调用批量操作：
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」TodoManager「末」,
command1:「始」AddTodo「末」,
title1:「始」项目需求分析「末」,
priority1:「始」high「末」,
dueDate1:「始」2025-08-12「末」,
tags1:「始」项目,分析「末」,
command2:「始」AddTodo「末」,
title2:「始」技术方案设计「末」,
priority2:「始」high「末」,
dueDate2:「始」2025-08-15「末」,
tags2:「始」项目,设计「末」,
command3:「始」AddTodo「末」,
title3:「始」开发环境搭建「末」,
priority3:「始」medium「末」,
tags3:「始」项目,环境「末」
<<<[END_TOOL_REQUEST]>>>
```

### 2. 学习计划管理
```
AI: 帮我制定一个学习Python的计划
```
AI会调用：
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」TodoManager「末」,
command1:「始」AddTodo「末」,
title1:「始」学习Python基础语法「末」,
priority1:「始」high「末」,
dueDate1:「始」2025-08-15「末」,
tags1:「始」学习,Python「末」,
command2:「始」AddTodo「末」,
title2:「始」完成Python练习题「末」,
priority2:「始」medium「末」,
dueDate2:「始」2025-08-20「末」,
tags2:「始」学习,Python,练习「末」,
command3:「始」AddTodo「末」,
title3:「始」开发一个小项目「末」,
priority3:「始」medium「末」,
dueDate3:「始」2025-08-25「末」,
tags3:「始」学习,Python,项目「末」
<<<[END_TOOL_REQUEST]>>>
```

### 3. 任务搜索和管理
```
AI: 搜索所有与"学习"相关的待办事项
```
AI会调用：
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」TodoManager「末」,
command:「始」SearchTodos「末」,
keyword:「始」学习「末」,
status:「始」all「末」
<<<[END_TOOL_REQUEST]>>>
```

### 4. 获取工作统计
```
AI: 显示我的待办事项完成情况统计
```
AI会调用：
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」TodoManager「末」,
command:「始」GetStats「末」
<<<[END_TOOL_REQUEST]>>>
```

## 自然语言交互示例

### 用户可以这样说：
- "帮我添加一个高优先级的任务：明天开会前准备PPT"
- "显示所有工作相关的未完成任务"
- "我完成了Python学习，请标记为完成"
- "删除那个过期的任务"
- "把学习计划的截止时间改到下周五"
- "搜索所有包含'项目'的待办事项"
- "显示我这个月的任务完成情况"

### AI会智能解析并调用相应的插件功能：
- 自动识别优先级关键词（重要、紧急、高优先级等）
- 解析时间表达（明天、下周、本月等）
- 提取标签信息（工作、学习、项目等）
- 匹配任务标题进行操作

## 批量操作示例

### 周计划制定
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」TodoManager「末」,
command1:「始」AddTodo「末」,
title1:「始」周一：团队会议「末」,
priority1:「始」high「末」,
dueDate1:「始」2025-08-11「末」,
tags1:「始」工作,会议「末」,
command2:「始」AddTodo「末」,
title2:「始」周三：项目评审「末」,
priority2:「始」high「末」,
dueDate2:「始」2025-08-13「末」,
tags2:「始」工作,评审「末」,
command3:「始」AddTodo「末」,
title3:「始」周五：代码提交「末」,
priority3:「始」medium「末」,
dueDate3:「始」2025-08-15「末」,
tags3:「始」工作,开发「末」,
command4:「始」ListTodos「末」,
status4:「始」pending「末」,
sortBy4:「始」dueDate「末」
<<<[END_TOOL_REQUEST]>>>
```

## 错误处理示例

### 无效输入处理
```json
// 输入：空标题
{"command":"AddTodo","title":"","priority":"high"}
// 输出：
{"status":"error","result":"标题不能为空"}

// 输入：无效日期
{"command":"AddTodo","title":"测试","dueDate":"2025-13-45"}
// 输出：会忽略无效日期，使用null

// 输入：未知命令
{"command":"UnknownCommand"}
// 输出：
{"status":"error","result":"未知命令: UnknownCommand"}
```

## 数据持久化

所有待办事项数据都保存在 `VCPToolBox/PluginData/TodoManager/todos.json` 文件中，格式如下：

```json
{
  "todos": [
    {
      "id": "uuid-string",
      "title": "完成项目报告",
      "description": "准备季度总结报告",
      "priority": "high",
      "status": "pending",
      "tags": ["工作", "重要"],
      "dueDate": "2025-08-15",
      "createdAt": "2025-08-08T14:00:00Z",
      "completedAt": null
    }
  ]
}
```

## 集成到VCP系统

1. 确保插件目录在 `VCPToolBox/Plugin/TodoManager/`
2. 在AI的系统提示词中添加占位符：`{{VCPTodoManager}}`
3. VCP主服务会自动加载插件并将功能描述注入到AI的系统提示词中
4. AI就可以根据用户需求自动调用待办管理功能了

## 性能优化建议

1. **定期清理**：删除过期的已完成任务
2. **标签管理**：使用一致的标签命名规范
3. **批量操作**：对于多个相关任务，使用批量添加
4. **数据备份**：定期备份 todos.json 文件