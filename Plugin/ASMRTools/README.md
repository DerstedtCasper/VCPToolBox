# ASMRTools - ASMR.one 下载工具

专为VCP系统设计的ASMR.one音声作品下载插件，支持搜索、获取详细信息和选择性下载功能。

## ✨ 功能特性

- 🔍 **智能搜索**: 支持关键词搜索，可使用标签、社团、年龄分级等过滤器
- 📋 **详细信息**: 获取作品完整信息，包括文件结构、大小统计和标签信息
- ⬇️ **选择性下载**: 支持下载整个作品或指定文件夹/文件，保持原始目录结构
- 📊 **实时进度**: 基于文件大小的精确进度计算，实时ETA预估
- 🎯 **推荐发现**: 获取个人推荐和热门作品列表

## 🚀 快速开始

### 系统要求
- Python 3.8+
- 有效的ASMR.one账户

### 安装步骤

1. **安装Python依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置账户信息**
   
   复制配置模板：
   ```bash
   cp config.env.example config.env
   ```
   
   编辑 `config.env` 文件：
   ```env
   # ASMR.one 账户配置 (必需)
   ASMR_USERNAME=your_username
   ASMR_PASSWORD=your_password
   
   # 下载配置
   ASMR_DOWNLOAD_PATH=./downloads
   
   # 进度更新配置
   ASMR_PROGRESS_UPDATE_INTERVAL=5
   ```

3. **运行安装脚本**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

## 📖 使用指南

### 搜索作品
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」ASMRTools「末」,
command:「始」SearchWorks「末」,
keyword:「始」催眠「末」,
tags:「始」治愈,ASMR「末」,
limit:「始」10「末」
<<<[END_TOOL_REQUEST]>>>
```

### 获取作品详细信息
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」ASMRTools「末」,
command:「始」GetWorkInfo「末」,
work_id:「始」RJ01405234「末」
<<<[END_TOOL_REQUEST]>>>
```

### 下载整个作品
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」ASMRTools「末」,
command:「始」DownloadWorkAsync「末」,
work_id:「始」RJ01405234「末」
<<<[END_TOOL_REQUEST]>>>
```

### 选择性下载特定文件夹
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」ASMRTools「末」,
command:「始」DownloadWorkAsync「末」,
work_id:「始」RJ01413394「末」,
target_path:「始」01：mp3「末」
<<<[END_TOOL_REQUEST]>>>
```

### 下载嵌套文件夹
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」ASMRTools「末」,
command:「始」DownloadWorkAsync「末」,
work_id:「始」RJ01413394「末」,
target_path:「始」05：特典/03：闹钟音频「末」
<<<[END_TOOL_REQUEST]>>>
```

## 🎛️ 命令参数

### SearchWorks
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `keyword` | 字符串 | ✅ | 搜索关键词 |
| `tags` | 字符串 | ❌ | 包含的标签，多个用逗号分隔 |
| `no_tags` | 字符串 | ❌ | 排除的标签，多个用逗号分隔 |
| `circle` | 字符串 | ❌ | 指定社团名称 |
| `age` | 字符串 | ❌ | 年龄限制 (general/r15/adult) |
| `limit` | 整数 | ❌ | 结果数量限制，默认20 |

### GetWorkInfo
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `work_id` | 字符串 | ✅ | 作品ID (RJ/VJ/BJ格式) |

### DownloadWorkAsync
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `work_id` | 字符串 | ✅ | 作品ID (RJ/VJ/BJ格式) |
| `target_path` | 字符串 | ❌ | 指定下载路径，不指定则下载全部 |

**target_path 示例**：
- `"01：mp3"` - 只下载mp3文件夹
- `"05：特典/03：闹钟音频"` - 下载嵌套文件夹
- `"readme.txt"` - 只下载特定文件

## 📁 项目结构

```
ASMRTools/
├── plugin-manifest.json           # 插件清单
├── plugin_main.py                 # 插件入口
├── config.env.example             # 配置模板
├── requirements.txt               # Python依赖
├── README.md                      # 使用文档
├── SELECTIVE_DOWNLOAD_SUMMARY.md  # 选择性下载功能说明
└── asmr_core/                     # 核心模块
    ├── __init__.py
    ├── config.py                  # 配置管理
    ├── asmr_api.py               # ASMR.one API客户端
    ├── request_handler.py         # 同步请求处理
    ├── async_handler_fixed.py     # 异步下载处理
    ├── sync_downloader_simple.py  # 文件下载器
    └── progress_manager.py        # 进度管理
```

## 🔧 高级功能

### 选择性下载
ASMRTools支持精确控制下载内容：

- **全部下载**: 不指定`target_path`参数
- **文件夹下载**: 指定文件夹路径，如`"音声"`
- **嵌套文件夹**: 支持多级路径，如`"特典/壁纸"`
- **单文件下载**: 指定具体文件名

### 实时进度追踪
- 基于文件大小的精确进度计算
- 智能ETA预估算法
- 实时下载速度显示
- 已完成文件列表追踪

### 文件结构分析
GetWorkInfo命令提供详细的文件结构信息：
- 树状目录结构显示
- 文件大小统计和排序
- 总文件数量和总大小
- 智能的大小格式化显示

## ⚠️ 注意事项

1. **账户安全**: 请妥善保管您的ASMR.one账户信息
2. **网络环境**: 部分地区可能需要配置代理访问
3. **版权合规**: 请遵守相关版权法律，仅下载您有权访问的内容
4. **存储空间**: 确保有足够的磁盘空间存储下载内容

## 🐛 故障排除

### 常见问题

**登录失败**
- 检查用户名和密码是否正确
- 确认网络连接正常
- 如需要，配置代理设置

**下载失败**
- 检查网络连接稳定性
- 验证下载目录权限
- 确认磁盘空间充足

**搜索无结果**
- 检查关键词拼写
- 尝试不同的搜索条件
- 确认账户登录状态

### 日志查看
插件运行时的详细信息会输出到VCP日志系统，可通过VCP界面查看执行状态和错误信息。
