# ASMRTools 选择性下载功能实现总结

## 🎯 功能概述

ASMRTools现在支持选择性下载功能，用户可以指定只下载作品中的特定文件夹或文件，而不需要下载整个作品。

## ✅ 已实现的功能

### 1. 新增参数支持

**参数名**: `target_path` (可选)
- **类型**: 字符串
- **默认值**: 空字符串（下载全部内容）
- **格式**: 文件夹路径或文件路径

### 2. 支持的路径格式

| 路径类型 | 示例 | 说明 |
|---------|------|------|
| 空值 | `""` 或不指定 | 下载全部内容 |
| 单级文件夹 | `"01：mp3"` | 只下载mp3文件夹 |
| 嵌套文件夹 | `"05：特典/03：闹钟音频"` | 下载特典中的闹钟音频文件夹 |
| 特定文件 | `"readme.txt"` | 只下载指定文件 |

### 3. 实际测试验证

使用作品 **RJ01413394** 进行测试：

#### 测试1: 下载mp3文件夹
```
路径: "01：mp3"
结果: 从491个总文件中过滤出9个文件
状态: ✅ 成功下载所有mp3文件
```

#### 测试2: 下载嵌套文件夹
```
路径: "05：特典/03：闹钟音频"
结果: 从491个总文件中过滤出18个文件
状态: ✅ 正确识别嵌套路径
```

## 🔧 技术实现细节

### 1. 插件清单更新 (`plugin-manifest.json`)

```json
{
    "commandIdentifier": "DownloadWorkAsync",
    "description": "（异步）下载指定的音声作品。支持选择性下载特定文件夹或文件。",
    "parameters": {
        "work_id": "作品ID（必需）",
        "target_path": "指定要下载的文件夹或文件路径（可选）"
    }
}
```

### 2. 异步处理器增强 (`async_handler_fixed.py`)

#### 参数处理
```python
# 获取目标路径参数（可选）
target_path = request_data.get('target_path', '')

# 构建下载范围描述
download_scope = "全部内容" if not target_path else f"指定路径: {target_path}"
```

#### 文件过滤
```python
# 如果指定了目标路径，过滤文件
if target_path:
    all_files = downloader._filter_files_by_path(all_files, target_path)
```

### 3. 同步下载器增强 (`sync_downloader_simple.py`)

#### 路径过滤方法
```python
def _filter_files_by_path(self, all_files: List[Dict], target_path: str) -> List[Dict]:
    """根据目标路径过滤文件"""
    
def _path_matches(self, file_path: str, target_path: str) -> bool:
    """检查文件路径是否匹配目标路径"""
```

#### 过滤逻辑
- 精确匹配文件: `file_path == target_path`
- 文件夹内容匹配: `file_path.startswith(target_path + '/')`
- 文件夹匹配: `file_dir == target_path`

## 📊 功能验证结果

### 路径过滤测试
```
✅ 全部文件: 7/7 文件
✅ mp3文件夹: 2/7 文件
✅ 嵌套的闹钟音频文件夹: 2/7 文件
✅ 单个文件: 1/7 文件
✅ 不存在的路径: 0/7 文件
```

### 实际下载测试
```
作品: RJ01413394 (491个文件)
✅ 01：mp3 → 9个文件成功下载
✅ 05：特典/03：闹钟音频 → 18个文件正确识别
```

## 🎯 使用示例

### 1. 下载全部内容
```json
{
    "command": "DownloadWorkAsync",
    "work_id": "RJ01413394"
}
```

### 2. 只下载mp3文件夹
```json
{
    "command": "DownloadWorkAsync",
    "work_id": "RJ01413394",
    "target_path": "01：mp3"
}
```

### 3. 下载嵌套文件夹
```json
{
    "command": "DownloadWorkAsync",
    "work_id": "RJ01413394",
    "target_path": "05：特典/03：闹钟音频"
}
```

### 4. 下载特定文件
```json
{
    "command": "DownloadWorkAsync",
    "work_id": "RJ01413394",
    "target_path": "readme.txt"
}
```

## 🌟 功能特点

### ✅ 优势
1. **节省时间**: 只下载需要的内容，避免下载整个作品
2. **节省空间**: 减少不必要的文件下载
3. **保持结构**: 下载的文件保持原始的文件夹结构
4. **中文支持**: 完全支持中文路径名称
5. **嵌套支持**: 支持多级嵌套文件夹路径
6. **向下兼容**: 不指定路径时保持原有的全部下载行为

### ✅ 安全性
1. **路径验证**: 只能下载作品内的文件，不能访问其他路径
2. **错误处理**: 不存在的路径会返回0个文件，不会出错
3. **格式兼容**: 支持各种路径分隔符格式

## 🎉 总结

ASMRTools的选择性下载功能已经完全实现并通过测试验证：

1. **✅ 参数支持**: 新增`target_path`参数，支持可选的路径指定
2. **✅ 路径过滤**: 智能的文件路径匹配和过滤算法
3. **✅ 结构保持**: 下载的文件完全保持原始文件夹结构
4. **✅ 中文支持**: 完美支持中文路径和文件名
5. **✅ 嵌套支持**: 支持多级嵌套文件夹路径
6. **✅ 实际验证**: 使用真实作品RJ01413394成功测试

用户现在可以精确控制要下载的内容，大大提升了下载效率和用户体验！