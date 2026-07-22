from __future__ import annotations
import json
import math
import os
import shutil
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
DEBUG_TABS_URL = f"http://localhost:{DEBUG_PORT}/json"
START_URL = "https://backpack.tf/effects"
STARTUP_TIMEOUT_SECONDS = 20
PAGE_SETTLE_SECONDS = 10
CLOUDFLARE_POLL_SECONDS = 1


def is_github_actions() -> bool:
    return os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def find_chrome() -> Path:
    configured_path = os.environ.get("CHROME_PATH")
    if configured_path:
        chrome = Path(configured_path)
        if chrome.is_file():
            return chrome
        raise FileNotFoundError(f"CHROME_PATH does not exist: {chrome}")

    command_path = (
        shutil.which("google-chrome")
        or shutil.which("google-chrome-stable")
        or shutil.which("chrome")
        or shutil.which("chromium")
        or shutil.which("chromium-browser")
    )
    if command_path:
        return Path(command_path)

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
        "Cannot find Google Chrome. Set CHROME_PATH to its executable location."
    )


def debugger_is_ready() -> bool:
    try:
        with urlopen(DEBUG_URL, timeout=1):
            return True
    except (OSError, URLError):
        return False


def cloudflare_challenge_is_active() -> bool:
    try:
        with urlopen(DEBUG_TABS_URL, timeout=2) as response:
            tabs = json.load(response)
    except (OSError, URLError, json.JSONDecodeError):
        return False

    markers = (
        "just a moment",
        "attention required",
        "cdn-cgi/challenge-platform",
    )

    for tab in tabs:
        title = str(tab.get("title", "")).lower()
        url = str(tab.get("url", "")).lower()
        if "backpack.tf" not in url:
            continue
        if any(marker in title or marker in url for marker in markers):
            return True

    return False


def wait_for_cloudflare_clearance(
    timeout_seconds: float = PAGE_SETTLE_SECONDS,
    poll_interval_seconds: float = CLOUDFLARE_POLL_SECONDS,
) -> None:
    if not cloudflare_challenge_is_active():
        print("No Cloudflare challenge detected, starting scraper.")
        return

    print(f"Cloudflare challenge detected; waiting up to {timeout_seconds:g} seconds...")
    checks = max(1, math.ceil(timeout_seconds / poll_interval_seconds))

    for i in range(checks):
        time.sleep(poll_interval_seconds)
        if not cloudflare_challenge_is_active():
            print("Cloudflare challenge cleared, starting scraper.")
            return

    raise RuntimeError(
        "Cloudflare challenge remained active. Refusing to start an incomplete scrape."
    )


def build_chrome_command(chrome: Path, profile_dir: Path) -> list[str]:
    command = [
        str(chrome),
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={profile_dir}",
    ]

    if is_github_actions():
        command.extend(
            [
                "--headless=new",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )

    command.append(START_URL)
    return command


def launch_chrome() -> None:
    if debugger_is_ready():
        print(f"Using the browser instance already running on port {DEBUG_PORT}.")
        return

    chrome = find_chrome()
    if is_github_actions():
        profile_dir = Path(tempfile.mkdtemp(prefix="TF2MarketAnalyserChrome-"))
    else:
        profile_dir = Path(tempfile.gettempdir()) / "TF2MarketAnalyserChrome"

    subprocess.Popen(build_chrome_command(chrome, profile_dir))

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
    wait_for_cloudflare_clearance()

    if __package__:
        scraper_module = import_module(f"{__package__}.scraper")
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        scraper_module = import_module("scraper.scraper")

    scraper_module.run_scraper()


if __name__ == "__main__":
    main()
