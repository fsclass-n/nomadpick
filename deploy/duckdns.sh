#!/usr/bin/env bash
# DuckDNS 도메인(nomadpick.duckdns.org)을 현재 EC2 공인 IP 로 갱신
set -euo pipefail
cd "$(dirname "$0")/.."
DUCKDNS_SUBDOMAIN=$(grep -E '^DUCKDNS_SUBDOMAIN=' .env | cut -d= -f2-)
DUCKDNS_TOKEN=$(grep -E '^DUCKDNS_TOKEN=' .env | cut -d= -f2-)
if [ -z "$DUCKDNS_SUBDOMAIN" ] || [ -z "$DUCKDNS_TOKEN" ]; then
  echo "DUCKDNS_SUBDOMAIN / DUCKDNS_TOKEN 미설정" >&2
  exit 1
fi
curl -fsS "https://www.duckdns.org/update?domains=${DUCKDNS_SUBDOMAIN}&token=${DUCKDNS_TOKEN}&ip="
echo
