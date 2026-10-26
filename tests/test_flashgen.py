"""Script parity tests. POSIX execution uses fake tools, never a real phone.

Run: python3 -m unittest discover -s tests -v
"""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

from lib import devices, flashgen


class FlashScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / "ROM files"
        self.out.mkdir()
        self.parts = ["system", "vendor", "chip_prod", "sys_prod", "cust", "patch"]
        for name in self.parts:
            (self.out / (name + ".img")).write_bytes(bytes(4096))
        flashgen.write(str(self.out), self.parts, "Test build\n", devices.get("davinci"))

    def test_davinci_safety_parity(self):
        for basename in ("install_clean", "update_keep_data"):
            for ext in ("bat", "sh"):
                with self.subTest(script=basename + "." + ext):
                    text = (self.out / (basename + "." + ext)).read_text()
                    self.assertIn("--disable-verity --disable-verification flash vbmeta", text)
                    self.assertNotIn("wipe-super", text)
                    self.assertNotIn("|| set LPW=", text)
                    self.assertNotIn("|| LPW=", text)
                    self.assertNotIn("call :lpwrite", text)
                    switch = text.index("fastboot reboot bootloader")
                    for part in ("dtbo", "boot", "vbmeta"):
                        self.assertGreater(text.index("flash " + part + " "), switch)

    def test_shell_scripts_have_unix_line_endings(self):
        for path in self.out.glob("*.sh"):
            self.assertNotIn(b"\r", path.read_bytes(), path.name)
            self.assertTrue(path.read_bytes().startswith(b"#!/bin/sh\n"))

    def test_update_keeps_data(self):
        for ext in ("bat", "sh"):
            text = (self.out / ("update_keep_data." + ext)).read_text()
            self.assertNotIn("fastboot format", text)
            self.assertNotIn("delete-logical-partition", text)
            self.assertNotIn("create-logical-partition", text)

    def fake_environment(self, fail=""):
        # Only fake fastboot is reachable via the script-local PATH. No real
        # fastboot/adb invocation occurs in these execution tests.
        fake = self.out / "fastboot"
        fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$FASTBOOT_LOG"\n'
                        'if [ "$*" = "$FAIL_COMMAND" ]; then exit 7; fi\n', newline="\n")
        fake.chmod(0o755)
        self.trace = self.root / "commands.log"
        return dict(os.environ, FASTBOOT_LOG=str(self.trace), FAIL_COMMAND=fail)

    def run_script(self, name, answer="YES\n", fail=""):
        return subprocess.run([shutil.which("sh"), str(self.out / (name + ".sh"))],
                              input=answer, text=True, capture_output=True,
                              cwd=self.root, env=self.fake_environment(fail), timeout=30)

    def batch_commands(self, name):
        commands = []
        for line in (self.out / (name + ".bat")).read_text().splitlines():
            if line == "exit /b 0":
                break  # Do not include the unreachable sweet lpwrite subroutine.
            if not line.startswith("fastboot "):
                continue
            command = line.split(" || ", 1)[0].split(" >nul", 1)[0]
            command = command.replace("%OUT%", "$OUT/")
            commands.append(" ".join(shlex.split(command)[1:]))
        return commands

    @unittest.skipUnless(os.name == "posix" and shutil.which("sh"), "requires a POSIX shell")
    def test_shell_execution_matches_batch_command_order(self):
        for name in ("install_clean", "update_keep_data"):
            with self.subTest(script=name):
                if hasattr(self, "trace") and self.trace.exists():
                    self.trace.unlink()
                result = self.run_script(name)
                self.assertEqual(result.returncode, 0, result.stderr)
                actual = self.trace.read_text().replace(str(self.out), "$OUT").splitlines()
                self.assertEqual(actual, self.batch_commands(name))

    @unittest.skipUnless(os.name == "posix" and shutil.which("sh"), "requires a POSIX shell")
    def test_flash_failure_aborts_before_bootloader_and_boot(self):
        failed = "flash vendor " + str(self.out / "vendor.img")
        for name in ("install_clean", "update_keep_data"):
            with self.subTest(script=name):
                if hasattr(self, "trace") and self.trace.exists():
                    self.trace.unlink()
                result = self.run_script(name, fail=failed)
                self.assertNotEqual(result.returncode, 0)
                commands = self.trace.read_text().splitlines()
                self.assertEqual(commands[-1], failed)
                self.assertNotIn("reboot bootloader", commands)

    @unittest.skipUnless(os.name == "posix" and shutil.which("sh"), "requires a POSIX shell")
    def test_declining_clean_install_runs_no_fastboot_commands(self):
        result = self.run_script("install_clean", answer="NO\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.trace.exists())


if __name__ == "__main__":
    unittest.main()
