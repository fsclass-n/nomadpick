#!/usr/bin/env bash
# AWS EC2 (Ubuntu 22.04/24.04) 최초 1회 설정 - Docker 설치, 저장소 클론, DuckDNS 갱신 cron
#   사용: bash ec2-setup.sh
# 사전 준비: 보안 그룹 인바운드 22(SSH), 80, 443 허용 / 탄력적 IP 연결 권장
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/fsclass-n/nomadpick.git}"
APP_DIR="${APP_DIR:-$HOME/nomadpick}"

sudo apt-get update -y
sudo apt-get install -y ca-certificates curl git
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi

if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
  echo ">> $APP_DIR/.env 를 편집하여 DATABASE_URL(TiDB), JWT_SECRET, RPA_API_KEY, DATA_GO_KR_KEY, DUCKDNS_TOKEN 등을 입력하세요."
fi

# DuckDNS IP 갱신 (5분마다) - .env 의 DUCKDNS_SUBDOMAIN / DUCKDNS_TOKEN 사용
CRON_LINE="*/5 * * * * cd $APP_DIR && bash deploy/duckdns.sh >/dev/null 2>&1"
( crontab -l 2>/dev/null | grep -v 'deploy/duckdns.sh' ; echo "$CRON_LINE" ) | crontab -

echo ">> 완료. 다시 로그인(docker 그룹 적용) 후 실행: cd $APP_DIR && docker compose up -d --build"
