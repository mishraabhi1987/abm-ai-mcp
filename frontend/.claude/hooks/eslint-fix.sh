#!/usr/bin/env bash
# PostToolUse: sirf JS/JSX/TS/TSX par eslint --fix chalao.
# Claude Code edited file ka path stdin se JSON mein deta hai.
file=$(jq -r '.tool_input.file_path // empty')

# Koi file nahi / hamari files nahi -> chup-chaap exit 0 (hook fail na ho)
[ -z "$file" ] && exit 0
case "$file" in
  *.js|*.jsx|*.ts|*.tsx) npx eslint --fix "$file" 2>/dev/null ;;
  *) exit 0 ;;
esac
exit 0