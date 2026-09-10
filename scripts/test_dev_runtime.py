"""Read-only startup checks with isolated listener fixtures; no real services killed."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HELPER = Path(__file__).with_name("dev-runtime.sh")


class RuntimeTests(unittest.TestCase):
    def run_shell(self, body, listing=""):
        with tempfile.TemporaryDirectory(prefix="speccify-runtime-test-") as directory:
            binary = Path(directory) / "lsof"
            binary.write_text('#!/bin/sh\n[ -n "$LISTING" ] || exit 1\nprintf "%s\\n" "$LISTING"\n')
            binary.chmod(0o755)
            return subprocess.run(
                ["bash", "-c", 'source "$HELPER"; ' + body],
                env={
                    **os.environ,
                    "HELPER": str(HELPER),
                    "LISTING": listing,
                    "PATH": directory + os.pathsep + os.environ["PATH"],
                },
                capture_output=True,
                text=True,
                check=False,
            )

    def test_foreign_listener_is_not_called_speccify(self):
        result = self.run_shell(
            "desktop_require_free_port 8768", "limactl 52270 TCP 127.0.0.1:8768 (LISTEN)"
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("limactl 52270", result.stderr)
        self.assertIn("beweist keine", result.stderr)
        self.assertNotIn("pkill", result.stderr)

    def test_free_port_succeeds(self):
        self.assertEqual(self.run_shell("desktop_require_free_port 18768").returncode, 0)

    def test_script_rejects_conflict_before_preparation(self):
        result = self.run_shell(
            'bash "${HELPER%/*}/dev.sh" --ui-port=8768',
            "limactl 52270 TCP 127.0.0.1:8768 (LISTEN)",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("limactl", result.stderr)
        self.assertNotIn("Werkzeuge prüfen", result.stdout)

    def test_script_status_never_prepares(self):
        result = self.run_shell('bash "${HELPER%/*}/dev.sh" --status --ui-port=18768')
        self.assertEqual(result.returncode, 0)
        self.assertIn("18768", result.stdout)
        self.assertNotIn("Werkzeuge prüfen", result.stdout)

    def test_invalid_ports_fail(self):
        for value in ["0", "65536", "-1", "abc", "123456789123456789", ""]:
            with self.subTest(value=value):
                self.assertNotEqual(
                    self.run_shell(f'desktop_validate_port "{value}"').returncode, 0
                )

    def test_valid_ports_include_leading_zeroes(self):
        for value in ["1", "18768", "65535", "08768"]:
            with self.subTest(value=value):
                self.assertEqual(self.run_shell(f'desktop_validate_port "{value}"').returncode, 0)

    def test_status_reports_unknown_listener_and_missing_app(self):
        result = self.run_shell(
            "desktop_status 18768 /nonexistent/speccify-test.app", "other 12 TCP LISTEN"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("http://127.0.0.1:18768", result.stdout)
        self.assertIn("other 12", result.stdout)
        self.assertIn("Noch kein lokaler App-Build", result.stdout)


if __name__ == "__main__":
    unittest.main()
