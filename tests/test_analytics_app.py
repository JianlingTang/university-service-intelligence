import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "analytics_app" / "server.py"
SPEC = importlib.util.spec_from_file_location("analytics_server", MODULE_PATH)
SERVER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SERVER)


class AnalyticsAppTests(unittest.TestCase):
    def test_summary_reconciles_core_counts(self):
        summary = SERVER.get_summary()
        self.assertEqual(summary["cases_received"], 18_000)
        self.assertGreater(summary["cases_closed"], 15_000)
        self.assertGreater(summary["response_count"], 5_000)
        self.assertTrue(0 <= summary["sla_compliance_rate"] <= 1)

    def test_service_filter_reduces_scope(self):
        overall = SERVER.get_summary()
        it_summary = SERVER.get_summary(2)
        self.assertLess(it_summary["cases_received"], overall["cases_received"])
        self.assertGreater(it_summary["cases_received"], 1_000)

    def test_scenario_returns_twelve_weeks(self):
        scenario = SERVER.run_scenario(1, 10, 5)
        self.assertEqual(len(scenario["weeks"]), 12)
        self.assertGreaterEqual(scenario["weeks_over_capacity"], 0)
        self.assertGreaterEqual(scenario["total_gap_hours"], 0)

    def test_actions_have_evidence_and_owner(self):
        actions = SERVER.get_actions()
        self.assertEqual(len(actions), 8)
        for action in actions:
            self.assertTrue(action["owner"])
            self.assertGreater(action["sample_size"], 0)
            self.assertTrue(action["recommended_action"])


if __name__ == "__main__":
    unittest.main()

