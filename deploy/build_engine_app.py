"""Assemble the self-contained Agent Engine deployment folder (chunk 12).

Why this exists: `adk deploy agent_engine` stages ONLY the folder you point
it at (source_packages = [that folder] — set unconditionally, no extra-
packages mechanism in this CLI generation). Our agent imports two top-level
repo packages (`agent.race_engineer.*`, `shared.*`) that would not exist on
the engine. So we build `build/engine_app/`:

    engine_app/
      __init__.py
      agent.py            <- sys.path bootstrap + re-exports root_agent
                             (the CLI's generated app does `from .agent
                             import root_agent`, so this name is required)
      race_engineer/      <- vendored copy of agent/race_engineer/, with
                             imports rewritten agent.race_engineer -> race_engineer
                             (renamed to avoid colliding with agent.py above)
      shared/             <- vendored verbatim (no clash, no rewrite)
      requirements.txt    <- engine runtime deps (CLI appends its own too)
      .env                <- engine env: Vertex mode, model location, TOOLBOX_URL

Run from the repo root:  python3 deploy/build_engine_app.py
Idempotent: wipes and rebuilds build/engine_app each time.
"""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
BUILD = REPO / "build" / "engine_app"
TOOLBOX_URL = os.environ.get("TOOLBOX_URL", "")

AGENT_PY = '''"""Agent Engine entrypoint shim.

The deploy CLI generates an app file that does `from .agent import
root_agent`, so this module must exist under this exact name. It bootstraps
sys.path so the vendored `race_engineer` and `shared` packages resolve as
top-level absolute imports, then re-exports the agent.
"""
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from race_engineer.agent import root_agent  # noqa: E402,F401
'''

REQUIREMENTS = """google-adk[toolbox]>=1.0,<2
toolbox-core==1.1.0
google-cloud-firestore>=2.16
pydantic>=2.7
"""

ENV = f"""GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_LOCATION=global
TOOLBOX_URL={TOOLBOX_URL}
"""


def vendor(src: pathlib.Path, dst: pathlib.Path, rewrite: bool) -> int:
    shutil.copytree(
        src, dst,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".env"),
    )
    rewritten = 0
    if rewrite:
        for py in dst.rglob("*.py"):
            text = py.read_text()
            new = re.sub(r"\bagent\.race_engineer\b", "race_engineer", text)
            if new != text:
                py.write_text(new)
                rewritten += 1
    return rewritten


def main() -> None:
    if not TOOLBOX_URL:
        sys.exit("TOOLBOX_URL is not set — run `source activate.sh` first "
                 "so the engine knows where MCP Toolbox lives.")

    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)

    n = vendor(REPO / "agent" / "race_engineer", BUILD / "race_engineer", rewrite=True)
    vendor(REPO / "shared", BUILD / "shared", rewrite=False)

    (BUILD / "__init__.py").write_text("")
    (BUILD / "agent.py").write_text(AGENT_PY)
    (BUILD / "requirements.txt").write_text(REQUIREMENTS)
    (BUILD / ".env").write_text(ENV)

    # Self-check: the staged tree must not reference the old package path,
    # and must import cleanly with the staging dir on sys.path.
    stale = [str(p) for p in BUILD.rglob("*.py")
             if "agent.race_engineer" in p.read_text()]
    assert not stale, f"unrewritten imports remain: {stale}"
    sys.path.insert(0, str(BUILD))
    import importlib
    mod = importlib.import_module("race_engineer.prompts")  # no GCP deps at import
    assert hasattr(mod, "build_event_reaction_prompt")
    print(f"Staged {BUILD}")
    print(f"  race_engineer/: {n} files had imports rewritten")
    print(f"  TOOLBOX_URL baked into .env: {TOOLBOX_URL}")
    print("Import self-check passed (race_engineer.prompts loads from the staged tree).")


if __name__ == "__main__":
    main()
