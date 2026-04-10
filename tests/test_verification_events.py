import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "verification_events.py"


class VerificationEventsTests(unittest.TestCase):
    def run_tool(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(TOOL), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_init_and_append_synthetic_event_updates_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            events_path = temp_dir / "verification_events.jsonl"
            summary_path = temp_dir / "analytics_summary.json"

            init_result = self.run_tool(
                "--events-path",
                str(events_path),
                "--summary-path",
                str(summary_path),
                "init",
            )
            self.assertEqual(init_result.returncode, 0, msg=init_result.stderr)

            append_result = self.run_tool(
                "--events-path",
                str(events_path),
                "--summary-path",
                str(summary_path),
                "append-synthetic",
                "--user-seed",
                "user-a",
                "--source",
                "synthetic",
            )
            self.assertEqual(append_result.returncode, 0, msg=append_result.stderr)

            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["verified_user_count"], 1)
            self.assertEqual(summary["event_count"], 1)
            self.assertEqual(summary["sources"]["synthetic"], 1)

    def test_import_jsonl_and_count_unique_users(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            events_path = temp_dir / "verification_events.jsonl"
            summary_path = temp_dir / "analytics_summary.json"
            import_path = temp_dir / "import.jsonl"

            import_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "schema_version": "clawwars/vnext/verification_event@1",
                                "event_id": "evt1",
                                "event_type": "core_action_completed",
                                "anonymous_user_id": "anon_same",
                                "occurred_at": "2026-04-10T10:00:00Z",
                                "source": "collector_sync",
                                "metadata": {},
                            }
                        ),
                        json.dumps(
                            {
                                "schema_version": "clawwars/vnext/verification_event@1",
                                "event_id": "evt2",
                                "event_type": "core_action_completed",
                                "anonymous_user_id": "anon_same",
                                "occurred_at": "2026-04-10T10:05:00Z",
                                "source": "collector_sync",
                                "metadata": {},
                            }
                        ),
                        json.dumps(
                            {
                                "schema_version": "clawwars/vnext/verification_event@1",
                                "event_id": "evt3",
                                "event_type": "core_action_completed",
                                "anonymous_user_id": "anon_other",
                                "occurred_at": "2026-04-10T10:06:00Z",
                                "source": "collector_sync",
                                "metadata": {},
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            init_result = self.run_tool(
                "--events-path",
                str(events_path),
                "--summary-path",
                str(summary_path),
                "init",
            )
            self.assertEqual(init_result.returncode, 0, msg=init_result.stderr)

            import_result = self.run_tool(
                "--events-path",
                str(events_path),
                "--summary-path",
                str(summary_path),
                "import",
                "--input",
                str(import_path),
            )
            self.assertEqual(import_result.returncode, 0, msg=import_result.stderr)

            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["verified_user_count"], 2)
            self.assertEqual(summary["event_count"], 3)
            self.assertEqual(summary["sources"]["collector_sync"], 3)


if __name__ == "__main__":
    unittest.main()
