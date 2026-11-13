#!/usr/bin/env python3
"""Restore the private roster locally without changing public resources."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
backup = root / 'private' / 'presenters.json'
if not backup.exists():
    raise SystemExit('이 컴퓨터의 private/presenters.json 백업이 필요합니다. 공개 저장소에는 포함되지 않습니다.')
roster = json.loads(backup.read_text())
public = json.loads((root / 'resources' / 'stocks.json').read_text())
people = {s['symbol']: s for s in roster['stocks']}
public['schemaVersion'] = 1
for stock in public['stocks']:
    saved = people[stock['symbol']]
    stock.pop('selectionCount', None)
    stock['presenters'] = saved['presenters']
    stock['sources'] = saved.get('sources', [])
output = root / 'private' / 'restored-stocks.json'
output.write_text(json.dumps(public, ensure_ascii=False, indent=2) + '\n')
output.chmod(0o600)
print('발표자 명단을 private/restored-stocks.json에 복원했습니다. 공개 파일은 변경하지 않았습니다.')
