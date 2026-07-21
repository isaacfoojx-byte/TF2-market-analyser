from __future__ import annotations
import os
import subprocess
import sys
import tempfile
import time
from importlib import import_module
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


DEBUG_PORT = 9222
DEBUG_URL = f"http://localhost:{DEBUG_PORT}/json/version"
START_URL = "https://backpack.tf/effects"
STARTUP_TIMEOUT_SECONDS = 20


def find_chrome() -> Path:
    candidates = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Google/Chrome/Application/chrome.exe",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(
        "Cannot find Google Chrome in a standard Windows install location."
    )


def debugger_is_ready() -> bool:
    try:
        with urlopen(DEBUG_URL, timeout=1):
            return True
    except (OSError, URLError):
        return False


def launch_chrome() -> None:
    if debugger_is_ready():
        print(f"Using the Chrome instance already running on port {DEBUG_PORT}.")
        return

    chrome = find_chrome()
    profile_dir = Path(tempfile.gettempdir()) / "TF2MarketAnalyserChrome"

    subprocess.Popen(
        [
            str(chrome),
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={profile_dir}",
            START_URL,
        ]
    )

    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if debugger_is_ready():
            return
        time.sleep(0.25)

    raise TimeoutError(
        f"Chrome opened, but its debugging endpoint did not become available "
    )


def main() -> None:
    launch_chrome()
    if __package__:
        import_module(f"{__package__}.scraper")
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import_module("scraper.scraper")


if __name__ == "__main__":
    main()
