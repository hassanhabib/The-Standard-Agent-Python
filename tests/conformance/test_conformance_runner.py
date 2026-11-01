# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The conformance runner, run the way a host runs it: over the real vectors, one profile at a time.

The vectors are the specification's executable half and live with the reference implementation
(hassanhabib/The-Standard-Agent, conformance/vectors). STANDARD_AGENTS_VECTORS points at them;
without it, the sibling checkout ../The-Standard-Agent is used. A machine with neither has no
evidence to certify against, so these tests skip and say why rather than pass vacuously.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

_VECTORS_PATH = Path(os.environ.get(
    "STANDARD_AGENTS_VECTORS",
    _REPOSITORY_ROOT.parent / "The-Standard-Agent" / "conformance" / "vectors"))


def _certify(profile_name: str) -> subprocess.CompletedProcess:
    # The same import roots pytest is given (pyproject.toml), so the runner drives this checkout
    # whether or not the package is installed.
    import_roots = [str(_REPOSITORY_ROOT / "src"), str(_REPOSITORY_ROOT)]

    environment = dict(
        os.environ,
        PYTHONIOENCODING="utf-8",
        PYTHONPATH=os.pathsep.join(import_roots + [os.environ.get("PYTHONPATH", "")]))

    return subprocess.run(
        [sys.executable, "-m", "conformance", str(_VECTORS_PATH), "--profile", profile_name],
        cwd=_REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600)


@pytest.mark.skipif(
    not _VECTORS_PATH.is_dir(),
    reason=(
        f"no conformance vectors at {_VECTORS_PATH}: set STANDARD_AGENTS_VECTORS to the "
        + "reference repository's conformance/vectors folder"))
@pytest.mark.parametrize("profile_name", ["Core", "Reliable", "Enterprise", "Critical"])
def test_should_certify_the_profile(profile_name):
    # given
    expected_certification = f"CERTIFIED  {profile_name}"

    # when
    certification = _certify(profile_name)

    # then
    report = certification.stdout + certification.stderr
    assert certification.returncode == 0, report
    assert expected_certification in certification.stdout.splitlines(), report
