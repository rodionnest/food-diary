import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import fill_micro


class MealReminderTests(unittest.TestCase):
    def test_missing_skin_metrics_are_independent(self):
        day = {"date": "2026-11-28", "rashScore": 0, "itch": 0, "earScore": 0}
        for field, name in (("rashScore", "сыпь"), ("itch", "зуд"), ("earScore", "уши")):
            for score in range(6):
                with self.subTest(field=field, score=score):
                    self.assertEqual(fill_micro.skin_reminder({**day, field: score}), "")
            for value in (None, True, -1, 6, 1.5, "0"):
                with self.subTest(field=field, value=value):
                    self.assertEqual(fill_micro.skin_reminder({**day, field: value}),
                                     f"Как оценишь {name} от 0 до 5?")
        self.assertEqual(fill_micro.skin_reminder({**day, "itch": False}), "")
        self.assertEqual(fill_micro.skin_reminder({**day, "earScore": False}), "Как оценишь уши от 0 до 5?")
        self.assertEqual(fill_micro.skin_reminder({"rashScore": 0, "note": "уши норм"}),
                         "Как оценишь зуд от 0 до 5 и уши от 0 до 5?")
        self.assertEqual(fill_micro.skin_reminder({}),
                         "Как оценишь сыпь от 0 до 5, зуд от 0 до 5 и уши от 0 до 5?")

    def test_historical_itch_scale_and_ear_reminder(self):
        day = {"date": "2026-11-27", "rashScore": 1}
        for itch in (0, 1, 2, 3, False):
            self.assertEqual(fill_micro.skin_reminder({**day, "itch": itch}), "")
        for itch in (None, True, 4, 5):
            self.assertEqual(fill_micro.skin_reminder({**day, "itch": itch}), "Как оценишь зуд от 0 до 3?")

    def test_meal_check_only_prompts_for_requested_dates_and_diary(self):
        dates = ["2026-11-28", "2026-11-29", "2026-11-30"]
        days = {d: {"date": d, "meals": [{"name": "test", "kcal": 10}]} for d in dates}
        days[dates[0]].update(rashScore=0, itch=4)
        days[dates[1]].update(rashScore=0, itch=5, earScore=0)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "nutrients.json").write_text('{"keys": [], "products": []}', encoding="utf-8")
            for diary in ("rodion", "anna"):
                path = root / "data" / diary / "days.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(days), encoding="utf-8")
            for diary, expected in (("rodion", [dates[0]]), ("anna", [])):
                args = ["fill_micro.py", diary, "--meal-date", dates[0], "--meal-date", dates[1]]
                out = io.StringIO()
                with patch.object(fill_micro, "ROOT", root), patch("sys.argv", args), redirect_stdout(out):
                    fill_micro.main()
                questions = [line.split()[0] for line in out.getvalue().splitlines() if line.endswith("?")]
                self.assertEqual(questions, expected)
                if expected:
                    self.assertIn(f"{dates[0]} — Как оценишь уши от 0 до 5?", out.getvalue())
                self.assertEqual(json.loads((root / "data" / diary / "days.json").read_text("utf-8")), days)
