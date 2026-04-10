import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "orchestrator_state.py"


class SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


class OrchestratorStateTests(unittest.TestCase):
    def run_tool(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(TOOL), *args],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def make_state_dir(self, temp_root: Path) -> Path:
        state_dir = temp_root / "state"
        (state_dir / "tool_requests").mkdir(parents=True)
        (state_dir / "run.json").write_text(
            json.dumps(
                {
                    "schema_version": "clawwars/vnext/run@1",
                    "run_id": "test-run",
                    "pilot_class": "pilot_a",
                    "status": "not_started",
                    "current_heartbeat": 0,
                    "max_heartbeats": 20,
                    "updated_at": "1970-01-01T00:00:00Z",
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
                    "checked_at": "1970-01-01T00:00:00Z",
                    "passed": False,
                    "checks": [{"name": "not_run", "passed": False, "detail": "not run"}],
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
        (state_dir / "gates.json").write_text(
            json.dumps(
                {
                    "schema_version": "clawwars/vnext/gates@1",
                    "gates": {
                        "G1": {"status": "pending", "description": "Problem identified with evidence.", "evidence": []},
                        "G2": {"status": "pending", "description": "Public product deployed and URL verified.", "evidence": []},
                        "G3": {"status": "pending", "description": "At least one receipt-backed outreach item posted.", "evidence": []},
                        "G4": {"status": "pending", "description": "At least one verified external core action recorded.", "evidence": []},
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
                        "public_url": None,
                        "url_verified": False,
                        "required_env_vars": ["GITHUB_PAGES_OWNER", "GITHUB_PAGES_REPO", "GITHUB_PAGES_TOKEN"],
                        "verified_at": None,
                    },
                    "notes": "test",
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
                        "read_path": str(state_dir / "collector_export.jsonl"),
                        "read_format": "jsonl",
                        "summary_path": "state/analytics_summary.json",
                        "client_event_contract": {
                            "event_type": "core_action_completed",
                            "anonymous_user_id_field": "anonymous_user_id",
                            "timestamp_field": "occurred_at",
                            "metadata_rules": "No PII. Anonymous stable IDs or hashes only.",
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
                    "notes": "test",
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
                    "verified_user_count": 0,
                    "event_count": 0,
                    "last_event_at": None,
                    "sources": {},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (state_dir / "tool_grants.json").write_text(
            json.dumps({"schema_version": "clawwars/vnext/tool_grants@1", "grants": []}, indent=2) + "\n",
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
        (state_dir / "verification_events.jsonl").write_text("", encoding="utf-8")
        (state_dir / "operator_events.jsonl").write_text("", encoding="utf-8")
        return state_dir

    def test_preflight_writes_structured_failure_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            state_dir = self.make_state_dir(temp_dir)
            workspace = temp_dir / "workspace"
            workspace.mkdir()
            env = {"PATH": "", "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}

            result = self.run_tool(
                "--state-dir",
                str(state_dir),
                "--workspace",
                str(workspace),
                "preflight",
                env=env,
            )

            self.assertNotEqual(result.returncode, 0)
            preflight = json.loads((state_dir / "preflight.json").read_text(encoding="utf-8"))
            self.assertFalse(preflight["passed"])
            check_names = {check["name"] for check in preflight["checks"]}
            self.assertIn("openclaw_in_path", check_names)
            self.assertIn("reviewer_auth_present", check_names)

    def test_preflight_flags_missing_reviewer_key_even_when_openclaw_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            state_dir = self.make_state_dir(temp_dir)
            workspace = temp_dir / "workspace"
            workspace.mkdir()
            (workspace / "OBJECTIVE.md").write_text("# Objective\n", encoding="utf-8")
            bin_dir = temp_dir / "bin"
            bin_dir.mkdir()
            (bin_dir / "openclaw.cmd").write_text("@echo off\nexit /b 0\n", encoding="utf-8")
            verification_export = state_dir / "collector_export.jsonl"
            verification_export.write_text("", encoding="utf-8")

            env = {
                "PATH": str(bin_dir),
                "PATHEXT": ".COM;.EXE;.BAT;.CMD",
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                "GITHUB_PAGES_OWNER": "owner",
                "GITHUB_PAGES_REPO": "repo",
                "GITHUB_PAGES_TOKEN": "token",
                "CLAW_VERIFY_WRITE_ENDPOINT": "https://collector.example.test/write",
                "CLAW_VERIFY_READ_PATH": str(verification_export),
            }

            result = self.run_tool(
                "--state-dir",
                str(state_dir),
                "--workspace",
                str(workspace),
                "preflight",
                env=env,
            )

            self.assertNotEqual(result.returncode, 0)
            preflight = json.loads((state_dir / "preflight.json").read_text(encoding="utf-8"))
            checks = {check["name"]: check for check in preflight["checks"]}
            self.assertTrue(checks["openclaw_in_path"]["passed"])
            self.assertFalse(checks["reviewer_auth_present"]["passed"])

    def test_preflight_flags_missing_workspace_objective(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            state_dir = self.make_state_dir(temp_dir)
            workspace = temp_dir / "workspace"
            workspace.mkdir()

            result = self.run_tool(
                "--state-dir",
                str(state_dir),
                "--workspace",
                str(workspace),
                "preflight",
                env={"PATH": "", "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")},
            )

            self.assertNotEqual(result.returncode, 0)
            preflight = json.loads((state_dir / "preflight.json").read_text(encoding="utf-8"))
            checks = {check["name"]: check for check in preflight["checks"]}
            self.assertIn("workspace_objective_seeded", checks)
            self.assertFalse(checks["workspace_objective_seeded"]["passed"])

    def test_update_gates_uses_canonical_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            state_dir = self.make_state_dir(temp_dir)
            site_root = temp_dir / "site"
            site_root.mkdir()
            (site_root / "index.html").write_text("<html>ok</html>", encoding="utf-8")

            handler = partial(SilentHandler, directory=str(site_root))
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(thread.join, 1)
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)

            deployment = json.loads((state_dir / "deployment.json").read_text(encoding="utf-8"))
            deployment["product_lane"]["public_url"] = f"http://127.0.0.1:{server.server_port}/index.html"
            (state_dir / "deployment.json").write_text(json.dumps(deployment, indent=2) + "\n", encoding="utf-8")

            outreach = {
                "schema_version": "clawwars/vnext/outreach_queue@1",
                "items": [
                    {
                        "id": "hb8-outreach-1",
                        "heartbeat": 8,
                        "status": "posted",
                        "platform": "reddit",
                        "target": "r/webdev",
                        "content": "test",
                    }
                ],
            }
            (state_dir / "outreach_queue.json").write_text(json.dumps(outreach, indent=2) + "\n", encoding="utf-8")
            receipts = {
                "schema_version": "clawwars/vnext/outreach_receipts@1",
                "receipts": [
                    {
                        "receipt_id": "hb8-outreach-1:public_url",
                        "item_id": "hb8-outreach-1",
                        "receipt_type": "public_url",
                        "receipt_value": "http://example.com/post/1",
                        "recorded_at": "2026-04-10T10:00:00Z",
                        "validated": True,
                    }
                ],
            }
            (state_dir / "outreach_receipts.json").write_text(json.dumps(receipts, indent=2) + "\n", encoding="utf-8")
            (state_dir / "verification_events.jsonl").write_text(
                json.dumps(
                    {
                        "schema_version": "clawwars/vnext/verification_event@1",
                        "event_id": "evt1",
                        "event_type": "core_action_completed",
                        "anonymous_user_id": "anon_1",
                        "occurred_at": "2026-04-10T10:05:00Z",
                        "source": "collector_sync",
                        "metadata": {},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            analytics = {
                "schema_version": "clawwars/vnext/analytics_summary@1",
                "verified_user_count": 1,
                "event_count": 1,
                "last_event_at": "2026-04-10T10:05:00Z",
                "sources": {"collector_sync": 1},
            }
            (state_dir / "analytics_summary.json").write_text(json.dumps(analytics, indent=2) + "\n", encoding="utf-8")

            result = self.run_tool("--state-dir", str(state_dir), "update-gates")

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            gates = json.loads((state_dir / "gates.json").read_text(encoding="utf-8"))["gates"]
            deployment_after = json.loads((state_dir / "deployment.json").read_text(encoding="utf-8"))
            self.assertEqual(gates["G2"]["status"], "pass")
            self.assertEqual(gates["G3"]["status"], "pass")
            self.assertEqual(gates["G4"]["status"], "pass")
            self.assertTrue(deployment_after["product_lane"]["url_verified"])

    def test_update_gates_blocks_g2_when_public_url_check_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            state_dir = self.make_state_dir(temp_dir)
            deployment = json.loads((state_dir / "deployment.json").read_text(encoding="utf-8"))
            deployment["product_lane"]["public_url"] = "http://127.0.0.1:9/not-running"
            (state_dir / "deployment.json").write_text(json.dumps(deployment, indent=2) + "\n", encoding="utf-8")

            result = self.run_tool("--state-dir", str(state_dir), "update-gates")

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            gates = json.loads((state_dir / "gates.json").read_text(encoding="utf-8"))["gates"]
            deployment_after = json.loads((state_dir / "deployment.json").read_text(encoding="utf-8"))
            self.assertEqual(gates["G2"]["status"], "pending")
            self.assertFalse(deployment_after["product_lane"]["url_verified"])

    def test_enforce_deadlines_blocks_run_after_missed_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            state_dir = self.make_state_dir(temp_dir)
            gates = json.loads((state_dir / "gates.json").read_text(encoding="utf-8"))
            gates["gates"]["G1"]["status"] = "pass"
            (state_dir / "gates.json").write_text(json.dumps(gates, indent=2) + "\n", encoding="utf-8")

            result = self.run_tool("--state-dir", str(state_dir), "enforce-deadlines", "--next-heartbeat", "7")

            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            run = json.loads((state_dir / "run.json").read_text(encoding="utf-8"))
            self.assertFalse(payload["allowed"])
            self.assertEqual(payload["blocked_gate"], "G2")
            self.assertEqual(run["status"], "blocked")
            self.assertEqual(run["classification"], "deployment_failure")


if __name__ == "__main__":
    unittest.main()
