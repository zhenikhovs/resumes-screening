#!/usr/bin/env bash
cd "$(dirname "$0")/.."
exec uvicorn web_api.main:app --reload --host 127.0.0.1 --port 8000
