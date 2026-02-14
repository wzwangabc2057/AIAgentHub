#!/bin/bash
# AIAgentHub start script
# Usage:
#   ./scripts/start.sh serve     - Start main server (API + Scheduler + Worker)
#   ./scripts/start.sh worker    - Start worker only (distributed)
#   ./scripts/start.sh stop      - Stop all AIAgentHub processes

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

case "${1:-serve}" in
    serve)
        echo "Starting AIAgentHub server..."
        if tmux has-session -t aiagent_server 2>/dev/null; then
            echo "Server already running in tmux session 'aiagent_server'"
            echo "Attach with: tmux attach -t aiagent_server"
        else
            tmux new-session -d -s aiagent_server "cd $PROJECT_DIR && python server.py"
            echo "Server started in tmux session 'aiagent_server'"
            echo "Attach with: tmux attach -t aiagent_server"
        fi
        ;;
    worker)
        NODE_ID="${NODE_ID:-worker_$(hostname)}"
        echo "Starting AIAgentHub worker (node: $NODE_ID)..."
        if tmux has-session -t aiagent_worker 2>/dev/null; then
            echo "Worker already running"
        else
            tmux new-session -d -s aiagent_worker "cd $PROJECT_DIR && python worker.py"
            echo "Worker started in tmux session 'aiagent_worker'"
        fi
        ;;
    stop)
        echo "Stopping AIAgentHub..."
        tmux kill-session -t aiagent_server 2>/dev/null && echo "Server stopped" || echo "No server session"
        tmux kill-session -t aiagent_worker 2>/dev/null && echo "Worker stopped" || echo "No worker session"
        ;;
    *)
        echo "Usage: $0 {serve|worker|stop}"
        exit 1
        ;;
esac
