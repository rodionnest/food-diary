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
        for score in range(6):
            for itch in (False, True):
                self.assertEqual(fill_micro.skin_reminder({"rashScore": score, "itch": itch}), "")
        self.assertEqual(fill_micro.skin_reminder({"rashScore": 0}), "Был ли зуд?")
        self.assertEqual(fill_micro.skin_reminder({"itch": False}), "Как оценишь сыпь от 0 до 5?")
        for score in (None, -1, 6, 2.5, True, "0"):
            with self.subTest(score=score):
                self.assertEqual(fill_micro.skin_reminder({"rashScore": score, "itch": None}),
                                 "Как оценишь сыпь от 0 до 5 и был ли зуд?")

    def test_meal_check_only_prompts_for_requested_dates_and_diary(self):
        dates = ["2000-01-01", "2000-01-02", "2000-01-03"]
        days = {d: {"date": d, "meals": [{"name": "test", "kcal": 10}]} for d in dates}
        days[dates[1]].update(rashScore=0, itch=False)
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
                self.assertEqual(json.loads((root / "data" / diary / "days.json").read_text("utf-8")), days)
