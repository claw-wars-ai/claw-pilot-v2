import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSOR = REPO_ROOT / "tools" / "process_outreach_state.py"


class DistributionPolicyTests(unittest.TestCase):
    def make_state_dir(self, temp_root: Path) -> Path:
        state_dir = temp_root / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "distribution_policy.json").write_text(
            json.dumps(
                {
                    "schema_version": "clawwars/vnext/distribution_policy@1",
                    "default_surface": "reddit_public_post",
                    "additional_surface": "hackernews_show_hn",
                    "surfaces": [
                        {
                            "id": "reddit_public_post",
                            "platform": "reddit",
                            "target_rule": "non-empty public subreddit or thread target",
                            "status": "enabled",
                            "notes": "baseline",
                        },
                        {
                            "id": "hackernews_show_hn",
                            "platform": "hackernews_show_hn",
                            "target_rule": "target must be exactly show-hn",
                            "status": "enabled",
                            "notes": "narrow extension",
                        },
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (state_dir / "outreach_queue.json").write_text(
            json.dumps({"schema_version": "clawwars/vnext/outreach_queue@1", "items": []}, indent=2) + "\n",
            encoding="utf-8",
        )
        (state_dir / "outreach_receipts.json").write_text(
            json.dumps({"schema_version": "clawwars/vnext/outreach_receipts@1", "receipts": []}, indent=2) + "\n",
            encoding="utf-8",
        )
        (state_dir / "operator_events.jsonl").write_text("", encoding="utf-8")
        return state_dir

    def run_processor(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PROCESSOR), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_hackernews_show_hn_surface_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            state_dir = self.make_state_dir(temp_dir)
            plan_file = temp_dir / "HB9_PLAN.md"
            outbox = temp_dir / "OUTBOX.md"
            operator_log = temp_dir / "OPERATOR_LOG.md"
            plan_file.write_text(
                "# HB9 Plan\n\n"
                "## Proposed Outreach\n"
                "Platform: hackernews_show_hn\n"
                "Target: show-hn\n"
                "Content: Show HN: an AI-agent-built browser tool for a narrow workflow problem.\n"
                "Why: This is a public Show HN submission.\n",
                encoding="utf-8",
            )

            result = self.run_processor(
                "--state-dir",
                str(state_dir),
                "--outbox-target",
                str(outbox),
                "--operator-log-target",
                str(operator_log),
                "review-plan",
                "--heartbeat",
                "9",
                "--plan-file",
                str(plan_file),
                "--review-response",
                "APPROVE",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            queue = json.loads((state_dir / "outreach_queue.json").read_text(encoding="utf-8"))["items"]
            self.assertEqual(queue[0]["surface"], "hackernews_show_hn")
            self.assertEqual(queue[0]["status"], "approved_draft")

    def test_unsupported_surface_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            state_dir = self.make_state_dir(temp_dir)
            plan_file = temp_dir / "HB9_PLAN.md"
            outbox = temp_dir / "OUTBOX.md"
            operator_log = temp_dir / "OPERATOR_LOG.md"
            plan_file.write_text(
                "# HB9 Plan\n\n"
                "## Proposed Outreach\n"
                "Platform: twitter_dm\n"
                "Target: @someone\n"
                "Content: hi\n",
                encoding="utf-8",
            )

            result = self.run_processor(
                "--state-dir",
                str(state_dir),
                "--outbox-target",
                str(outbox),
                "--operator-log-target",
                str(operator_log),
                "review-plan",
                "--heartbeat",
                "9",
                "--plan-file",
                str(plan_file),
                "--review-response",
                "APPROVE",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unsupported outreach platform", result.stderr)


if __name__ == "__main__":
    unittest.main()
