# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The core-owned-keys rule (docs/per-request-inference.md 4.4). provider_options_json is
# inference-shaping only, and that bound is only real if the merge enforces it. The wire carries
# `tools` and `messages`; a naive merge of a passthrough containing either would widen the
# perimeter at the wire level, which is precisely what section 3 promises cannot happen.

import json

from standard_agents.models.brokers.generators.provider_options import ProviderOptions


def test_should_strip_every_core_owned_key_and_report_each_one():
    # given: a passthrough trying to touch what the core writes
    provider_options_json = """
        {
            "temperature": 2.0,
            "tools": [{"type": "function"}],
            "messages": [],
            "response_format": {"type": "json_object"},
            "max_tokens": 999999,
            "chat_template_kwargs": {"enable_thinking": false}
        }
        """

    # when
    sanitized = ProviderOptions.sanitize(provider_options_json)

    # then: the modeled fields win, and the collisions are named so a trace can say so
    assert sanitized.malformed is False

    assert sorted(sanitized.stripped_keys) == sorted(
        ["temperature", "tools", "messages", "response_format", "max_tokens"])

    survived = json.loads(sanitized.json)
    assert len(survived) == 1
    assert "chat_template_kwargs" in survived
