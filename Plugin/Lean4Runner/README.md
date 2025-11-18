# Lean4Runner 插件

通过 VCP 以“口令或结构化参数”的方式调用 Lean4 / Lake：
- 表达式评估（#eval）与类型检查（#check）
- 运行含 `def main` 的 Lean 文件
- 执行 `lake build / lake update`

## 安装与依赖

- 需要宿主环境已安装 Lean 工具链（elan）：`~/.elan/bin`（Windows: `%USERPROFILE%\.elan\bin`）
- 若二进制未在 PATH，可在插件 `config.env` 中指定：
  - `LEAN_BIN=C:\\Users\\<you>\\.elan\\bin\\lean.exe`
  - `LAKE_BIN=C:\\Users\\<you>\\.elan\\bin\\lake.exe`

## 配置项（plugin-manifest.json › configSchema）

- `LEAN_BIN`/`LAKE_BIN`：可选，显式指向 lean/lake 可执行文件
- `DEFAULT_IMPORTS`：Eval/Typecheck 默认 import 列表，逗号分隔（默认 `Mathlib`）
- `WORKDIR`：可选全局工作目录，未提供时可每次传 `workspaceDir`

## 调用方式（结构化）

1) EvalExpr（#eval 表达式）
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」Lean4Runner「末」,
command:「始」EvalExpr「末」,
expr:「始」(List.range 10).foldl (·+·) 0「末」,
imports:「始」Mathlib「末」,
workspaceDir:「始」D:/MATH Studio/math_studio「末」
<<<[END_TOOL_REQUEST]>>>
```

2) Typecheck（#check 表达式）
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」Lean4Runner「末」,
command:「始」Typecheck「末」,
expr:「始」Nat.succ「末」,
imports:「始」Mathlib「末」
<<<[END_TOOL_REQUEST]>>>
```

3) RunFile（运行含 main 的文件）
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」Lean4Runner「末」,
command:「始」RunFile「末」,
file:「始」Playground.lean「末」,
workspaceDir:「始」D:/MATH Studio/math_studio「末」
<<<[END_TOOL_REQUEST]>>>
```

4) LakeBuild / LakeUpdate
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」Lean4Runner「末」,
command:「始」LakeBuild「末」,
workspaceDir:「始」D:/MATH Studio/math_studio「末」,
targets:「始」math_studio「末」
<<<[END_TOOL_REQUEST]>>>
```

## 调用方式（口令 token）

单字段 `token`，插件内部解析路由：
```
<<<[TOOL_REQUEST]>>>
tool_name:「始」Lean4Runner「末」,
command:「始」Token「末」,
token:「始」eval: (Nat.succ 1); imports=Mathlib; dir=D:/MATH Studio/math_studio「末」
<<<[END_TOOL_REQUEST]>>>
```

支持：
- `eval:` / `check:` / `run:` / `lake: build|update`，参数使用 `k=v;` 形式

## 返回格式

所有命令返回统一 JSON：
```
{ "status": "success"|"error", "result": "纯文本结果或错误信息" }
```

## 备注与最佳实践

- 对包含 `lakefile.lean`/`lakefile.toml` 的目录，Eval/Typecheck 优先使用 `lake env lean` 保持依赖一致。
- 如需 mathlib，请确保 `lakefile.lean` 中包含 `require mathlib ...` 并已 `lake update`。
- Windows 路径可用 `D:/...` 或 `C:\\...`，在 token 中推荐前者（避免转义）。

