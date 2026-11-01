#!/usr/bin/env bash
# Локальный запуск без установки пакетов и обращения к сети.
cd "$(dirname "$0")" || exit 1
exec python3 -u server.py "$@"
