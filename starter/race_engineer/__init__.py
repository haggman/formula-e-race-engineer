"""Exposes root_agent for `adk web` discovery — best-effort.

# GIVEN — infrastructure, don't edit. Same guard as the reference: the
# eager import below is ONLY for `adk web`, which discovers agents by
# importing the package. Environments without google-adk or TOOLBOX_URL
# (e.g. the slim engine-mode frontend container) must not crash on package
# import, so we import the agent module only when both are present.
"""
import importlib.util
import os

if importlib.util.find_spec("google.adk") is not None and os.environ.get("TOOLBOX_URL"):
    from starter.race_engineer import agent  # noqa: F401 — exposes root_agent for adk web
