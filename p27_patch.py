#!/usr/bin/env python3
"""p27_patch.py — P2.7 cascade patch (one shot; run from the REPO ROOT, then delete).

What it does:
  1. frontend/static/index.html
     a. removes the dead surname tooltip (the title attr — the tower rebuilds
        via innerHTML at 1 Hz, so the element never survives the hover delay)
     b. splits the call-meta render so secs and tools display independently
        (Q&A answers carry secs only after edit 2 — without this split the
        Q&A meta line would read "· 12.3s · undefined tools")
  2. frontend/main.py — stamps Q&A answers with wall seconds (_handle_ask)
  3. README.md + setup/all.sh — "~20-30 min" setup claims -> "budget 20,
     ~10 typical" (Finding #8). STUDENT_GUIDE.md is scanned too: it carries
     no 20-30 claim today, so the script confirms that and moves on.
  4. README.md — "14 curated tools" -> "14 tools: 11 curated + discovery +
     SQL" (Test 2 docs-pass finding, folded in: only 11 of the 14 are
     curated; the other 3 are the discovery pair + the SQL escape hatch)
  5. STUDENT_GUIDE.md — fixes the MCP Toolbox docs link (Test 2 docs-pass
     finding: the project was renamed genai-toolbox -> mcp-toolbox and
     https://googleapis.github.io/genai-toolbox/ now returns 404; docs
     live at https://mcp-toolbox.dev/documentation/introduction/ — verified
     2026-06-06)
  6. PACKAGING.md — ticks the three delivered P2.7 checkboxes
     (the optional activate.sh stale-engine warning stays parked/unchecked)

Cumulative + idempotent: every edit skips when already applied; an anchor
that is neither found nor already applied raises AssertionError naming the
file and edit, and nothing after that point is written.
"""
from __future__ import annotations

import sys
from pathlib import Path

if not Path("activate.sh").is_file() or not Path("PACKAGING.md").is_file():
    sys.exit("Run this from the repo root (where activate.sh lives).")


def apply(path: str, label: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if new in text:
        print(f"  ○ {label} — already applied, skipping")
        return
    assert old in text, f"{path}: ANCHOR NOT FOUND for edit: {label}"
    assert text.count(old) == 1, f"{path}: anchor not unique for edit: {label}"
    p.write_text(text.replace(old, new), encoding="utf-8")
    print(f"  ✓ {label} — applied")


print("== p27_patch: index.html ==")
apply(
    "frontend/static/index.html",
    "1a. remove dead surname tooltip",
    '      `<span class="drv" title="${(DRIVERS[c.driver] || {}).full || ""}">${(DRIVERS[c.driver] || {}).last || c.driver || "—"}</span>` +\n',
    '      `<span class="drv">${(DRIVERS[c.driver] || {}).last || c.driver || "—"}</span>` +\n',
)
apply(
    "frontend/static/index.html",
    "1b. meta line: render secs and tools independently",
    '    (msg.secs != null ? ` · ${msg.secs}s · ${msg.tools} tool${msg.tools === 1 ? "" : "s"}` : "") +\n',
    '    (msg.secs != null ? ` · ${msg.secs}s` : "") +\n'
    '    (msg.tools != null ? ` · ${msg.tools} tool${msg.tools === 1 ? "" : "s"}` : "") +\n',
)

print("== p27_patch: frontend/main.py ==")
apply(
    "frontend/main.py",
    "2a. import time",
    "import os\nfrom pathlib import Path\n",
    "import os\nimport time\nfrom pathlib import Path\n",
)
apply(
    "frontend/main.py",
    "2b. wall-secs stamp on Q&A answers",
    '    stamp = {"race_time_s": latest["race_time_s"], "lap": latest["lap"]}\n'
    "    try:\n"
    "        answer = await engineer.ask(question)\n"
    '        await radio_broadcast({"type": "radio", "kind": "qa",\n'
    '                               "text": answer, **stamp})\n',
    '    stamp = {"race_time_s": latest["race_time_s"], "lap": latest["lap"]}\n'
    "    t0 = time.monotonic()\n"
    "    try:\n"
    "        answer = await engineer.ask(question)\n"
    '        await radio_broadcast({"type": "radio", "kind": "qa",\n'
    '                               "text": answer,\n'
    '                               "secs": round(time.monotonic() - t0, 1),\n'
    "                               **stamp})\n",
)

print("== p27_patch: setup-time claims (Finding #8) ==")
apply(
    "README.md",
    "3a. README quick-start time claim",
    "bash setup/all.sh         # deploy the full data plane (~20-30 min) + verify",
    "bash setup/all.sh         # deploy the full data plane (budget 20 min, ~10 typical) + verify",
)
apply(
    "setup/all.sh",
    "3b. all.sh header time claim",
    "# Wall clock: ~20-30 minutes (Firestore index builds decide). Idempotent:\n"
    "# safe to rerun after a failure — completed steps fast-forward.\n",
    "# Wall clock: budget 20 minutes, ~10 typical on a fresh project (Firestore\n"
    "# index builds are the one variable). Idempotent: safe to rerun after a\n"
    "# failure — completed steps fast-forward.\n",
)
sg = Path("STUDENT_GUIDE.md").read_text(encoding="utf-8")
if "20-30" in sg or "20–30" in sg:
    raise AssertionError(
        "STUDENT_GUIDE.md DOES contain a 20-30 claim — unexpected; patch by hand"
    )
print("  ○ 3c. STUDENT_GUIDE.md: no 20-30 setup claim found — nothing to change (expected)")

print("== p27_patch: README tool-count wording (docs-pass finding) ==")
apply(
    "README.md",
    "4. '14 curated tools' -> '14 tools: 11 curated + discovery + SQL'",
    "                              14 curated tools + schema discovery + SQL)",
    "                              14 tools: 11 curated + discovery + SQL)",
)

print("== p27_patch: STUDENT_GUIDE Toolbox docs link (docs-pass finding) ==")
apply(
    "STUDENT_GUIDE.md",
    "5. MCP Toolbox docs link (old URL 404s after project rename)",
    "- MCP Toolbox: https://googleapis.github.io/genai-toolbox/ — our server",
    "- MCP Toolbox: https://mcp-toolbox.dev/documentation/introduction/ — our server",
)

print("== p27_patch: PACKAGING.md — tick the delivered P2.7 boxes ==")
apply(
    "PACKAGING.md",
    "6a. tick index.html tooltip item",
    "- [ ] index.html: REMOVE the surname tooltip (`title` attr)",
    "- [x] index.html: REMOVE the surname tooltip (`title` attr)",
)
apply(
    "PACKAGING.md",
    "6b. tick main.py Q&A stamp item",
    "- [ ] main.py: optional — stamp Q&A answers with wall secs",
    "- [x] main.py: optional — stamp Q&A answers with wall secs",
)
apply(
    "PACKAGING.md",
    "6c. tick + annotate the time-claims item",
    '- [ ] README.md + setup/all.sh header + STUDENT_GUIDE.md: revise the\n'
    '  "~20-30 min" setup claims to "budget 20, ~10 typical" (Finding #8).\n',
    '- [x] README.md + setup/all.sh header + STUDENT_GUIDE.md: revise the\n'
    '  "~20-30 min" setup claims to "budget 20, ~10 typical" (Finding #8).\n'
    "  (Done — README + all.sh patched; STUDENT_GUIDE carried no such claim.)\n",
)

print("\np27_patch complete. Review with: git diff --stat && git diff")
print("Then: rm p27_patch.py  (one-shot — do not leave it in the repo)")
