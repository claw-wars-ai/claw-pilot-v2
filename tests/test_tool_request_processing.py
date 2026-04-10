import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSOR = REPO_ROOT / "tools" / "process_tool_requests.py"


class ToolRequestProcessingTests(unittest.TestCase):
    def make_state_dir(self, temp_root: Path) -> Path:
        state_dir = temp_root / "state"
        (state_dir / "tool_requests").mkdir(parents=True)
        (state_dir / "tool_grants.json").write_text(
            json.dumps({"schema_version": "clawwars/vnext/tool_grants@1", "grants": []}, indent=2) + "\n",
            encoding="utf-8",
        )
        return state_dir

    def run_processor(self, state_dir: Path, render_target: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PROCESSOR), "--state-dir", str(state_dir), "--render-target", str(render_target)],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_low_risk_request_is_auto_granted_and_rendered(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            state_dir = self.make_state_dir(temp_dir)
            request = {
                "id": "hb3-github-pages",
                "heartbeat": 3,
                "tool": "GitHub Pages deployment",
                "why": "Need the approved public deployment lane.",
                "plan": "Push the static site to GitHub Pages for G2 verification.",
                "risk": "low",
                "alternatives_considered": ["Local-only preview is not enough for G2."],
            }
            (state_dir / "tool_requests" / "hb3-github-pages.json").write_text(
                json.dumps(request, indent=2) + "\n",
                encoding="utf-8",
            )

            render_target = temp_dir / "TOOL_GRANTS.md"
            result = self.run_processor(state_dir, render_target)

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            grants = json.loads((state_dir / "tool_grants.json").read_text(encoding="utf-8"))["grants"]
            self.assertEqual(grants[0]["status"], "auto_granted")
            self.assertEqual(grants[0]["request_id"], "hb3-github-pages")
            rendered = render_target.read_text(encoding="utf-8")
            self.assertIn("GitHub Pages deployment", rendered)
            self.assertIn("auto_granted", rendered)

    def test_missing_required_fields_becomes_invalid_with_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            state_dir = self.make_state_dir(temp_dir)
            request = {
                "id": "hb4-missing-plan",
                "heartbeat": 4,
                "tool": "Browser automation",
                "why": "Need scripted verification.",
                "risk": "MEDIUM",
                "alternatives_considered": ["Manual testing is slower."],
            }
            (state_dir / "tool_requests" / "hb4-missing-plan.json").write_text(
                json.dumps(request, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_processor(state_dir, temp_dir / "TOOL_GRANTS.md")

            self.assertEqual(result.returncode, 1)
            grants = json.loads((state_dir / "tool_grants.json").read_text(encoding="utf-8"))["grants"]
            self.assertEqual(grants[0]["status"], "invalid")
            self.assertIn("missing required fields: plan", grants[0]["reason"])

    def test_malformed_json_request_becomes_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            state_dir = self.make_state_dir(temp_dir)
            (state_dir / "tool_requests" / "broken.json").write_text(
                '{"id": "broken", "heartbeat": 2,',
                encoding="utf-8",
            )

            result = self.run_processor(state_dir, temp_dir / "TOOL_GRANTS.md")

            self.assertEqual(result.returncode, 1)
            grants = json.loads((state_dir / "tool_grants.json").read_text(encoding="utf-8"))["grants"]
            self.assertEqual(grants[0]["status"], "invalid")
            self.assertIn("invalid JSON", grants[0]["reason"])


if __name__ == "__main__":
    unittest.main()
