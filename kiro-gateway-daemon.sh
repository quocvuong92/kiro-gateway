#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_DIR="$SCRIPT_DIR/daemon"
PID_FILE="$DAEMON_DIR/kiro-gateway.pid"
WATCHDOG_PID_FILE="$DAEMON_DIR/watchdog.pid"
LOG_FILE="$DAEMON_DIR/kiro-gateway.log"
CRASH_LOG_FILE="$DAEMON_DIR/kiro-gateway-crash.log"
RESTART_COUNT_FILE="$DAEMON_DIR/restart-count.txt"

# Python virtual environment
VENV_PYTHON="$HOME/py/common/bin/python"

# Ensure daemon directory exists
mkdir -p "$DAEMON_DIR"

# Auto-restart configuration
MAX_RESTARTS=10            # Max restarts within the time window
RESTART_WINDOW=300        # Time window in seconds (5 minutes)
INITIAL_BACKOFF=5         # Initial backoff in seconds
MAX_BACKOFF=300           # Max backoff in seconds (5 minutes)
HEALTH_CHECK_INTERVAL=10  # Check process health every 10 seconds

log_crash() {
    echo "$(date): $1" >> "$CRASH_LOG_FILE"
    echo "$1"
}

get_restart_count() {
    if [ -f "$RESTART_COUNT_FILE" ]; then
        cat "$RESTART_COUNT_FILE"
    else
        echo "0"
    fi
}

increment_restart_count() {
    local count=$(get_restart_count)
    echo $((count + 1)) > "$RESTART_COUNT_FILE"
}

reset_restart_count() {
    echo "0" > "$RESTART_COUNT_FILE"
}

calculate_backoff() {
    local restart_count=$1
    local backoff=$((INITIAL_BACKOFF * (2 ** restart_count)))
    if [ $backoff -gt $MAX_BACKOFF ]; then
        backoff=$MAX_BACKOFF
    fi
    echo $backoff
}

check_venv() {
    if [ ! -f "$VENV_PYTHON" ]; then
        echo "Error: Python virtual environment not found at $VENV_PYTHON"
        echo ""
        echo "Please ensure the virtual environment exists at ~/py/common/bin/python"
        echo "Or update the VENV_PYTHON variable in this script to point to your Python interpreter."
        exit 1
    fi

    # Check if it's actually executable
    if [ ! -x "$VENV_PYTHON" ]; then
        echo "Error: Python interpreter at $VENV_PYTHON is not executable"
        exit 1
    fi
}

check_dependencies() {
    echo "Checking dependencies..."
    cd "$SCRIPT_DIR"

    # Check if requirements.txt exists
    if [ ! -f "requirements.txt" ]; then
        echo "Error: requirements.txt not found in $SCRIPT_DIR"
        exit 1
    fi

    # Check if main.py exists
    if [ ! -f "main.py" ]; then
        echo "Error: main.py not found in $SCRIPT_DIR"
        exit 1
    fi

    # Check if .env exists
    if [ ! -f ".env" ]; then
        echo "Warning: .env file not found. The application may fail to start."
        echo "Copy .env.example to .env and configure your credentials:"
        echo "  cp .env.example .env"
        echo ""
    fi

    echo "Dependencies check passed"
}

install_dependencies() {
    echo "Installing/updating dependencies..."
    cd "$SCRIPT_DIR"

    check_venv

    if "$VENV_PYTHON" -m pip install -r requirements.txt; then
        echo "Dependencies installed successfully"
        return 0
    else
        echo "Failed to install dependencies!"
        return 1
    fi
}

start_main_process() {
    echo "$(date): Starting kiro-gateway..." >> "$LOG_FILE"
    cd "$SCRIPT_DIR"
    nohup "$VENV_PYTHON" main.py >> "$LOG_FILE" 2>&1 &
    local pid=$!
    echo $pid > "$PID_FILE"
    echo "$(date): kiro-gateway started (PID: $pid)" >> "$LOG_FILE"
    return 0
}

watchdog_monitor() {
    local restart_count=0
    local last_restart_time=0
    local backoff=0

    log_crash "Watchdog started. Monitoring kiro-gateway process..."

    while true; do
        sleep $HEALTH_CHECK_INTERVAL

        # Check if main process is still running
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ! kill -0 "$PID" 2>/dev/null; then
                # Process crashed
                log_crash "Process $PID crashed or stopped unexpectedly!"

                # Check restart window
                current_time=$(date +%s)
                time_since_last_restart=$((current_time - last_restart_time))

                if [ $time_since_last_restart -gt $RESTART_WINDOW ]; then
                    # Reset counter if outside the restart window
                    restart_count=0
                    backoff=0
                    log_crash "Reset restart counter (outside time window)"
                fi

                # Check if we've exceeded max restarts
                if [ $restart_count -ge $MAX_RESTARTS ]; then
                    log_crash "Max restart attempts ($MAX_RESTARTS) reached within $RESTART_WINDOW seconds. Stopping watchdog."
                    log_crash "Please check logs and restart manually: $0 restart"
                    exit 1
                fi

                # Calculate backoff
                if [ $restart_count -gt 0 ]; then
                    backoff=$(calculate_backoff $restart_count)
                    log_crash "Waiting $backoff seconds before restart (attempt $((restart_count + 1))/$MAX_RESTARTS)..."
                    sleep $backoff
                fi

                # Attempt restart
                log_crash "Attempting to restart kiro-gateway (attempt $((restart_count + 1))/$MAX_RESTARTS)..."
                start_main_process

                restart_count=$((restart_count + 1))
                increment_restart_count
                last_restart_time=$(date +%s)

                # Give it some time to start
                sleep 5
            fi
        else
            log_crash "PID file not found. Watchdog stopping."
            break
        fi
    done
}

start_watchdog() {
    if [ -f "$WATCHDOG_PID_FILE" ] && kill -0 "$(cat "$WATCHDOG_PID_FILE")" 2>/dev/null; then
        echo "Watchdog is already running (PID: $(cat "$WATCHDOG_PID_FILE"))"
        return 1
    fi

    watchdog_monitor &
    echo $! > "$WATCHDOG_PID_FILE"
    echo "Watchdog started (PID: $!)"
}

stop_watchdog() {
    if [ -f "$WATCHDOG_PID_FILE" ]; then
        WATCHDOG_PID=$(cat "$WATCHDOG_PID_FILE")
        if kill -0 "$WATCHDOG_PID" 2>/dev/null; then
            kill "$WATCHDOG_PID"
            rm -f "$WATCHDOG_PID_FILE"
            echo "Watchdog stopped"
        else
            rm -f "$WATCHDOG_PID_FILE"
        fi
    fi
}

start_daemon() {
    check_venv
    check_dependencies

    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "kiro-gateway is already running (PID: $(cat "$PID_FILE"))"
        return 1
    fi

    echo "Starting kiro-gateway daemon with auto-restart..."
    reset_restart_count
    start_main_process
    PID=$(cat "$PID_FILE")
    echo "kiro-gateway started (PID: $PID)"

    # Start watchdog
    start_watchdog
}

stop_daemon() {
    # Stop watchdog first to prevent auto-restart
    stop_watchdog

    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "Stopping kiro-gateway (PID: $PID)..."
            kill "$PID"

            # Wait up to 10 seconds for graceful shutdown
            for i in {1..10}; do
                if ! kill -0 "$PID" 2>/dev/null; then
                    break
                fi
                sleep 1
            done

            # Force kill if still running
            if kill -0 "$PID" 2>/dev/null; then
                echo "Force stopping kiro-gateway..."
                kill -9 "$PID" 2>/dev/null
            fi

            rm -f "$PID_FILE"
            echo "kiro-gateway stopped"
        else
            echo "Process $PID not found"
            rm -f "$PID_FILE"
        fi
    else
        echo "kiro-gateway is not running"
    fi

    # Clean up restart count
    rm -f "$RESTART_COUNT_FILE"
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "kiro-gateway is running (PID: $(cat "$PID_FILE"))"
    else
        echo "kiro-gateway is not running"
    fi

    if [ -f "$WATCHDOG_PID_FILE" ] && kill -0 "$(cat "$WATCHDOG_PID_FILE")" 2>/dev/null; then
        echo "Watchdog is running (PID: $(cat "$WATCHDOG_PID_FILE"))"
    else
        echo "Watchdog is not running"
    fi

    if [ -f "$RESTART_COUNT_FILE" ]; then
        echo "Restart count: $(cat "$RESTART_COUNT_FILE")"
    fi
}

show_logs() {
    echo "=== Main Log ==="
    if [ -f "$LOG_FILE" ]; then
        tail -20 "$LOG_FILE"
    else
        echo "No log file found"
    fi

    echo -e "\n=== Crash Log ==="
    if [ -f "$CRASH_LOG_FILE" ]; then
        tail -20 "$CRASH_LOG_FILE"
    else
        echo "No crash log file found"
    fi
}

cleanup_logs() {
    echo "Cleaning up log files..."

    local cleaned=0

    if [ -f "$LOG_FILE" ]; then
        > "$LOG_FILE"
        echo "✓ Emptied main log: $LOG_FILE"
        cleaned=$((cleaned + 1))
    fi

    if [ -f "$CRASH_LOG_FILE" ]; then
        > "$CRASH_LOG_FILE"
        echo "✓ Emptied crash log: $CRASH_LOG_FILE"
        cleaned=$((cleaned + 1))
    fi

    if [ $cleaned -eq 0 ]; then
        echo "No log files to clean up"
    else
        echo "Cleaned up $cleaned log file(s)"
    fi
}

follow_logs() {
    echo "Following logs (Ctrl+C to stop)..."
    echo "=================================="

    local pids=()

    # Start tail -f for each existing log file in the background
    if [ -f "$LOG_FILE" ]; then
        echo "--- Main Log ($LOG_FILE) ---"
        tail -f "$LOG_FILE" 2>/dev/null | sed 's/^/[MAIN] /' &
        pids+=($!)
    fi

    if [ -f "$CRASH_LOG_FILE" ]; then
        echo "--- Crash Log ($CRASH_LOG_FILE) ---"
        tail -f "$CRASH_LOG_FILE" 2>/dev/null | sed 's/^/[CRASH] /' &
        pids+=($!)
    fi

    if [ ${#pids[@]} -eq 0 ]; then
        echo "No log files found to follow"
        return 1
    fi

    echo "=================================="

    # Wait for all tail processes (they'll run until interrupted)
    trap "kill ${pids[@]} 2>/dev/null; exit 0" INT TERM
    wait
}

case "$1" in
    install)
        check_venv
        install_dependencies
        ;;
    start)
        start_daemon
        ;;
    stop)
        stop_daemon
        ;;
    restart)
        stop_daemon
        sleep 2
        start_daemon
        ;;
    status)
        status
        ;;
    logs)
        if [ "$2" = "-f" ] || [ "$2" = "--follow" ]; then
            follow_logs
        else
            show_logs
        fi
        ;;
    cleanup-logs)
        cleanup_logs
        ;;
    *)
        echo "Usage: $0 {install|start|stop|restart|status|logs|cleanup-logs}"
        echo ""
        echo "Commands:"
        echo "  install      - Install/update Python dependencies from requirements.txt"
        echo "  start        - Start kiro-gateway daemon with auto-restart watchdog"
        echo "  stop         - Stop kiro-gateway daemon and watchdog"
        echo "  restart      - Restart the daemon"
        echo "  status       - Show daemon status"
        echo "  logs [-f]    - Show recent logs (main, crash)"
        echo "                 -f, --follow: Follow logs in real-time (like tail -f)"
        echo "  cleanup-logs - Empty all log files (main, crash)"
        echo ""
        echo "Configuration:"
        echo "  Python venv: $VENV_PYTHON"
        echo ""
        echo "Auto-restart Configuration:"
        echo "  Max restarts: $MAX_RESTARTS within $RESTART_WINDOW seconds"
        echo "  Health check interval: $HEALTH_CHECK_INTERVAL seconds"
        echo "  Initial backoff: $INITIAL_BACKOFF seconds"
        echo "  Max backoff: $MAX_BACKOFF seconds"
        echo ""
        echo "Log files:"
        echo "  Main: $LOG_FILE"
        echo "  Crash: $CRASH_LOG_FILE"
        exit 1
        ;;
esac
