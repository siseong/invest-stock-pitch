#!/bin/zsh
cd -- "${0:A:h}"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3가 필요합니다.'
  read -r '?Enter를 누르면 종료합니다.'
  exit 1
fi
(sleep 1; open 'http://127.0.0.1:8765') &
python3 server.py --port 8765
