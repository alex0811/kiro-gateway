#!/usr/bin/env sh

set -eu

resolve_script_path() {
  target="$1"

  while [ -h "$target" ]; do
    target_dir="$(CDPATH= cd -- "$(dirname -- "$target")" && pwd)"
    link_target="$(readlink "$target")"
    case "$link_target" in
      /*) target="$link_target" ;;
      *) target="${target_dir}/${link_target}" ;;
    esac
  done

  target_dir="$(CDPATH= cd -- "$(dirname -- "$target")" && pwd)"
  printf '%s/%s\n' "$target_dir" "$(basename -- "$target")"
}

print_error() {
  printf '%s\n' "$1" >&2
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    print_error "Missing required command: $1"
    exit 1
  fi
}

kiro_gateway_init_env() {
  SCRIPT_PATH="$(resolve_script_path "$1")"
  BIN_DIR="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")" && pwd)"
  REPO_ROOT="$(CDPATH= cd -- "${BIN_DIR}/.." && pwd)"

  export KIRO_GATEWAY_REPO_ROOT="${REPO_ROOT}"
  export KIRO_GATEWAY_HOST="${KIRO_GATEWAY_HOST:-127.0.0.1}"
  export KIRO_GATEWAY_PORT="${KIRO_GATEWAY_PORT:-8000}"
  export KIRO_GATEWAY_PROXY_API_KEY="${KIRO_GATEWAY_PROXY_API_KEY:-local-test-key}"
  export KIRO_GATEWAY_CREDS_FILE="${KIRO_GATEWAY_CREDS_FILE:-$HOME/.aws/sso/cache/kiro-auth-token.json}"
  export KIRO_GATEWAY_CLI_DB_FILE="${KIRO_GATEWAY_CLI_DB_FILE:-}"
  export KIRO_GATEWAY_REFRESH_TOKEN="${KIRO_GATEWAY_REFRESH_TOKEN:-}"
  export KIRO_GATEWAY_PID_FILE="${KIRO_GATEWAY_PID_FILE:-${TMPDIR:-/tmp}/kiro-gateway-${KIRO_GATEWAY_PORT}.pid}"
  export KIRO_GATEWAY_LOG_FILE="${KIRO_GATEWAY_LOG_FILE:-${TMPDIR:-/tmp}/kiro-gateway-${KIRO_GATEWAY_PORT}.log}"

  if [ -z "${KIRO_GATEWAY_CLI_DB_FILE}" ]; then
    if [ -f "$HOME/.local/share/kiro-cli/data.sqlite3" ]; then
      KIRO_GATEWAY_CLI_DB_FILE="$HOME/.local/share/kiro-cli/data.sqlite3"
      export KIRO_GATEWAY_CLI_DB_FILE
    elif [ -f "$HOME/.local/share/amazon-q/data.sqlite3" ]; then
      KIRO_GATEWAY_CLI_DB_FILE="$HOME/.local/share/amazon-q/data.sqlite3"
      export KIRO_GATEWAY_CLI_DB_FILE
    fi
  fi

  export ANTHROPIC_BASE_URL="http://${KIRO_GATEWAY_HOST}:${KIRO_GATEWAY_PORT}"
  export ANTHROPIC_AUTH_TOKEN="${KIRO_GATEWAY_PROXY_API_KEY}"
  export ANTHROPIC_DEFAULT_SONNET_MODEL="${ANTHROPIC_DEFAULT_SONNET_MODEL:-claude-sonnet-4.6}"
  export ANTHROPIC_DEFAULT_HAIKU_MODEL="${ANTHROPIC_DEFAULT_HAIKU_MODEL:-claude-haiku-4.5}"
  export ANTHROPIC_DEFAULT_OPUS_MODEL="${ANTHROPIC_DEFAULT_OPUS_MODEL:-claude-opus-4.6}"
}

gateway_health_url() {
  printf '%s/health\n' "${ANTHROPIC_BASE_URL}"
}

gateway_is_healthy() {
  curl -fsS "$(gateway_health_url)" >/dev/null 2>&1
}

wait_for_gateway() {
  attempts="${1:-60}"

  while [ "$attempts" -gt 0 ]; do
    if gateway_is_healthy; then
      return 0
    fi

    if [ -f "${KIRO_GATEWAY_PID_FILE}" ]; then
      gateway_pid="$(cat "${KIRO_GATEWAY_PID_FILE}" 2>/dev/null || true)"
      if [ -n "${gateway_pid}" ] && ! kill -0 "${gateway_pid}" 2>/dev/null; then
        return 1
      fi
    fi

    attempts=$((attempts - 1))
    sleep 1
  done

  return 1
}

find_running_gateway_pid() {
  if [ -f "${KIRO_GATEWAY_PID_FILE}" ]; then
    pid_from_file="$(cat "${KIRO_GATEWAY_PID_FILE}" 2>/dev/null || true)"
    if [ -n "${pid_from_file}" ] && kill -0 "${pid_from_file}" 2>/dev/null; then
      printf '%s\n' "${pid_from_file}"
      return 0
    fi
  fi

  if command -v lsof >/dev/null 2>&1; then
    pid_from_port="$(lsof -tiTCP:${KIRO_GATEWAY_PORT} -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"
    if [ -n "${pid_from_port}" ]; then
      printf '%s\n' "${pid_from_port}"
      return 0
    fi
  fi

  return 1
}

validate_gateway_prereqs() {
  if [ ! -x "${KIRO_GATEWAY_REPO_ROOT}/.venv/bin/python" ]; then
    print_error "Missing virtualenv Python at ${KIRO_GATEWAY_REPO_ROOT}/.venv/bin/python"
    exit 1
  fi

  if [ -f "${KIRO_GATEWAY_CREDS_FILE}" ]; then
    return 0
  fi

  if [ -n "${KIRO_GATEWAY_CLI_DB_FILE}" ] && [ -f "${KIRO_GATEWAY_CLI_DB_FILE}" ]; then
    return 0
  fi

  if [ -n "${KIRO_GATEWAY_REFRESH_TOKEN}" ]; then
    return 0
  fi

  print_error "No usable Kiro credentials found."
  print_error "Set one of: KIRO_GATEWAY_CREDS_FILE, KIRO_GATEWAY_CLI_DB_FILE, KIRO_GATEWAY_REFRESH_TOKEN"
  exit 1
}

start_gateway_process() {
  validate_gateway_prereqs

  if [ -f "${KIRO_GATEWAY_CREDS_FILE}" ]; then
    (
      cd "${KIRO_GATEWAY_REPO_ROOT}" || exit 1
      env \
        PROXY_API_KEY="${KIRO_GATEWAY_PROXY_API_KEY}" \
        KIRO_CREDS_FILE="${KIRO_GATEWAY_CREDS_FILE}" \
        "${KIRO_GATEWAY_REPO_ROOT}/.venv/bin/python" main.py \
          --host "${KIRO_GATEWAY_HOST}" \
          --port "${KIRO_GATEWAY_PORT}"
    ) >"${KIRO_GATEWAY_LOG_FILE}" 2>&1 &
  elif [ -n "${KIRO_GATEWAY_CLI_DB_FILE}" ] && [ -f "${KIRO_GATEWAY_CLI_DB_FILE}" ]; then
    (
      cd "${KIRO_GATEWAY_REPO_ROOT}" || exit 1
      env \
        PROXY_API_KEY="${KIRO_GATEWAY_PROXY_API_KEY}" \
        KIRO_CLI_DB_FILE="${KIRO_GATEWAY_CLI_DB_FILE}" \
        "${KIRO_GATEWAY_REPO_ROOT}/.venv/bin/python" main.py \
          --host "${KIRO_GATEWAY_HOST}" \
          --port "${KIRO_GATEWAY_PORT}"
    ) >"${KIRO_GATEWAY_LOG_FILE}" 2>&1 &
  else
    (
      cd "${KIRO_GATEWAY_REPO_ROOT}" || exit 1
      env \
        PROXY_API_KEY="${KIRO_GATEWAY_PROXY_API_KEY}" \
        REFRESH_TOKEN="${KIRO_GATEWAY_REFRESH_TOKEN}" \
        "${KIRO_GATEWAY_REPO_ROOT}/.venv/bin/python" main.py \
          --host "${KIRO_GATEWAY_HOST}" \
          --port "${KIRO_GATEWAY_PORT}"
    ) >"${KIRO_GATEWAY_LOG_FILE}" 2>&1 &
  fi

  gateway_pid="$!"
  printf '%s\n' "${gateway_pid}" > "${KIRO_GATEWAY_PID_FILE}"
  printf '%s\n' "${gateway_pid}"
}
