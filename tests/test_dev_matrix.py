"""Offline checks for scripts/run_dev_matrix.py (no paid calls)."""

import runpy
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M = runpy.run_path(str(ROOT / "scripts" / "run_dev_matrix.py"))
CORE = [f"IN{i:02d}" for i in range(1, 11)]


class Plans(unittest.TestCase):
    def test_counts_and_three_repetitions(self):
        self.assertEqual(len(M["plan_cells"]("step12", CORE, M["EVAL_MODEL"])), 60)
        self.assertEqual(len(M["plan_cells"]("step13", CORE, M["EVAL_MODEL"])), 60)
        self.assertEqual(len(M["plan_cells"]("step14", CORE, M["EVAL_MODEL"])), 120)
        for plan in ("step12", "step13", "step14"):
            ids = [c["id"] for c in M["plan_cells"](plan, CORE, M["EVAL_MODEL"])]
            self.assertEqual(len(ids), len(set(ids)), plan)
            self.assertEqual({c["rep"] for c in M["plan_cells"](plan, CORE, M["EVAL_MODEL"])}, {1, 2, 3})

    def test_identical_settings_share_one_cell_across_plans(self):
        s12 = {c["id"] for c in M["plan_cells"]("step12", CORE, M["EVAL_MODEL"])}
        s13 = {c["id"] for c in M["plan_cells"]("step13", CORE, M["EVAL_MODEL"])}
        s14 = {c["id"] for c in M["plan_cells"]("step14", CORE, M["EVAL_MODEL"])}
        self.assertEqual(len(s13 - s12), 30)   # only the multi-agent cells are new
        self.assertEqual(len(s14 - s12), 90)   # prompt, top-5 and large-document cells are new
        self.assertEqual(len(s12 & s13 & s14), 30)

    def test_model_order_is_interleaved(self):
        cells = M["plan_cells"]("step12", CORE, M["EVAL_MODEL"])
        self.assertNotEqual(cells[0]["model"], cells[2]["model"])

    def test_only_registered_settings(self):
        for c in M["plan_cells"]("step14", CORE, M["EVAL_MODEL"]):
            self.assertIn(c["k"], (3, 5))
            self.assertIn(c["doc"], ("short", "large"))
            self.assertIn(c["mode"], ("single_v2", "llm"))


class Costs(unittest.TestCase):
    def test_batch_cost_uses_reconciled_usage_only(self):
        data = {"models": {"m": {"input_usd_per_million": "1", "output_usd_per_million": "2"}},
                "batches": [{"id": "b", "model": "m", "requests": [
                    {"status": "reconciled", "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 500_000}},
                    {"status": "failed", "reserve_max_cost_usd": "0.5"}]}]}
        cost, n = M["batch_cost"](data, "b")
        self.assertEqual((cost, n), (Decimal(2), 2))

    def test_runner_refuses_without_an_approval_file(self):
        missing = M["APPROVALS"] / "step99_approval.json"
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
