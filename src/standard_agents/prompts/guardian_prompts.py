# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The built-in guardian prompts, shipped as package data.

The policy is the replaceable part (what to screen or score); a consumption skill can supply its
own. The contract is the output protocol (allow or refuse, the score) the broker parses, so it is
framework-owned and always appended, never replaced.
"""

from importlib.resources import files

_GUARDIANS = "standard_agents.prompts.guardians"


def gate_policy() -> str:
    return _read("gate.policy.md")


def gate_contract() -> str:
    return _read("gate.contract.md")


def judge_policy() -> str:
    return _read("judge.policy.md")


def judge_contract() -> str:
    return _read("judge.contract.md")


def _read(resource_name: str) -> str:
    return files(_GUARDIANS).joinpath(resource_name).read_text(encoding="utf-8")
