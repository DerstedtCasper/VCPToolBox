#!/usr/bin/env bash
# start_wrapper.sh —— 仅做环境准备，不强行校验
set -eE -o pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

# UTF-8 兜底（中文安全；若 config.env 里有 LANG/LC_ALL 会覆盖）
export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-$LANG}"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
export PYTHONUTF8=1   # Python3.7+ 强制 UTF-8（中文 I/O 更稳）

# 1) venv（存在则激活）
if [[ -f "$BASE_DIR/venv/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$BASE_DIR/venv/bin/activate"
fi

# 2) 安全加载 config.env：先净化(BOM/CRLF)到临时文件，再 source
CONFIG_FILE="$BASE_DIR/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
  SANITIZED="$(mktemp)"
  awk 'NR==1{sub(/^\xef\xbb\xbf/,"")} {gsub("\r",""); print}' "$CONFIG_FILE" > "$SANITIZED"
  set +u
  set -o allexport
  # shellcheck source=/dev/null
  source "$SANITIZED" || true     # 仅导入，不因个别行问题中断
  set +o allexport
  rm -f "$SANITIZED"
fi

# 3) 交给 node（不锁端口、不做必填校验）
exec /usr/bin/env node server.js
