"""Package marker — intentionally bare as shipped.

Your agent doesn't exist yet: Tier A's `adk create starter/race_engineer`
writes agent.py (and replaces this file with `from . import agent`). Until
then, nothing may import `.agent` here — step-0 verification reaches the
given plumbing (config, tools.*) through this package, and it must import
cleanly with no agent present.
"""
