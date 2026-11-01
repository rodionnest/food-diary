"""Экспорт публичного снимка в docs без изменения исходных данных."""
import getpass
import subprocess
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
PIN_GATE = """<style>
html[data-pin-locked] body > :not(#pinGate){display:none!important}
html[data-pin-locked] body{margin:0;min-height:100vh;background:#f4f3f1;color:#222}
#pinGate{position:fixed;inset:0;z-index:9999;display:grid;place-items:center;padding:20px;font:16px system-ui;background:#f4f3f1;color:#222}
#pinGate form{box-sizing:border-box;width:min(100%,360px);padding:28px;background:white;border:1px solid #ddd;border-radius:18px;display:grid;gap:14px}
#pinGate h1,#pinGate p{margin:0}#pinGate h1{font-size:24px}#pinGate label{font-size:14px}
#pinGate input,#pinGate button{box-sizing:border-box;width:100%;padding:12px;font:inherit;border:1px solid #aaa;border-radius:9px}
#pinGate input{font-size:24px;text-align:center;letter-spacing:8px}#pinGate button{background:#333;color:white;cursor:pointer}
#pinError{min-height:2.6em;color:#b42318;font-size:14px}
</style><script src="pin-gate.js"></script>"""


def with_pin_gate(page):
    return page.replace('<html', '<html data-pin-locked', 1).replace('<head>', '<head>' + PIN_GATE, 1)


DIARIES = {'rodion': ('Дневник Родион.html', 'Дневник Родиона'),
           'anna': ('Дневник Анны.html', 'Дневник Анны')}


def export(root=ROOT, pin=None):
    if pin is None or len(pin) != 4 or not pin.isascii() or not pin.isdigit():
        raise ValueError("Для экспорта нужен четырёхзначный PIN")
    snapshot = {'updatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'diaries': {}}
    # Сначала читаем и проверяем все данные: отсутствие дней — ошибка экспорта.
    for diary in DIARIES:
        collections = {}
        for collection in ('days', 'products', 'suspects'):
            path = root / 'data' / diary / f'{collection}.json'
            value = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            if not isinstance(value, dict):
                raise ValueError(f'{path}: ожидается JSON-объект')
            if collection == 'days':
                if not value or any(not isinstance(day, dict) or day.get('date') != date for date, day in value.items()):
                    raise ValueError(f'{path}: нужны реальные дни с совпадающими датами')
                value = dict(sorted(value.items(), reverse=True))
            collections[collection] = value
        snapshot['diaries'][diary] = collections
    encrypted = subprocess.run(
        ['node', str(ROOT / 'encrypt-snapshot.cjs')],
        input=json.dumps({'pin': pin, 'snapshot': snapshot}, ensure_ascii=False),
        text=True, capture_output=True, check=True,
    ).stdout
    files = {}
    for diary, (filename, _) in DIARIES.items():
        page = (root / filename).read_text(encoding='utf-8')
        page = page.replace(f'<script src="local-claude.js" data-diary="{diary}"></script>',
                            f'<script src="snapshot-encrypted.js"></script><script src="static-diary.js" data-diary="{diary}"></script>')
        page = page.replace('<body>', '<body><nav style="padding:12px"><a href="index.html">← Все дневники</a></nav>', 1)
        files[filename] = with_pin_gate(page)
    for filename in ('static-diary.js', 'pin-gate.js', 'favicon.svg'):
        files[filename] = (root / filename).read_text(encoding='utf-8')
    files['snapshot-encrypted.js'] = 'window.ENCRYPTED_DIARY = ' + encrypted + ';\n'
    links = ''.join(f'<p><a href="{quote(filename)}">{title}</a></p>' for filename, title in DIARIES.values())
    files['index.html'] = with_pin_gate(f'''<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Дневники питания</title>
<script src="snapshot-encrypted.js"></script><link rel="icon" href="favicon.svg"><style>body{{font:18px system-ui;max-width:600px;margin:60px auto;padding:20px}}a{{display:block;padding:20px;border:1px solid #ccc;border-radius:14px;color:inherit}}</style>
</head><body><h1>Дневники питания</h1>{links}<p>Только просмотр. Снимок обновлён: {snapshot['updatedAt']}.</p></body></html>''')
    files['.nojekyll'] = ''
    output = root / 'docs'
    output.mkdir(exist_ok=True)
    for filename, text in files.items():
        target = output / filename
        temporary = target.with_name(target.name + '.tmp')
        temporary.write_text(text, encoding='utf-8')
        os.replace(temporary, target)
    # Удаляем только известные открытые ресурсы предыдущей версии.
    for filename in ('snapshot-data.js', 'nutrients.json'):
        (output / filename).unlink(missing_ok=True)
    return snapshot


if __name__ == '__main__':
    result = export(pin=os.environ.get("DIARY_PIN") or getpass.getpass("PIN снимка: "))
    print(f"Снимок docs/ обновлён: {result['updatedAt']}")
