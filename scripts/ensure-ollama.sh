#!/usr/bin/env bash
set -euo pipefail
if curl -sf --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "ollama already on :11434"
  exec tail -f /dev/null
fi
exec ollama serve
