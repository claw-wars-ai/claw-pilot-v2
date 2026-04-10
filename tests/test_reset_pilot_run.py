import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "reset_pilot_run.py"


class ResetPilotRunTests(unittest.TestCase):
    def run_tool(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(TOOL), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def make_repo(self, temp_root: Path) -> tuple[Path, Path, Path]:
        repo_root = temp_root / "repo"
        state_dir = repo_root / "state"
        workspace = repo_root / "pilot-workspace"
        tool_requests = state_dir / "tool_requests"
        tool_requests.mkdir(parents=True)
        workspace.mkdir(parents=True)

        (repo_root / "OBJECTIVE.md").write_text("# Objective\n\nfresh\n", encoding="utf-8")
        (repo_root / "TOOL_GRANTS.md").write_text("# TOOL GRANTS\n", encoding="utf-8")
        (repo_root / "OUTBOX.md").write_text("# OUTBOX\n", encoding="utf-8")
        (repo_root / "OPERATOR_LOG.md").write_text("# OPERATOR LOG\n", encoding="utf-8")

        (state_dir / "run.json").write_text(
            json.dumps(
                {
                    "schema_version": "clawwars/vnext/run@1",
                    "run_id": "old-run",
                    "pilot_class": "pilot_b",
                    "status": "completed",
                    "current_heartbeat": 8,
                    "max_heartbeats": 20,
                    "updated_at": "2026-04-10T10:00:00Z",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (state_dir / "preflight.json").write_text(
            json.dumps(
                {
                    "schema_version": "clawwars/vnext/preflight@1",
                    "checked_at": "2026-04-10T10:00:00Z",
                    "passed": True,
                    "checks": [{"name": "ok", "passed": True, "detail": "ok"}],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (state_dir / "gates.json").write_text(
            json.dumps(
                {
                    "schema_version": "clawwars/vnext/gates@1",
                    "gates": {
                        "G1": {"status": "pass", "description": "a", "evidence": ["x"]},
                        "G2": {"status": "pass", "description": "b", "evidence": ["x"]},
                        "G3": {"status": "pass", "description": "c", "evidence": ["x"]},
                        "G4": {"status": "pass", "description": "d", "evidence": ["x"]},
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (state_dir / "deployment.json").write_text(
            json.dumps(
                {
                    "schema_version": "clawwars/vnext/deployment@1",
                    "status": "configured",
                    "product_lane": {
                        "kind": "github_pages",
                        "mode": "github_actions",
                        "repository": "repo",
                        "owner": "owner",
                        "branch": "gh-pages",
                        "site_path": "/",
                        "public_url": "https://example.test",
                        "url_verified": True,
                        "required_env_vars": ["GITHUB_PAGES_OWNER"],
                        "verified_at": "2026-04-10T10:00:00Z",
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (state_dir / "verification_config.json").write_text(
            json.dumps(
                {
                    "schema_version": "clawwars/vnext/verification_config@1",
                    "status": "configured",
                    "lane": {
                        "kind": "operator_managed_collector",
                        "readiness": "ready",
                        "write_endpoint": "https://collector.example.test/write",
                        "read_path": "/tmp/export.jsonl",
                        "read_format": "jsonl",
                        "summary_path": "state/analytics_summary.json",
                        "client_event_contract": {
                            "event_type": "core_action_completed",
                            "anonymous_user_id_field": "anonymous_user_id",
                            "timestamp_field": "occurred_at",
                            "metadata_rules": "No PII.",
                        },
                        "sync_contract": {
                            "import_format": "jsonl",
                            "import_command": "python tools/verification_events.py import --input <export-path>",
                            "derive_command": "python tools/verification_events.py derive-summary",
                        },
                        "env_vars": ["CLAW_VERIFY_WRITE_ENDPOINT", "CLAW_VERIFY_READ_PATH"],
                        "pii_policy": "anonymous_only",
                        "verified_user_runs_require_lane": True,
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (state_dir / "analytics_summary.json").write_text(
            json.dumps(
                {
                    "schema_version": "clawwars/vnext/analytics_summary@1",
                    "verified_user_count": 2,
                    "event_count": 3,
                    "last_event_at": "2026-04-10T10:00:00Z",
                    "sources": {"collector_sync": 3},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (state_dir / "tool_grants.json").write_text(
            json.dumps(
                {
                    "schema_version": "clawwars/vnext/tool_grants@1",
                    "grants": [
                        {
                            "id": "bootstrap",
                            "tool": "GitHub Pages deployment",
                            "status": "granted",
                            "source": "bootstrap",
                        },
                        {
                            "id": "hb2-temp",
                            "tool": "Another tool",
                            "status": "auto_granted",
                            "source": "request_file",
                        },
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
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
                            "target_rule": "target",
                            "status": "enabled",
                            "notes": "baseline",
                        },
                        {
                            "id": "hackernews_show_hn",
                            "platform": "hackernews_show_hn",
                            "target_rule": "show-hn",
                            "status": "enabled",
                            "notes": "extension",
                        },
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (state_dir / "outreach_queue.json").write_text(
            json.dumps(
                {
                    "schema_version": "clawwars/vnext/outreach_queue@1",
                    "items": [{"id": "hb7-outreach-1", "heartbeat": 7, "status": "posted", "platform": "reddit", "target": "r/test", "content": "x"}],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (state_dir / "outreach_receipts.json").write_text(
            json.dumps(
                {
                    "schema_version": "clawwars/vnext/outreach_receipts@1",
                    "receipts": [
                        {
                            "item_id": "hb7-outreach-1",
                            "receipt_type": "public_url",
                            "receipt_value": "https://example.test/post",
                            "recorded_at": "2026-04-10T10:00:00Z",
                            "validated": True,
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (state_dir / "verification_events.jsonl").write_text(
            json.dumps(
                {
                    "schema_version": "clawwars/vnext/verification_event@1",
                    "event_id": "evt1",
                    "event_type": "core_action_completed",
                    "anonymous_user_id": "anon_1",
                    "occurred_at": "2026-04-10T10:00:00Z",
                    "source": "collector_sync",
                    "metadata": {},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (state_dir / "operator_events.jsonl").write_text(
            json.dumps(
                {
                    "event_id": "evt1",
                    "action": "outreach_posted",
                    "actor": "orchestrator",
                    "occurred_at": "2026-04-10T10:00:00Z",
                    "details": {"item_id": "hb7-outreach-1"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (tool_requests / "README.md").write_text("docs\n", encoding="utf-8")
        (tool_requests / "hb2-temp.json").write_text('{"id":"hb2-temp"}\n', encoding="utf-8")

        (workspace / "HB1_PLAN.md").write_text("# HB1\n", encoding="utf-8")
        (workspace / "HB1_EXECUTION.md").write_text("# HB1\n", encoding="utf-8")
        (workspace / "OBJECTIVE.md").write_text("old objective\n", encoding="utf-8")
        (workspace / "JOURNEY.md").write_text("old journey\n", encoding="utf-8")
        (workspace / "RESOURCES.md").write_text("old resources\n", encoding="utf-8")
        (workspace / ".heartbeat.lock").write_text("123\n", encoding="utf-8")
        logs_dir = workspace / "logs"
        logs_dir.mkdir()
        (logs_dir / "hb1.log").write_text("log\n", encoding="utf-8")
        return repo_root, state_dir, workspace

    def test_reset_archives_runtime_state_and_prepares_blank_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_root = Path(temp_dir_str)
            repo_root, state_dir, workspace = self.make_repo(temp_root)

            result = self.run_tool(
                "--repo-root",
                str(repo_root),
                "--state-dir",
                str(state_dir),
                "--workspace",
                str(workspace),
                "--run-id",
                "fresh-run-001",
                "--pilot-class",
                "pilot_a",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)

            run = json.loads((state_dir / "run.json").read_text(encoding="utf-8"))
            deployment = json.loads((state_dir / "deployment.json").read_text(encoding="utf-8"))
            analytics = json.loads((state_dir / "analytics_summary.json").read_text(encoding="utf-8"))
            grants = json.loads((state_dir / "tool_grants.json").read_text(encoding="utf-8"))["grants"]
            queue = json.loads((state_dir / "outreach_queue.json").read_text(encoding="utf-8"))["items"]
            receipts = json.loads((state_dir / "outreach_receipts.json").read_text(encoding="utf-8"))["receipts"]

            self.assertEqual(run["run_id"], "fresh-run-001")
            self.assertEqual(run["current_heartbeat"], 0)
            self.assertEqual(run["max_heartbeats"], 10)
            self.assertEqual(run["status"], "not_started")
            self.assertIsNone(deployment["product_lane"]["public_url"])
            self.assertFalse(deployment["product_lane"]["url_verified"])
            self.assertEqual(analytics["verified_user_count"], 0)
            self.assertEqual(analytics["event_count"], 0)
            self.assertEqual(queue, [])
            self.assertEqual(receipts, [])
            self.assertEqual(len(grants), 1)
            self.assertEqual(grants[0]["source"], "bootstrap")
            self.assertEqual((state_dir / "verification_events.jsonl").read_text(encoding="utf-8"), "")
            self.assertEqual((state_dir / "operator_events.jsonl").read_text(encoding="utf-8"), "")
            self.assertFalse((state_dir / "tool_requests" / "hb2-temp.json").exists())

            self.assertTrue((workspace / "OBJECTIVE.md").exists())
            self.assertEqual((workspace / "OBJECTIVE.md").read_text(encoding="utf-8"), "# Objective\n\nfresh\n")
            self.assertTrue((workspace / "JOURNEY.md").exists())
            self.assertTrue((workspace / "RESOURCES.md").exists())
            self.assertFalse((workspace / "HB1_PLAN.md").exists())
            self.assertFalse((workspace / ".heartbeat.lock").exists())
            self.assertEqual(list((workspace / "logs").iterdir()), [])

            state_archives = list((state_dir / "archive").iterdir())
            workspace_archives = list((workspace / "archive").iterdir())
            self.assertEqual(len(state_archives), 1)
            self.assertEqual(len(workspace_archives), 1)
            archived_run = json.loads((state_archives[0] / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(archived_run["run_id"], "old-run")
            self.assertTrue((workspace_archives[0] / "HB1_PLAN.md").exists())


if __name__ == "__main__":
    unittest.main()
