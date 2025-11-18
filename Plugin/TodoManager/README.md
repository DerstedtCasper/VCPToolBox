# TodoManager 插件

一个功能完整的待办事项管理插件，支持添加、查看、完成、删除、编辑、搜索待办事项，以及获取统计信息。

## 功能特性

### 🎯 核心功能
- ✅ **添加待办** - 支持标题、描述、优先级、截止时间、标签
- 📋 **查看列表** - 支持状态筛选、优先级筛选、标签筛选、多种排序
- ✅ **完成待办** - 标记任务为已完成
- 🗑️ **删除待办** - 移除不需要的任务
- ✏️ **编辑待办** - 修改现有任务的各种属性
- 🔍 **搜索功能** - 在标题、描述、标签中搜索关键词
- 📊 **统计信息** - 完成率、优先级分布、即将到期任务等

### 🚀 高级特性
- 🔄 **批量操作** - 支持一次执行多个命令
- 🏷️ **标签管理** - 灵活的标签系统
- ⏰ **到期提醒** - 自动显示即将到期和已逾期的任务
- 📈 **智能排序** - 按优先级、截止时间、创建时间排序
- 💾 **数据持久化** - JSON文件存储，支持自定义路径

## 安装和配置

### 1. 依赖安装
```bash
cd VCPToolBox/Plugin/TodoManager
npm install
```

### 2. 配置文件
编辑 `config.env` 文件：
```env
# 数据存储路径
TODO_DATA_PATH=./PluginData/TodoManager/todos.json

# 默认提醒天数
DEFAULT_REMINDER_DAYS=3

# 最大待办数量限制
MAX_TODOS=1000
```

## 使用方法

### AI调用示例

#### 1. 添加待办事项
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」TodoManager「末」,
command:「始」AddTodo「末」,
title:「始」完成项目报告「末」,
description:「始」准备季度总结报告「末」,
priority:「始」high「末」,
dueDate:「始」2025-08-15「末」,
tags:「始」工作,重要「末」
<<<[END_TOOL_REQUEST]>>>
```

#### 2. 查看待办列表
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」TodoManager「末」,
command:「始」ListTodos「末」,
status:「始」pending「末」,
sortBy:「始」priority「末」
<<<[END_TOOL_REQUEST]>>>
```

#### 3. 完成待办事项
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」TodoManager「末」,
command:「始」CompleteTodo「末」,
title:「始」学习Python「末」
<<<[END_TOOL_REQUEST]>>>
```

#### 4. 搜索待办事项
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」TodoManager「末」,
command:「始」SearchTodos「末」,
keyword:「始」项目「末」,
status:「始」pending「末」
<<<[END_TOOL_REQUEST]>>>
```

#### 5. 获取统计信息
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」TodoManager「末」,
command:「始」GetStats「末」
<<<[END_TOOL_REQUEST]>>>
```

#### 6. 批量操作示例
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」TodoManager「末」,
command1:「始」AddTodo「末」,
title1:「始」任务1「末」,
priority1:「始」high「末」,
command2:「始」AddTodo「末」,
title2:「始」任务2「末」,
priority2:「始」medium「末」,
command3:「始」ListTodos「末」,
status3:「始」pending「末」
<<<[END_TOOL_REQUEST]>>>
```

## 参数说明

### AddTodo 参数
- `title` (必需): 待办事项标题
- `description` (可选): 详细描述
- `priority` (可选): 优先级 (high/medium/low)，默认medium
- `dueDate` (可选): 截止日期，格式YYYY-MM-DD
- `tags` (可选): 标签，多个用逗号分隔

### ListTodos 参数
- `status` (可选): 状态筛选 (pending/completed/all)，默认pending
- `priority` (可选): 优先级筛选 (high/medium/low)
- `tag` (可选): 标签筛选
- `sortBy` (可选): 排序方式 (priority/dueDate/createdAt)，默认priority
- `limit` (可选): 限制返回数量

### CompleteTodo/DeleteTodo 参数
- `id` (推荐): 待办事项ID
- `title` (备选): 通过标题匹配

### EditTodo 参数
- `id` (必需): 待办事项ID
- 其他参数同AddTodo，提供的字段将被更新

### SearchTodos 参数
- `keyword` (必需): 搜索关键词
- `status` (可选): 状态筛选，默认all

## 测试

运行测试脚本：
```bash
node test.js
```

## 数据格式

待办事项数据结构：
```json
{
  "id": "uuid",
  "title": "待办标题",
  "description": "详细描述",
  "priority": "high|medium|low",
  "status": "pending|completed",
  "tags": ["标签1", "标签2"],
  "dueDate": "2025-08-15",
  "createdAt": "2025-08-08T14:00:00Z",
  "completedAt": "2025-08-08T16:00:00Z"
}
```

## 注意事项

1. **数据安全**: 数据存储在本地JSON文件中，请定期备份
2. **性能考虑**: 建议待办事项数量不超过配置的最大限制
3. **日期格式**: 截止日期必须使用YYYY-MM-DD格式
4. **批量操作**: 支持同时执行多个命令，提高效率
5. **错误处理**: 插件包含完善的错误处理和验证机制

## 版本信息

- 版本: 1.0.0
- 作者: VCP Developer
- 许可: MIT