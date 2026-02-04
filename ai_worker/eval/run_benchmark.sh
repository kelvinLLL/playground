#!/bin/bash

# Configuration
# Point this to your local API if running (e.g., http://127.0.0.1:8045/v1)
# Or use OpenAI's default https://api.openai.com/v1
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://127.0.0.1:8045/v1}"
export OPENAI_MODEL="${OPENAI_MODEL:-gemini-3-flash}"

# Ensure API Key is set (load from ../.env if needed)
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Loading API Key from ../.env..."
    export OPENAI_API_KEY=$(grep "^OPENAI_API_KEY=" ../.env | cut -d '=' -f2 | tr -d '\n' | tr -d '\r' | tr -d '"' | tr -d "'")
fi

echo "Using API URL: $OPENAI_BASE_URL"
echo "Using Model: $OPENAI_MODEL"

# 1. Start MemU Server
echo "Starting MemU Server..."
mkdir -p memu/server/memory
nohup uv run memu-server start > memu_server.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to start
sleep 5

# 2. Run Benchmark
echo "Running MemU Benchmark..."
uv run python -m ai_worker.eval.runner \
    --provider memu \
    --datasets ai_worker/eval/datasets/locomo/retrieval.jsonl \
    --output ai_worker/eval/reports/memu_results.md

EXIT_CODE=$?

# 3. Cleanup
echo "Stopping MemU Server..."
kill $SERVER_PID

if [ $EXIT_CODE -eq 0 ]; then
    echo "Benchmark Success! Results in ai_worker/eval/reports/memu_results.md"
else
    echo "Benchmark Failed. Check memu_server.log for details."
fi
