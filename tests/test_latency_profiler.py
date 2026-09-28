import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_latency import percentile, summarize
from latency_profiler import LatencyRun


class LatencyProfilerTests(unittest.TestCase):
    def test_records_only_stage_timings_and_does_not_store_prompts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "runs.jsonl"
            run = LatencyRun("timer_1m", "cold", enabled=True, output=path)
            run.mark("user_request_received")
            run.mark("timer_started")
            run.mark("final_response_ready")
            run.fast_path_used = True
            run.action = "study_timer_start"
            run.increment("number_of_tool_calls")
            run.finish(success=True)

            record = json.loads(path.read_text())
            self.assertGreaterEqual(record["timer_start_latency_ms"], 0)
            self.assertEqual(record["number_of_tool_calls"], 1)
            self.assertTrue(record["fast_path_used"])
            self.assertEqual(record["action"], "study_timer_start")
            self.assertNotIn("prompt", record)
            self.assertNotIn("secret prompt text", path.read_text())

    def test_summary_reports_median_p95_and_dominant_stage(self):
        runs = [
            {"benchmark": "visual", "mode": "warm", "total_ms": total,
             "model_decision_ms": 10, "artifact_render_ms": render,
             "number_of_tool_calls": 2, "number_of_process_spawns": 1}
            for total, render in ((100, 20), (200, 150), (300, 250))
        ]
        row = summarize(runs)[0]
        self.assertEqual(row["median_ms"], 200)
        self.assertEqual(row["p95_ms"], 290)
        self.assertEqual(row["dominant_stage"], "artifact_render_ms")
        self.assertEqual(row["average_tool_calls"], 2)
        self.assertEqual(percentile([], .95), None)


if __name__ == "__main__":
    unittest.main()
