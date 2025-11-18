const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

class TodoManager {
    constructor() {
        // 从环境变量获取配置，如果没有则使用默认值
        this.dataPath = process.env.TODO_DATA_PATH || './PluginData/TodoManager/todos.json';
        this.defaultReminderDays = parseInt(process.env.DEFAULT_REMINDER_DAYS) || 3;
        this.maxTodos = parseInt(process.env.MAX_TODOS) || 1000;
        
        // 确保数据目录存在
        this.ensureDataDirectory();
        
        // 加载数据
        this.data = this.loadData();
    }

    ensureDataDirectory() {
        const dir = path.dirname(this.dataPath);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
    }

    loadData() {
        try {
            if (fs.existsSync(this.dataPath)) {
                const rawData = fs.readFileSync(this.dataPath, 'utf8');
                return JSON.parse(rawData);
            }
        } catch (error) {
            console.error('加载数据失败:', error.message);
        }
        
        // 返回默认数据结构
        return { todos: [] };
    }

    saveData() {
        try {
            fs.writeFileSync(this.dataPath, JSON.stringify(this.data, null, 2), 'utf8');
            return true;
        } catch (error) {
            console.error('保存数据失败:', error.message);
            return false;
        }
    }

    // 添加待办事项
    addTodo(params) {
        const { title, description = '', priority = 'medium', dueDate, tags = '' } = params;
        
        if (!title || title.trim() === '') {
            return { success: false, error: '标题不能为空' };
        }

        if (this.data.todos.length >= this.maxTodos) {
            return { success: false, error: `待办事项数量已达到上限 (${this.maxTodos})` };
        }

        // 验证优先级
        const validPriorities = ['high', 'medium', 'low'];
        const finalPriority = validPriorities.includes(priority) ? priority : 'medium';

        // 处理标签
        const tagArray = tags ? tags.split(',').map(tag => tag.trim()).filter(tag => tag) : [];

        // 验证日期格式
        let finalDueDate = null;
        if (dueDate) {
            const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
            if (dateRegex.test(dueDate)) {
                const date = new Date(dueDate);
                if (!isNaN(date.getTime())) {
                    finalDueDate = dueDate;
                }
            }
        }

        const todo = {
            id: uuidv4(),
            title: title.trim(),
            description: description.trim(),
            priority: finalPriority,
            status: 'pending',
            tags: tagArray,
            dueDate: finalDueDate,
            createdAt: new Date().toISOString(),
            completedAt: null
        };

        this.data.todos.push(todo);
        
        if (this.saveData()) {
            return {
                success: true,
                message: `✅ 待办事项已添加成功！\n📝 标题: ${todo.title}\n🔸 优先级: ${this.getPriorityEmoji(todo.priority)} ${this.getPriorityText(todo.priority)}\n📅 截止日期: ${todo.dueDate || '未设置'}\n🏷️ 标签: ${todo.tags.length > 0 ? todo.tags.join(', ') : '无'}\n🆔 ID: ${todo.id}`,
                todo: todo
            };
        } else {
            return { success: false, error: '保存数据失败' };
        }
    }

    // 列出待办事项
    listTodos(params = {}) {
        const { status = 'pending', priority, tag, sortBy = 'priority', limit } = params;
        
        let todos = [...this.data.todos];

        // 状态筛选
        if (status !== 'all') {
            todos = todos.filter(todo => todo.status === status);
        }

        // 优先级筛选
        if (priority) {
            todos = todos.filter(todo => todo.priority === priority);
        }

        // 标签筛选
        if (tag) {
            todos = todos.filter(todo => todo.tags.includes(tag));
        }

        // 排序
        todos.sort((a, b) => {
            switch (sortBy) {
                case 'priority':
                    const priorityOrder = { 'high': 3, 'medium': 2, 'low': 1 };
                    return priorityOrder[b.priority] - priorityOrder[a.priority];
                case 'dueDate':
                    if (!a.dueDate && !b.dueDate) return 0;
                    if (!a.dueDate) return 1;
                    if (!b.dueDate) return -1;
                    return new Date(a.dueDate) - new Date(b.dueDate);
                case 'createdAt':
                    return new Date(b.createdAt) - new Date(a.createdAt);
                default:
                    return 0;
            }
        });

        // 限制数量
        if (limit && limit > 0) {
            todos = todos.slice(0, limit);
        }

        return {
            success: true,
            message: this.formatTodoList(todos, status),
            todos: todos,
            count: todos.length
        };
    }

    // 完成待办事项
    completeTodo(params) {
        const { id, title } = params;
        
        let todo = null;
        if (id) {
            todo = this.data.todos.find(t => t.id === id);
        } else if (title) {
            todo = this.data.todos.find(t => t.title.includes(title.trim()) && t.status === 'pending');
        }

        if (!todo) {
            return { success: false, error: '未找到指定的待办事项' };
        }

        if (todo.status === 'completed') {
            return { success: false, error: '该待办事项已经完成' };
        }

        todo.status = 'completed';
        todo.completedAt = new Date().toISOString();

        if (this.saveData()) {
            return {
                success: true,
                message: `🎉 待办事项已完成！\n📝 标题: ${todo.title}\n✨ 完成时间: ${new Date(todo.completedAt).toLocaleString('zh-CN')}`,
                todo: todo
            };
        } else {
            return { success: false, error: '保存数据失败' };
        }
    }

    // 删除待办事项
    deleteTodo(params) {
        const { id, title } = params;
        
        let todoIndex = -1;
        if (id) {
            todoIndex = this.data.todos.findIndex(t => t.id === id);
        } else if (title) {
            todoIndex = this.data.todos.findIndex(t => t.title.includes(title.trim()));
        }

        if (todoIndex === -1) {
            return { success: false, error: '未找到指定的待办事项' };
        }

        const todo = this.data.todos[todoIndex];
        this.data.todos.splice(todoIndex, 1);

        if (this.saveData()) {
            return {
                success: true,
                message: `🗑️ 待办事项已删除！\n📝 标题: ${todo.title}`,
                deletedTodo: todo
            };
        } else {
            return { success: false, error: '保存数据失败' };
        }
    }

    // 编辑待办事项
    editTodo(params) {
        const { id, title, description, priority, dueDate, tags } = params;
        
        if (!id) {
            return { success: false, error: '必须提供待办事项ID' };
        }

        const todo = this.data.todos.find(t => t.id === id);
        if (!todo) {
            return { success: false, error: '未找到指定的待办事项' };
        }

        // 更新字段
        if (title !== undefined) todo.title = title.trim();
        if (description !== undefined) todo.description = description.trim();
        if (priority !== undefined) {
            const validPriorities = ['high', 'medium', 'low'];
            if (validPriorities.includes(priority)) {
                todo.priority = priority;
            }
        }
        if (dueDate !== undefined) {
            if (dueDate === '' || dueDate === null) {
                todo.dueDate = null;
            } else {
                const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
                if (dateRegex.test(dueDate)) {
                    const date = new Date(dueDate);
                    if (!isNaN(date.getTime())) {
                        todo.dueDate = dueDate;
                    }
                }
            }
        }
        if (tags !== undefined) {
            todo.tags = tags ? tags.split(',').map(tag => tag.trim()).filter(tag => tag) : [];
        }

        if (this.saveData()) {
            return {
                success: true,
                message: `✏️ 待办事项已更新！\n📝 标题: ${todo.title}\n🔸 优先级: ${this.getPriorityEmoji(todo.priority)} ${this.getPriorityText(todo.priority)}\n📅 截止日期: ${todo.dueDate || '未设置'}\n🏷️ 标签: ${todo.tags.length > 0 ? todo.tags.join(', ') : '无'}`,
                todo: todo
            };
        } else {
            return { success: false, error: '保存数据失败' };
        }
    }

    // 搜索待办事项
    searchTodos(params) {
        const { keyword, status = 'all' } = params;
        
        if (!keyword || keyword.trim() === '') {
            return { success: false, error: '搜索关键词不能为空' };
        }

        const searchTerm = keyword.trim().toLowerCase();
        let todos = this.data.todos.filter(todo => {
            const titleMatch = todo.title.toLowerCase().includes(searchTerm);
            const descMatch = todo.description.toLowerCase().includes(searchTerm);
            const tagMatch = todo.tags.some(tag => tag.toLowerCase().includes(searchTerm));
            return titleMatch || descMatch || tagMatch;
        });

        // 状态筛选
        if (status !== 'all') {
            todos = todos.filter(todo => todo.status === status);
        }

        return {
            success: true,
            message: `🔍 搜索结果 (关键词: "${keyword}"):\n${this.formatTodoList(todos, status)}`,
            todos: todos,
            count: todos.length,
            keyword: keyword
        };
    }

    // 获取统计信息
    getStats() {
        const total = this.data.todos.length;
        const pending = this.data.todos.filter(t => t.status === 'pending').length;
        const completed = this.data.todos.filter(t => t.status === 'completed').length;
        
        const highPriority = this.data.todos.filter(t => t.priority === 'high' && t.status === 'pending').length;
        const mediumPriority = this.data.todos.filter(t => t.priority === 'medium' && t.status === 'pending').length;
        const lowPriority = this.data.todos.filter(t => t.priority === 'low' && t.status === 'pending').length;

        // 即将到期的任务
        const now = new Date();
        const reminderDate = new Date(now.getTime() + this.defaultReminderDays * 24 * 60 * 60 * 1000);
        const dueSoon = this.data.todos.filter(t => 
            t.status === 'pending' && 
            t.dueDate && 
            new Date(t.dueDate) <= reminderDate
        ).length;

        // 完成率
        const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;

        // 获取所有标签统计
        const tagStats = {};
        this.data.todos.forEach(todo => {
            todo.tags.forEach(tag => {
                tagStats[tag] = (tagStats[tag] || 0) + 1;
            });
        });

        const topTags = Object.entries(tagStats)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 5)
            .map(([tag, count]) => `${tag} (${count})`)
            .join(', ');

        const statsMessage = `📊 待办事项统计信息\n\n` +
            `📈 总体统计:\n` +
            `  • 总计: ${total} 个\n` +
            `  • 待完成: ${pending} 个\n` +
            `  • 已完成: ${completed} 个\n` +
            `  • 完成率: ${completionRate}%\n\n` +
            `🔸 优先级分布 (待完成):\n` +
            `  • 🔴 高优先级: ${highPriority} 个\n` +
            `  • 🟡 中优先级: ${mediumPriority} 个\n` +
            `  • 🟢 低优先级: ${lowPriority} 个\n\n` +
            `⏰ 即将到期: ${dueSoon} 个 (${this.defaultReminderDays}天内)\n\n` +
            `🏷️ 热门标签: ${topTags || '无'}`;

        return {
            success: true,
            message: statsMessage,
            stats: {
                total,
                pending,
                completed,
                completionRate,
                priority: { high: highPriority, medium: mediumPriority, low: lowPriority },
                dueSoon,
                topTags: tagStats
            }
        };
    }

    // 格式化待办事项列表
    formatTodoList(todos, status) {
        if (todos.length === 0) {
            return status === 'completed' ? '暂无已完成的待办事项' : '暂无待办事项';
        }

        const pendingCount = todos.filter(t => t.status === 'pending').length;
        const completedCount = todos.filter(t => t.status === 'completed').length;
        
        let header = `📋 待办事项列表`;
        if (status === 'all') {
            header += ` (${todos.length}个，${pendingCount}个待完成，${completedCount}个已完成)`;
        } else if (status === 'pending') {
            header += ` (${todos.length}个待完成)`;
        } else {
            header += ` (${todos.length}个已完成)`;
        }

        const formattedTodos = todos.map(todo => {
            const statusIcon = todo.status === 'completed' ? '✅' : this.getPriorityEmoji(todo.priority);
            const priorityText = todo.status === 'completed' ? '[已完成]' : `[${this.getPriorityText(todo.priority)}]`;
            
            let todoText = `${statusIcon} ${priorityText} ${todo.title}`;
            
            if (todo.description) {
                todoText += `\n   📄 ${todo.description}`;
            }
            
            if (todo.dueDate) {
                const dueDate = new Date(todo.dueDate);
                const now = new Date();
                const diffDays = Math.ceil((dueDate - now) / (1000 * 60 * 60 * 24));
                
                let dueDateText = `📅 截止：${todo.dueDate}`;
                if (todo.status === 'pending') {
                    if (diffDays < 0) {
                        dueDateText += ` ⚠️ 已逾期${Math.abs(diffDays)}天`;
                    } else if (diffDays === 0) {
                        dueDateText += ` ⚠️ 今天到期`;
                    } else if (diffDays <= this.defaultReminderDays) {
                        dueDateText += ` ⏰ 还有${diffDays}天`;
                    } else {
                        dueDateText += ` (还有${diffDays}天)`;
                    }
                }
                todoText += `\n   ${dueDateText}`;
            }
            
            if (todo.tags.length > 0) {
                todoText += `\n   🏷️ 标签：${todo.tags.join(', ')}`;
            }
            
            if (todo.status === 'completed' && todo.completedAt) {
                todoText += `\n   ✨ 完成于：${new Date(todo.completedAt).toLocaleString('zh-CN')}`;
            }
            
            todoText += `\n   🆔 ID：${todo.id}`;
            
            return todoText;
        });

        return header + '\n\n' + formattedTodos.join('\n\n');
    }

    // 获取优先级表情符号
    getPriorityEmoji(priority) {
        switch (priority) {
            case 'high': return '🔴';
            case 'medium': return '🟡';
            case 'low': return '🟢';
            default: return '🟡';
        }
    }

    // 获取优先级文本
    getPriorityText(priority) {
        switch (priority) {
            case 'high': return '高优先级';
            case 'medium': return '中优先级';
            case 'low': return '低优先级';
            default: return '中优先级';
        }
    }

    // 处理批量请求
    processBatchRequest(request) {
        const results = [];
        const commands = [];
        
        // 解析批量请求
        let commandIndex = 1;
        while (request[`command${commandIndex}`]) {
            const command = request[`command${commandIndex}`];
            const params = {};
            
            // 提取该命令的所有参数
            Object.keys(request).forEach(key => {
                if (key.endsWith(commandIndex.toString()) && key !== `command${commandIndex}`) {
                    const paramName = key.replace(commandIndex.toString(), '');
                    params[paramName] = request[key];
                }
            });
            
            commands.push({ command, params });
            commandIndex++;
        }
        
        // 执行每个命令
        commands.forEach((cmd, index) => {
            try {
                const result = this.processCommand(cmd.command, cmd.params);
                results.push({
                    commandIndex: index + 1,
                    command: cmd.command,
                    result: result
                });
            } catch (error) {
                results.push({
                    commandIndex: index + 1,
                    command: cmd.command,
                    result: { success: false, error: error.message }
                });
            }
        });
        
        // 格式化批量结果
        const successCount = results.filter(r => r.result.success).length;
        const totalCount = results.length;
        
        let batchMessage = `🔄 批量操作完成 (${successCount}/${totalCount} 成功)\n\n`;
        
        results.forEach(result => {
            batchMessage += `${result.commandIndex}. ${result.command}:\n`;
            if (result.result.success) {
                batchMessage += `   ✅ ${result.result.message}\n`;
            } else {
                batchMessage += `   ❌ ${result.result.error}\n`;
            }
            batchMessage += '\n';
        });
        
        return {
            success: successCount > 0,
            message: batchMessage,
            results: results,
            summary: { success: successCount, total: totalCount }
        };
    }

    // 处理单个命令
    processCommand(command, params) {
        switch (command) {
            case 'AddTodo':
                return this.addTodo(params);
            case 'ListTodos':
                return this.listTodos(params);
            case 'CompleteTodo':
                return this.completeTodo(params);
            case 'DeleteTodo':
                return this.deleteTodo(params);
            case 'EditTodo':
                return this.editTodo(params);
            case 'SearchTodos':
                return this.searchTodos(params);
            case 'GetStats':
                return this.getStats();
            default:
                return { success: false, error: `未知命令: ${command}` };
        }
    }
}

// 主函数
function main() {
    try {
        // 读取标准输入
        const input = require('fs').readFileSync(0, 'utf-8').trim();
        
        if (!input) {
            console.log(JSON.stringify({ status: "error", error: "没有接收到输入数据" }));
            process.exit(1);
        }

        // 解析输入
        let request;
        try {
            request = JSON.parse(input);
        } catch (parseError) {
            console.log(JSON.stringify({ status: "error", error: "输入数据格式错误" }));
            process.exit(1);
        }

        // 创建TodoManager实例
        const todoManager = new TodoManager();
        
        let result;
        
        // 检查是否为批量请求
        if (request.command1) {
            result = todoManager.processBatchRequest(request);
        } else {
            // 单个命令处理
            const command = request.command;
            if (!command) {
                result = { success: false, error: "缺少command参数" };
            } else {
                result = todoManager.processCommand(command, request);
            }
        }

        // 输出结果
        const output = {
            status: result.success ? "success" : "error",
            result: result.success ? result.message : result.error
        };

        console.log(JSON.stringify(output));
        process.exit(0);

    } catch (error) {
        console.log(JSON.stringify({ 
            status: "error", 
            error: `插件执行错误: ${error.message}` 
        }));
        process.exit(1);
    }
}

// 如果直接运行此文件，则执行主函数
if (require.main === module) {
    main();
}

module.exports = TodoManager;