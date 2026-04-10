import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSOR = REPO_ROOT / "tools" / "process_outreach_state.py"


class OutreachReceiptTests(unittest.TestCase):
    def make_state_dir(self, temp_root: Path) -> Path:
        state_dir = temp_root / "state"
        state_dir.mkdir(parents=True)
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

    def make_plan(self, temp_root: Path) -> Path:
        plan = temp_root / "HB8_PLAN.md"
        plan.write_text(
            "# HB8 Plan\n\n"
            "## Proposed Outreach\n"
            "Platform: reddit\n"
            "Target: r/webdev\n"
            "Content: I am an AI agent testing a browser tool and would value feedback.\n"
            "Why: The audience already discusses this problem.\n",
            encoding="utf-8",
        )
        return plan

    def run_processor(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PROCESSOR), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_approved_review_stays_draft_without_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            state_dir = self.make_state_dir(temp_dir)
            plan_file = self.make_plan(temp_dir)
            outbox = temp_dir / "OUTBOX.md"
            operator_log = temp_dir / "OPERATOR_LOG.md"

            result = self.run_processor(
                "--state-dir",
                str(state_dir),
                "--outbox-target",
                str(outbox),
                "--operator-log-target",
                str(operator_log),
                "review-plan",
                "--heartbeat",
                "8",
                "--plan-file",
                str(plan_file),
                "--review-response",
                "APPROVE",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            queue = json.loads((state_dir / "outreach_queue.json").read_text(encoding="utf-8"))["items"]
            receipts = json.loads((state_dir / "outreach_receipts.json").read_text(encoding="utf-8"))["receipts"]
            self.assertEqual(queue[0]["status"], "approved_draft")
            self.assertEqual(receipts, [])

    def test_record_receipt_transitions_approved_draft_to_posted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            state_dir = self.make_state_dir(temp_dir)
            plan_file = self.make_plan(temp_dir)
            outbox = temp_dir / "OUTBOX.md"
            operator_log = temp_dir / "OPERATOR_LOG.md"

            review_result = self.run_processor(
                "--state-dir",
                str(state_dir),
                "--outbox-target",
                str(outbox),
                "--operator-log-target",
                str(operator_log),
                "review-plan",
                "--heartbeat",
                "8",
                "--plan-file",
                str(plan_file),
                "--review-response",
                "APPROVE",
            )
            self.assertEqual(review_result.returncode, 0, msg=review_result.stderr)

            receipt_result = self.run_processor(
                "--state-dir",
                str(state_dir),
                "--outbox-target",
                str(outbox),
                "--operator-log-target",
                str(operator_log),
                "record-receipt",
                "--item-id",
                "hb8-outreach-1",
                "--receipt-type",
                "public_url",
                "--receipt-value",
                "https://example.com/post/123",
            )

            self.assertEqual(receipt_result.returncode, 0, msg=receipt_result.stderr)
            queue = json.loads((state_dir / "outreach_queue.json").read_text(encoding="utf-8"))["items"]
            receipts = json.loads((state_dir / "outreach_receipts.json").read_text(encoding="utf-8"))["receipts"]
            operator_events = [
                json.loads(line)
                for line in (state_dir / "operator_events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

            self.assertEqual(queue[0]["status"], "posted")
            self.assertEqual(receipts[0]["item_id"], "hb8-outreach-1")
            self.assertTrue(receipts[0]["validated"])
            self.assertEqual(operator_events[-1]["action"], "outreach_posted")
            self.assertIn("public_url", outbox.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
