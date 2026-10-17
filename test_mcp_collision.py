"""Tests for mcp-collision — deterministic; live-server tests use a fake stdio server."""

import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mcp_collision as mc


class TestSanitize(unittest.TestCase):
    def test_raw_passthrough(self):
        self.assertEqual(mc.sanitize("raw", "srv", "tool"), "tool")

    def test_claude_prefix(self):
        self.assertEqual(mc.sanitize("claude", "a", "b"), "a__b")

    def test_cursor_dash(self):
        self.assertEqual(mc.sanitize("cursor", "a", "b"), "a-b")

    def test_claude_sanitizes_dots(self):
        self.assertEqual(mc.sanitize("claude", "my.server", "x"), "my_server__x")

    def test_collapse_collision(self):
        self.assertEqual(mc.sanitize("claude", "my.server", "x"),
                         mc.sanitize("claude", "my_server", "x"))


class TestAnalyze(unittest.TestCase):
    def test_no_collision(self):
        coll, _ = mc.analyze({"a": ["x", "y"], "b": ["z"]}, "claude")
        self.assertEqual(coll, {})

    def test_same_tool_different_servers_ok(self):
        coll, _ = mc.analyze({"a": ["x"], "b": ["x"]}, "claude")
        self.assertEqual(coll, {})  # prefixed names differ

    def test_raw_collision(self):
        coll, _ = mc.analyze({"a": ["x"], "b": ["x"]}, "raw")
        self.assertEqual(coll, {"x": [("a", "x"), ("b", "x")]})

    def test_sanitized_collision(self):
        coll, _ = mc.analyze({"my.server": ["x"], "my_server": ["x"]}, "claude")
        self.assertEqual(coll, {"my_server__x": [("my.server", "x"), ("my_server", "x")]})


class TestLoadConfig(unittest.TestCase):
    def test_jsonc_tolerant(self):
        p = "/tmp/mc_test_jsonc.json"
        with open(p, "w") as f:
            f.write('{ // comment\n "mcpServers": {"a": {"command": "x"}}, /* block */ }\n')
        servers = mc.load_config(p)
        self.assertEqual(list(servers), ["a"])

    def test_trailing_comma(self):
        p = "/tmp/mc_test_tc.json"
        with open(p, "w") as f:
            f.write('{"mcpServers": {"a": {"command": "x"},},}\n')
        self.assertEqual(list(mc.load_config(p)), ["a"])

    def test_alternate_key(self):
        p = "/tmp/mc_test_alt.json"
        with open(p, "w") as f:
            f.write('{"mcp_servers": {"a": {"command": "x"}}}\n')
        self.assertEqual(list(mc.load_config(p)), ["a"])


class TestFakeServer(unittest.TestCase):
    """End-to-end over stdio with a fake MCP server (stdlib only)."""

    def setUp(self):
        self.fake = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_server.py")

    def _list(self, name):
        tools, err = mc.list_tools(["python3", self.fake, name], timeout=10)
        return tools, err

    def test_initialize_and_list(self):
        tools, err = self._list("demo")
        self.assertIsNone(err)
        self.assertEqual([t["name"] for t in tools], ["tool_one", "tool_two"])

    def test_bad_command(self):
        tools, err = mc.list_tools(["/nonexistent/binary/xyz"], timeout=10)
        self.assertIsNone(tools)
        self.assertIn("cannot spawn", err)


class TestCliEndToEnd(unittest.TestCase):
    def setUp(self):
        d = os.path.dirname(os.path.abspath(__file__))
        self.fake = os.path.join(d, "fake_server.py")
        self.cfg = "/tmp/mc_e2e_config.json"
        with open(self.cfg, "w") as f:
            json.dump({"mcpServers": {
                "one": {"command": "python3", "args": [self.fake, "one"]},
                "two": {"command": "python3", "args": [self.fake, "two"]},
            }}, f)

    def _scan(self, *extra):
        return subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(self.fake), "mcp_collision.py") if False else "mcp_collision.py",
             "scan", self.cfg, *extra],
            capture_output=True, text=True, timeout=60,
            cwd=os.path.dirname(os.path.abspath(__file__)))

    def test_scan_no_collision_claude(self):
        r = self._scan("--client", "claude")
        self.assertEqual(r.returncode, 0)
        self.assertIn("no collisions", r.stdout)

    def test_scan_raw_collision(self):
        r = self._scan("--client", "raw")
        self.assertEqual(r.returncode, 2)
        self.assertIn("COLLISION", r.stdout)

    def test_scan_json(self):
        r = self._scan("--client", "raw", "--json")
        data = json.loads(r.stdout)
        self.assertEqual(data["total_tools"], 4)
        self.assertIn("tool_one", data["collisions"])


if __name__ == "__main__":
    unittest.main()
