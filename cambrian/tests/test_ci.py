#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("manifest", Path(__file__).resolve().parents[1] / "ci/toolchain-manifest.py")
manifest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manifest)


class BuilderCompatibility(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in manifest.INPUTS:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(name)

    def test_browser_change_reuses_toolchains(self):
        before = manifest.fingerprint(self.root)
        (self.root / "browser.cpp").write_text("changed browser")
        self.assertEqual(before, manifest.fingerprint(self.root))

    def test_bootstrap_changes_require_a_new_image(self):
        before = manifest.fingerprint(self.root)
        (self.root / "python/mozboot").write_text("new Rust version")
        self.assertNotEqual(before, manifest.fingerprint(self.root))

    def test_missing_input_fails_closed(self):
        (self.root / "moz.configure").unlink()
        with self.assertRaises(ValueError):
            manifest.fingerprint(self.root)

    def test_generated_bytecode_does_not_expire_image(self):
        target = self.root / "python/mozboot"
        target.unlink()
        target.mkdir()
        (target / "bootstrap.py").write_text("bootstrap")
        before = manifest.fingerprint(self.root)
        (target / "__pycache__").mkdir()
        (target / "__pycache__/bootstrap.pyc").write_bytes(b"generated")
        self.assertEqual(before, manifest.fingerprint(self.root))


if __name__ == "__main__":
    unittest.main()
