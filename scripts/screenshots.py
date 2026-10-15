"""Capture the evidence screenshots used in the README with a headless browser.

    python scripts/screenshots.py app --base http://localhost:3000 --out docs/screenshots --prefix compose
    python scripts/screenshots.py url --url http://localhost:8000/docs --out docs/screenshots/swagger.png
    python scripts/screenshots.py terminal --command "pytest -v" --input pytest.txt --out out.png

`terminal` renders the captured output of a real command (ANSI colours
included) as a terminal window, for rubric items that ask for terminal
screenshots.

Requires: pip install playwright && playwright install chromium
"""

import argparse
import html
import re
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

DESKTOP = {"width": 1440, "height": 900}
MOBILE = {"width": 390, "height": 844}


def settle(page: Page, wait_for: str | None = None) -> None:
    page.wait_for_load_state("networkidle")
    if wait_for:
        page.wait_for_selector(wait_for, timeout=30_000)
    page.wait_for_timeout(400)  # let CSS transitions finish


def capture_app(base: str, out: Path, prefix: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for scheme in ("light", "dark"):
            page = browser.new_page(viewport=DESKTOP, color_scheme=scheme, device_scale_factor=1)
            page.on("console", lambda m: m.type == "error" and errors.append(m.text))
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{base}/#/dashboard")
            settle(page, ".timeline-item")
            page.screenshot(path=out / f"{prefix}-dashboard-{scheme}.png", full_page=True)
            if scheme == "dark":
                page.close()
                continue
            for view, selector in (
                ("appointments", ".data-table tbody tr"),
                ("patients", ".data-table tbody tr"),
                ("doctors", ".doctor-card"),
            ):
                page.goto(f"{base}/#/{view}")
                settle(page, selector)
                page.screenshot(path=out / f"{prefix}-{view}.png")
            page.goto(f"{base}/#/appointments")
            settle(page, ".data-table tbody tr")
            page.get_by_role("button", name="+ Book appointment").click()
            page.wait_for_selector("dialog[open] form")
            page.wait_for_timeout(300)
            page.screenshot(path=out / f"{prefix}-booking-form.png")
            page.close()

        mobile = browser.new_page(viewport=MOBILE, device_scale_factor=2, is_mobile=True)
        mobile.goto(f"{base}/#/dashboard")
        settle(mobile, ".timeline-item")
        mobile.screenshot(path=out / f"{prefix}-mobile.png")
        browser.close()

    if errors:
        raise SystemExit("browser console errors:\n" + "\n".join(errors))
    print(f"saved app screenshots to {out}")


def capture_url(
    url: str, out: Path, full_page: bool, wait_for: str | None, width: int, height: int
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(url)
        settle(page, wait_for)
        page.screenshot(path=out, full_page=full_page)
        browser.close()
    print(f"saved {out}")


# ---------------------------------------------------------------- terminal rendering

ANSI = re.compile(r"\x1b\[([0-9;]*)m")
PALETTE = {
    30: "#4d4d4d", 31: "#f2777a", 32: "#7fcf7a", 33: "#f2c45a",
    34: "#6aa8f7", 35: "#d79ee8", 36: "#6dd3d3", 37: "#e6e6e6",
    90: "#8a8a8a", 91: "#ff8f8f", 92: "#9ff09a", 93: "#ffe08a",
    94: "#8fc2ff", 95: "#ecb8f7", 96: "#93ecec", 97: "#ffffff",
}  # fmt: skip


def ansi_to_html(text: str) -> str:
    parts, color, bold, pos = [], None, False, 0
    text = re.sub(r"\x1b\[[0-9;]*[A-HJKSTf]", "", text)  # drop cursor movement codes

    def emit(chunk: str) -> None:
        if not chunk:
            return
        style = []
        if color:
            style.append(f"color:{color}")
        if bold:
            style.append("font-weight:700")
        escaped = html.escape(chunk)
        parts.append(f'<span style="{";".join(style)}">{escaped}</span>' if style else escaped)

    for match in ANSI.finditer(text):
        emit(text[pos : match.start()])
        pos = match.end()
        for code in [int(c) for c in (match.group(1) or "0").split(";") if c.isdigit()] or [0]:
            if code == 0:
                color, bold = None, False
            elif code == 1:
                bold = True
            elif code == 22:
                bold = False
            elif code == 39:
                color = None
            elif code in PALETTE:
                color = PALETTE[code]
    emit(text[pos:])
    return "".join(parts)


TERMINAL_PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
body {{ margin:0; padding:24px; background:#d9dde3; font-family:system-ui,sans-serif; }}
.window {{ width:{width}px; border-radius:10px; overflow:hidden;
  box-shadow:0 12px 32px rgba(0,0,0,.25); background:#0f1117; }}
.bar {{ display:flex; align-items:center; gap:8px; padding:10px 14px; background:#262a33;
  color:#aeb4bf; font-size:13px; }}
.dot {{ width:12px; height:12px; border-radius:50%; }}
.title {{ margin-left:10px; }}
pre {{ margin:0; padding:16px 18px 20px; color:#e6e6e6; font:13px/1.45 "Cascadia Mono",
  Consolas, ui-monospace, monospace; white-space:pre-wrap; word-break:break-word; }}
.prompt {{ color:#7fcf7a; }}
</style></head><body><div class="window">
<div class="bar"><span class="dot" style="background:#ff5f57"></span>
<span class="dot" style="background:#febc2e"></span><span class="dot" style="background:#28c840"></span>
<span class="title">{title}</span></div>
<pre><span class="prompt">{prompt}</span> {command}
{output}</pre></div></body></html>"""


def capture_terminal(
    command: str, source: Path, out: Path, title: str, prompt: str, width: int
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    page_html = TERMINAL_PAGE.format(
        width=width,
        title=html.escape(title),
        prompt=html.escape(prompt),
        command=html.escape(command),
        output=ansi_to_html(text.rstrip()),
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width + 48, "height": 400})
        page.set_content(page_html)
        page.locator(".window").screenshot(path=out)
        browser.close()
    print(f"saved {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="mode", required=True)

    app = sub.add_parser("app", help="screenshot every page of the ClinicCare UI")
    app.add_argument("--base", default="http://localhost:3000")
    app.add_argument("--out", type=Path, default=Path("docs/screenshots"))
    app.add_argument("--prefix", default="app")

    url = sub.add_parser("url", help="screenshot a single web page")
    url.add_argument("--url", required=True)
    url.add_argument("--out", type=Path, required=True)
    url.add_argument("--full-page", action="store_true")
    url.add_argument("--wait-for", help="CSS selector to wait for before capturing")
    url.add_argument("--width", type=int, default=1440)
    url.add_argument("--height", type=int, default=900)

    term = sub.add_parser("terminal", help="render captured command output as a terminal")
    term.add_argument("--command", required=True, help="the command that produced the output")
    term.add_argument("--input", type=Path, required=True, help="file with the captured output")
    term.add_argument("--out", type=Path, required=True)
    term.add_argument("--title", default="Terminal")
    term.add_argument("--prompt", default="$")
    term.add_argument("--width", type=int, default=1100)

    args = parser.parse_args()
    if args.mode == "app":
        capture_app(args.base.rstrip("/"), args.out, args.prefix)
    elif args.mode == "url":
        capture_url(args.url, args.out, args.full_page, args.wait_for, args.width, args.height)
    else:
        capture_terminal(args.command, args.input, args.out, args.title, args.prompt, args.width)


if __name__ == "__main__":
    main()
