#!/usr/bin/env bash
# 로컬 Docker 스모크 — 배포 런북 02 §4-2 를 1명령으로. 이미지 빌드 → 컨테이너 기동 → /health 대기 → 3점 스모크 → 접속 URL 출력.
# Railway 와 같은 형태로 띄운다: DATA_DIR=/data 를 named volume 에 마운트(SQLite 영구성), PORT 는 컨테이너 안 8000 고정.
#
#   scripts/docker_up.sh                # http://localhost:8000
#   PORT=8001 scripts/docker_up.sh      # 호스트 포트 변경(8000 이 make serve 로 사용 중일 때)
#   NO_CACHE=1 scripts/docker_up.sh     # 이미지 재빌드(캐시 무시)
#   정리는 scripts/docker_down.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${IMAGE:-millie-rec:local}"
NAME="${NAME:-millie-rec-local}"
VOLUME="${VOLUME:-millie-rec-data}"
PORT="${PORT:-8000}"
WAIT_S="${WAIT_S:-60}"

command -v docker >/dev/null || { echo "docker 가 없다 — Docker Desktop 을 켜거나 설치한다"; exit 1; }
docker info >/dev/null 2>&1 || { echo "docker 데몬에 연결할 수 없다 — Docker Desktop 실행 여부 확인"; exit 1; }

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "포트 $PORT 가 이미 사용 중이다(make serve 등). 다른 포트로: PORT=8001 $0"
  exit 1
fi

# 이전 컨테이너가 남아 있으면 먼저 치운다(볼륨은 유지)
if docker ps -a --format '{{.Names}}' | grep -qx "$NAME"; then
  echo "기존 컨테이너 $NAME 제거"
  docker rm -f "$NAME" >/dev/null
fi

echo "== build $IMAGE (context: $ROOT)"
BUILD_ARGS=()
[ "${NO_CACHE:-0}" = "1" ] && BUILD_ARGS+=(--no-cache)
docker build "${BUILD_ARGS[@]+"${BUILD_ARGS[@]}"}" -t "$IMAGE" "$ROOT"

docker volume create "$VOLUME" >/dev/null
echo "== run $NAME  (host :$PORT → container :8000, volume $VOLUME → /data)"
docker run -d --name "$NAME" \
  -p "${PORT}:8000" \
  -e PORT=8000 -e DATA_DIR=/data \
  -v "${VOLUME}:/data" \
  "$IMAGE" >/dev/null

echo -n "== /health 대기"
for _ in $(seq 1 "$WAIT_S"); do
  if curl -fsS "localhost:${PORT}/health" >/dev/null 2>&1; then echo " ok"; break; fi
  if [ "$(docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null)" != "true" ]; then
    echo; echo "컨테이너가 죽었다 — 로그:"; docker logs "$NAME" 2>&1 | tail -40; exit 1
  fi
  echo -n "."; sleep 1
done
curl -fsS "localhost:${PORT}/health" >/dev/null 2>&1 || { echo; echo "${WAIT_S}s 안에 /health 응답 없음 — 로그:"; docker logs "$NAME" 2>&1 | tail -40; exit 1; }

# 3점 스모크 = Makefile smoke 와 같은 항목(.claude/rules/local-run.md)
ok=1
curl -fsS "localhost:${PORT}/health" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("smoke: /health 200  status=%s db_ok=%s model_version=%s" % (d.get("status"), d.get("db_ok"), d.get("model_version")))' || ok=0
curl -fsS -o /dev/null "localhost:${PORT}/" && echo "smoke: / (demo static) 200" || ok=0
curl -fsS "localhost:${PORT}/api/recommend?seeds=1,2,3&k=5" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("smoke: /api/recommend 200  fallback_level=%s rows=%d model_version=%s" % (d.get("fallback_level"), len(d.get("rows", [])), d.get("model_version")))' || ok=0
[ "$ok" = 1 ] || { echo "smoke: FAIL — 로그:"; docker logs "$NAME" 2>&1 | tail -40; exit 1; }

cat <<EOF
smoke: PASS

  데모(API 연동)  http://localhost:${PORT}/?source=api
  데모(mock)      http://localhost:${PORT}/?source=mock
  API 문서        http://localhost:${PORT}/docs
  헬스            http://localhost:${PORT}/health

  로그 보기       docker logs -f ${NAME}
  정리            scripts/docker_down.sh            (컨테이너만)
                  scripts/docker_down.sh --all      (컨테이너 + 볼륨 + 이미지)
EOF
