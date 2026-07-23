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


DEBUG_PORTS = [9222,9333,9444]
DEBUG_PORT = None
# DEBUG_URL = f"http://localhost:{DEBUG_PORT}/json/version"
# DEBUG_TABS_URL = f"http://localhost:{DEBUG_PORT}/json"
# DEBUG_URL = f"http://[::1]:{DEBUG_PORT}/json/version"
# DEBUG_TABS_URL = f"http://[::1]:{DEBUG_PORT}/json"
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


# def debugger_is_ready() -> bool:
#     try:
#         with urlopen(DEBUG_URL, timeout=1):
#             return True
#     except (OSError, URLError):
#         return False

def debugger_is_ready(port):
    browser = "Unknown"
    try:
        debug_url = f"http://localhost:{port}/json/version"

        with urlopen(debug_url, timeout=1) as response:
            data = json.load(response)

        browser = data.get("Browser", "")

        if browser.startswith("Chrome/"):
            print(f"Found Chrome on port {port}")
            return True

        print(f"Port {port} belongs to {browser}")
        return False
    
    except Exception as e:
        print(f"Port {port} unavailable: {e}")
        return False

def port_is_in_use(port) -> bool:
    try:
        debug_url = f"http://localhost:{port}/json/version"

        with urlopen(debug_url, timeout=1):
            return True

    except Exception:
        return False


def cloudflare_challenge_is_active(port) -> bool:
    try:
        tabs_url = f"http://localhost:{port}/json"
        with urlopen(tabs_url, timeout=2) as response:
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


# def wait_for_cloudflare_clearance(port,
#     timeout_seconds: float = PAGE_SETTLE_SECONDS,
#     poll_interval_seconds: float = CLOUDFLARE_POLL_SECONDS,
# ) -> None:
#     if not cloudflare_challenge_is_active(port):
#         print("No Cloudflare challenge detected, starting scraper.")
#         return

#     print(f"Cloudflare challenge detected; waiting up to {timeout_seconds:g} seconds...")
#     checks = max(1, math.ceil(timeout_seconds / poll_interval_seconds))

#     for i in range(checks):
#         time.sleep(poll_interval_seconds)
#         if not cloudflare_challenge_is_active(port):
#             print("Cloudflare challenge cleared, starting scraper.")
#             return

#     raise RuntimeError(
#         "Cloudflare challenge remained active. Refusing to start an incomplete scrape."
#     )

def wait_for_cloudflare_clearance(
    port,
    timeout_seconds: float = PAGE_SETTLE_SECONDS,
    poll_interval_seconds: float = CLOUDFLARE_POLL_SECONDS,
) -> None:

    print("Waiting for backpack.tf session to become stable...")

    deadline = time.monotonic() + timeout_seconds
    # clear_since = None

    while time.monotonic() < deadline:

        try:
            tabs_url = f"http://localhost:{port}/json"

            with urlopen(tabs_url, timeout=2) as response:
                tabs = json.load(response)

            usable = False
            

            print("------")

            for tab in tabs:

                url = str(tab.get("url", "")).lower()
                title = tab.get("title", "").lower()

                if (
                    "backpack.tf" in url 
                    and "cdn-cgi" not in url
                    and "just a moment" not in title
                ):
                    
                    usable = True
                    break

            if usable:
                print("Session established.")
                return

            # challenge = (
            #     "just a moment" in title
            #     or "attention required" in title
            #     or "cdn-cgi/challenge-platform" in url
            # )

            # if challenge:
            #     clear_since = None

            # else:
            #     if clear_since is None:
            #         clear_since = time.monotonic()

            #     # Require the session to remain clear for 5 seconds
            #     elif time.monotonic() - clear_since >= 5:
            #         print("Cloudflare session established.")
            #         return

            time.sleep(poll_interval_seconds)

        except Exception:
            pass

        

    raise RuntimeError("Cloudflare challenge did not finish.")


def build_chrome_command(chrome: Path, profile_dir: Path, port) -> list[str]:
    # command = [
    #     str(chrome),
    #     f"--remote-debugging-port={DEBUG_PORT}",
    #     f"--user-data-dir={profile_dir}",
    # ]

    command = [
        str(chrome),
        "--remote-debugging-address=127.0.0.1",
        f"--remote-debugging-port={port}",
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

    global DEBUG_PORT

    chrome = find_chrome()

    for port in DEBUG_PORTS:

        if debugger_is_ready(port):
            DEBUG_PORT = port
            print(f"Using Chrome on debugging port {port}.")
            return

        if port_is_in_use(port):
            print(f"Port {port} is already in use by another application, skipping.")
            continue

        if is_github_actions():
            profile_dir = Path(tempfile.mkdtemp(prefix="TF2MarketAnalyserChrome-"))
        else:
            # profile_dir = Path(tempfile.gettempdir()) / "TF2MarketAnalyserChrome"
            profile_dir = Path(tempfile.mkdtemp(prefix="TF2MarketAnalyserChrome-"))

        subprocess.Popen(build_chrome_command(chrome, profile_dir,port))

        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS

        while time.monotonic() < deadline:
            if debugger_is_ready(port):
                DEBUG_PORT = port
                print(f"Using Chrome on debugging port {port}.")
                return
            time.sleep(0.25)

        print(f"Port {port} failed, trying another port...")
    raise RuntimeError("Could not launch Chrome on any debugging port.")

    


def main() -> None:
    start = time.perf_counter()
    launch_chrome()
    wait_for_cloudflare_clearance(DEBUG_PORT)
    print(f"Startup took {time.perf_counter() - start:.1f} seconds")

    if __package__:
        scraper_module = import_module(f"{__package__}.scraper")
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        scraper_module = import_module("scraper.scraper")

    scraper_module.run_scraper(DEBUG_PORT)


if __name__ == "__main__":
    main()
