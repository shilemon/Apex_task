#!/usr/bin/env bash
# Shared helpers for deploy.sh / rollback.sh (blue/green state handling).
STATE=.release/state.env

load_state() {
  ACTIVE=""; BLUE_TAG=none; GREEN_TAG=none
  # shellcheck disable=SC1090
  [ -f "$STATE" ] && . "$STATE"
  return 0
}

save_state() {
  mkdir -p .release
  printf 'ACTIVE=%s\nBLUE_TAG=%s\nGREEN_TAG=%s\n' "$1" "$BLUE_TAG" "$GREEN_TAG" > "$STATE"
}

set_upstream() {  # $1 = blue|green
  sed "s/__ACTIVE__/api-$1/" nginx/default.conf.template > nginx/default.conf.tmp
  mv nginx/default.conf.tmp nginx/default.conf
}

reload_nginx() {
  docker compose exec -T nginx nginx -t && docker compose exec -T nginx nginx -s reload
}

wait_ready_via_proxy() {
  for _ in $(seq 1 15); do
    curl -fsS http://localhost:8000/readiness >/dev/null 2>&1 && return 0
    sleep 1
  done
  return 1
}
