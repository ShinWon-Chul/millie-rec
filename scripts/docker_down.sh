#!/usr/bin/env bash
# scripts/docker_up.sh 가 만든 것을 정리한다. 기본은 컨테이너만(SQLite 볼륨·이미지는 유지 → 다음 up 이 빠르고 데이터가 남는다).
#
#   scripts/docker_down.sh            # 컨테이너 중지·삭제
#   scripts/docker_down.sh --volume   # + SQLite 볼륨 삭제(스냅샷·이벤트 초기화)
#   scripts/docker_down.sh --image    # + 이미지 삭제
#   scripts/docker_down.sh --all      # 전부
set -euo pipefail

IMAGE="${IMAGE:-millie-rec:local}"
NAME="${NAME:-millie-rec-local}"
VOLUME="${VOLUME:-millie-rec-data}"

rm_volume=0; rm_image=0
for a in "$@"; do
  case "$a" in
    --volume) rm_volume=1 ;;
    --image)  rm_image=1 ;;
    --all)    rm_volume=1; rm_image=1 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "모르는 옵션: $a (--volume | --image | --all)"; exit 1 ;;
  esac
done

command -v docker >/dev/null || { echo "docker 가 없다"; exit 1; }
docker info >/dev/null 2>&1 || { echo "docker 데몬에 연결할 수 없다 — Docker Desktop 실행 여부 확인"; exit 1; }

if docker ps -a --format '{{.Names}}' | grep -qx "$NAME"; then
  docker rm -f "$NAME" >/dev/null && echo "removed container  $NAME"
else
  echo "no container       $NAME"
fi

if [ "$rm_volume" = 1 ]; then
  if docker volume inspect "$VOLUME" >/dev/null 2>&1; then
    docker volume rm "$VOLUME" >/dev/null && echo "removed volume     $VOLUME (SQLite 초기화)"
  else
    echo "no volume          $VOLUME"
  fi
else
  docker volume inspect "$VOLUME" >/dev/null 2>&1 && echo "kept volume        $VOLUME (삭제: --volume)"
fi

if [ "$rm_image" = 1 ]; then
  if docker image inspect "$IMAGE" >/dev/null 2>&1; then
    docker rmi "$IMAGE" >/dev/null && echo "removed image      $IMAGE"
  else
    echo "no image           $IMAGE"
  fi
else
  docker image inspect "$IMAGE" >/dev/null 2>&1 && echo "kept image         $IMAGE (삭제: --image)"
fi
