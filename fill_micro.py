"""Проставляет микроэлементы (m.micro) строкам рациона по справочнику nutrients.json.

Порция пересчитывается через калории строки (как это делает страница): микро = per × kcal / kcal_справочника.
Строки, у которых micro уже есть, не трогаются (--force — пересчитать все).

    python3 fill_micro.py            # оба дневника
    python3 fill_micro.py rodion --force
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def clean(v):
    # то же округление, что cleanMicro() на странице
    return round(v) if v >= 100 else round(v, 1) if v >= 10 else round(v, 2)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    force = "--force" in sys.argv
    ref = json.loads((ROOT / "nutrients.json").read_text(encoding="utf-8"))
    keys = ref["keys"]
    table = {n.lower(): p for p in ref["products"] for n in p["names"]}
    for who in args or ["rodion", "anna"]:
        path = ROOT / "data" / who / "days.json"
        days = json.loads(path.read_text(encoding="utf-8"))
        filled, missing = 0, set()
        for day in days.values():
            for m in day.get("meals", []):
                if m.get("micro") and not force:
                    continue
                p = table.get(m["name"].lower().strip())
                if not p:
                    missing.add(m["name"])
                    continue
                k = 1 if p.get("portion") else m["kcal"] / p["kcal"]
                micro = {key: clean(v * k) for key, v in zip(keys, p["per"]) if v * k > 0}
                if micro:
                    m["micro"] = micro
                    filled += 1
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(days, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, path)
        print(f"{who}: заполнено {filled}" + (f"; нет в справочнике: {', '.join(sorted(missing))}" if missing else ""))


if __name__ == "__main__":
    main()
