#!/bin/bash
# PreToolUse hook: blocks any access to .env files
# via Read/Edit/Write (file_path) or Bash (command).
command -v jq >/dev/null 2>&1 || { echo "Blocked: jq required for env-guard" >&2; exit 2; }

input=$(cat)

file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')
command=$(echo "$input" | jq -r '.tool_input.command // empty')

# Check file_path (Read/Edit/Write)
if echo "$file_path" | grep -qE '(^|/)\.env($|\.)'; then
  echo "Blocked: accessing .env files is not allowed." >&2
  exit 2
fi

# Check Bash command for any reference to .env
if echo "$command" | grep -qE '(^|\s|\/)\.env($|\s|\.)'; then
  echo "Blocked: accessing .env via shell command is not allowed." >&2
  exit 2
fi

exit 0