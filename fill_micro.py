"""Проставляет микроэлементы (m.micro) строкам рациона по справочнику nutrients.json.

Порция пересчитывается через калории строки (как это делает страница): микро = per × kcal / kcal_справочника.
Строки, у которых micro уже есть, не трогаются (--force — пересчитать все).

    python3 fill_micro.py            # оба дневника
    python3 fill_micro.py rodion --force
    python3 fill_micro.py rodion --meal-date YYYY-MM-DD
"""
import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKIN_SCALES_FROM = "2026-11-28"


def clean(v):
    # то же округление, что cleanMicro() на странице
    return round(v) if v >= 100 else round(v, 1) if v >= 10 else round(v, 2)


def skin_reminder(day):
    current_scales = (day.get("date") or SKIN_SCALES_FROM) >= SKIN_SCALES_FROM
    itch = day.get("itch")
    if itch is False:  # У старой отметки «нет» известна и сила зуда.
        itch = 0
    metrics = [("сыпь", day.get("rashScore"), 5), ("зуд", itch, 5 if current_scales else 3)]
    if current_scales:
        metrics.append(("уши", day.get("earScore"), 5))
    missing = [f"{label} от 0 до {limit}" for label, value, limit in metrics
               if type(value) is not int or not 0 <= value <= limit]
    if len(missing) > 1:
        missing[-2:] = [" и ".join(missing[-2:])]
    return f"Как оценишь {', '.join(missing)}?" if missing else ""


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("diaries", nargs="*", metavar="дневник")
    parser.add_argument("--force", action="store_true", help="пересчитать заполненные микроэлементы")
    parser.add_argument("--meal-date", action="append", default=[], metavar="YYYY-MM-DD",
                        help="после записи еды проверить оценки сыпи, зуда и состояния ушей у Родиона за эту дату")
    args = parser.parse_intermixed_args()
    ref = json.loads((ROOT / "nutrients.json").read_text(encoding="utf-8"))
    keys = ref["keys"]
    table = {n.lower(): p for p in ref["products"] for n in p["names"]}
    for who in args.diaries or ["rodion", "anna"]:
        path = ROOT / "data" / who / "days.json"
        days = json.loads(path.read_text(encoding="utf-8"))
        filled, missing = 0, set()
        for day in days.values():
            for m in day.get("meals", []):
                if m.get("micro") and not args.force:
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
        if who == "rodion":
            for date in dict.fromkeys(args.meal_date):
                day = days.get(date)
                if not day or not day.get("meals"):
                    print(f"{date} — нет записи еды за эту дату.")
                    continue
                reminder = skin_reminder(day)
                if reminder:
                    print(f"{date} — {reminder}")


if __name__ == "__main__":
    main()
