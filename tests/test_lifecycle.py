#!/usr/bin/env python3
"""Execute the production hub lifecycle methods with simulated client/mDNS APIs."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def method(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


class LifecycleTest(unittest.TestCase):
    def test_independent_clients(self):
        source = (ROOT / "sendspin_mc/sendspin_mc_hub.cpp").read_text()
        methods = "\n".join(
            method(source, f"void SendspinMcHub::{name}")
            for name in ("loop()", "set_enabled(bool enabled)", "update_mdns_service_()")
        )
        harness = (ROOT / "tests/lifecycle_harness.cpp").read_text()
        compiler = shutil.which("c++")
        self.assertIsNotNone(compiler, "A host C++ compiler is required")
        with tempfile.TemporaryDirectory(prefix="sendspin-mc-lifecycle-") as tmp:
            cpp = Path(tmp) / "lifecycle.cpp"
            binary = Path(tmp) / "lifecycle"
            cpp.write_text(harness.replace("// PRODUCTION_METHODS", methods))
            subprocess.run([compiler, "-std=c++20", str(cpp), "-o", str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    unittest.main()
