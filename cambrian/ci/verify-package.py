#!/usr/bin/env python3
"""Exercise the shipped native browser, including SOCKS when present in source."""
import os
from pathlib import Path
import subprocess
import sys

bundle = Path(sys.argv[1])
fixture = Path("cambrian/tests/host_overrides_browser.py")
cases = [(f"direct-{process}", ["--socket-process", process]) for process in ("on", "off")]
if Path("cambrian/tests/socks_proxy.py").exists():
    for process in ("on", "off"):
        for version in ("4", "5"):
            for remote in (False, True):
                args = ["--socket-process", process, "--socks-version", version]
                if remote:
                    args += ["--socks-remote-dns"]
                cases.append((f"socks{version}-{'remote' if remote else 'local'}-{process}", args))
    for name, extra in (("ipv6", ["--socks-proxy-host", "::1"]), ("pac", ["--socks-pac"])):
        cases.append((name, ["--socket-process", "on", "--socks-version", "5", "--socks-remote-dns"] + extra))
for name, args in cases:
    subprocess.run([sys.executable, str(fixture), "--firefox", str(bundle / "app/firefox"),
                    "--report", f"/build/artifacts/{name}.json"] + args, check=True)
page = Path("/build/artifacts/package-check.html")
page.write_text("<!doctype html><title>Cambrian Firefox package</title><h1>Portable package works</h1>")
subprocess.run([str(bundle / "firefox"), "--headless", "--screenshot",
                "/build/artifacts/package.png", page.as_uri()], check=True,
               timeout=120, env={**os.environ, "XDG_STATE_HOME": "/build/launcher-state"})
