"""Exposes root_agent for `adk web` discovery — best-effort.

The eager import below is ONLY for `adk web`, which discovers agents by
importing the package. The engine-mode frontend container ships this
package too (for prompts/config/snapshot/state_client) but deliberately
WITHOUT google-adk or TOOLBOX_URL — agent.py needs both — so the package
import must not crash there. Guard: import only when both are present.
"""
import importlib.util
import os

if importlib.util.find_spec("google.adk") is not None and os.environ.get("TOOLBOX_URL"):
    from agent.race_engineer import agent  # noqa: F401 — exposes root_agent for adk web