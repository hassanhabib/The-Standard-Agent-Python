# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""An endpoint written in the documentation is an endpoint someone will paste.

A documented base that already named chat/completions once sent copied examples to
v1/chat/chat/completions (principal review 2026-09-04, F-12). Every documented endpoint is composed
through the real verb: a documented URL the builder refuses is a documentation bug, caught here
rather than by the next reader.
"""

import re
from pathlib import Path

import pytest

from standard_agents import StandardAgent

ROOT = Path(__file__).resolve().parents[3]

DOCUMENTED_FILES = ("README.md", "docs/hosting.md")

# The three shapes an endpoint takes in the docs: a Python argument, a JSON agent document, and
# the host's setting.
DOCUMENTED_API_URL = re.compile(
    r"(?:\bapi_url\s*=\s*|\"apiUrl\"\s*:\s*|\bAgent__Url=|\bAgent:Url=)\"?(?P<url>https?://[^\"\s]+)")


def _documented_api_urls() -> list[tuple[str, str]]:
    return [
        (documented_file, match.group("url"))
        for documented_file in DOCUMENTED_FILES
        if (ROOT / documented_file).exists()
        for match in DOCUMENTED_API_URL.finditer(
            (ROOT / documented_file).read_text(encoding="utf-8"))]


# xUnit fails a theory that finds no data, so a documentation set that teaches no endpoint fails
# here too rather than passing with nothing checked.
@pytest.mark.parametrize(
    ("documented_file", "documented_api_url"),
    _documented_api_urls() or [("<no documented file>", None)])
def test_should_compose_every_documented_api_url(documented_file, documented_api_url):
    # given . when . then
    assert documented_api_url is not None, "No documented API URL was found in " + ", ".join(
        DOCUMENTED_FILES)

    StandardAgent().brain(api_url=documented_api_url, api_key="key", model="model")
