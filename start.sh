#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
START_SH="$ROOT/start.sh"

if [[ "${1:-}" == "backend" ]]; then
  export PYTHONPATH="${ROOT}/backend"
  export PORT="${PORT:-5001}"
  cd "$ROOT"
  PY=""
  if [[ -x "$ROOT/.venv/bin/python3" ]]; then
    PY="$ROOT/.venv/bin/python3"
  elif [[ -x "$ROOT/.venv/bin/python" ]]; then
    PY="$ROOT/.venv/bin/python"
  fi
  if [[ -n "$PY" ]]; then
    echo "Using .venv for backend"
    if ! "$PY" -c "import flask" 2>/dev/null; then
      echo "Flask is missing from .venv. Install dependencies:"
      echo "  \"$PY\" -m pip install -r requirements.txt"
      sleep 5
      exit 1
    fi
    echo "Backend API at http://127.0.0.1:${PORT}/"
    echo "Press Ctrl+C to stop."
    exec "$PY" -m app.main
  fi
  echo "Backend: no .venv found. Create one and install deps, or use system Python with Flask."
  echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  echo "Trying system Python..."
  if command -v python3 >/dev/null 2>&1; then
    if ! python3 -c "import flask" 2>/dev/null; then
      echo "Flask not found. Run: pip install -r requirements.txt"
      sleep 5
      exit 1
    fi
    echo "Backend API at http://127.0.0.1:${PORT}/"
    echo "Press Ctrl+C to stop."
    exec python3 -m app.main
  elif command -v python >/dev/null 2>&1; then
    PYVER="$(python -c 'import sys; print(sys.version_info[0])' 2>/dev/null || echo 0)"
    if [[ "$PYVER" -ge 3 ]]; then
      if ! python -c "import flask" 2>/dev/null; then
        echo "Flask not found. Run: python -m pip install -r requirements.txt"
        sleep 5
        exit 1
      fi
      echo "Backend API at http://127.0.0.1:${PORT}/"
      echo "Press Ctrl+C to stop."
      exec python -m app.main
    fi
  fi
  echo "Python 3 is required."
  sleep 5
  exit 1
fi

if [[ "${1:-}" == "frontend" ]]; then
  cd "$ROOT"
  export PORT="${PORT:-3001}"
  PY=""
  if [[ -x "$ROOT/.venv/bin/python3" ]]; then
    PY="$ROOT/.venv/bin/python3"
  elif [[ -x "$ROOT/.venv/bin/python" ]]; then
    PY="$ROOT/.venv/bin/python"
  fi
  if [[ -n "$PY" ]]; then
    exec "$PY" frontend/server.py
  fi
  if command -v python3 >/dev/null 2>&1; then
    exec python3 frontend/server.py
  elif command -v python >/dev/null 2>&1; then
    PYVER="$(python -c 'import sys; print(sys.version_info[0])' 2>/dev/null || echo 0)"
    if [[ "$PYVER" -ge 3 ]]; then
      exec python frontend/server.py
    fi
  fi
  echo "Python 3 is required."
  sleep 5
  exit 1
fi

cd "$ROOT"

applescript_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

run_in_new_mac_terminal() {
  local cmd="$1"
  local esc
  esc="$(applescript_escape "$cmd")"
  osascript -e "tell application \"Terminal\" to do script \"$esc\""
}

run_linux_term() {
  local cmd="$1"
  if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal -- bash -c "cd \"$(printf %q "$ROOT")\" && $cmd; exec bash" &
  elif command -v konsole >/dev/null 2>&1; then
    konsole -e bash -c "cd \"$(printf %q "$ROOT")\" && $cmd; exec bash" &
  elif command -v xfce4-terminal >/dev/null 2>&1; then
    xfce4-terminal -e "bash -c 'cd $(printf %q "$ROOT") && $cmd; exec bash'" &
  elif command -v xterm >/dev/null 2>&1; then
    xterm -e bash -c "cd \"$(printf %q "$ROOT")\" && $cmd; exec bash" &
  else
    return 1
  fi
  return 0
}

case "$(uname -s)" in
  Darwin*)
    echo "Opening two Terminal windows: Backend :5001 and Frontend :3001"
    run_in_new_mac_terminal "cd \"$ROOT\" && bash \"$START_SH\" backend"
    sleep 0.5
    run_in_new_mac_terminal "cd \"$ROOT\" && bash \"$START_SH\" frontend"
    ;;
  Linux*)
    echo "Opening two terminal windows: Backend :5001 and Frontend :3001"
    if ! run_linux_term "bash $(printf %q "$START_SH") backend"; then
      echo "No supported terminal emulator found. Run in two tabs:"
      echo "  ./start.sh backend"
      echo "  ./start.sh frontend"
      exit 1
    fi
    sleep 0.5
    if ! run_linux_term "bash $(printf %q "$START_SH") frontend"; then
      echo "Could not open second window. Run ./start.sh frontend in another terminal."
      exit 1
    fi
    ;;
  *)
    echo "Unsupported OS. Run in two terminals:"
    echo "  ./start.sh backend"
    echo "  ./start.sh frontend"
    exit 1
    ;;
esac
