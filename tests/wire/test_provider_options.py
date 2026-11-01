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


def test_should_pass_engine_keys_through_whole():
    # given: what the core cannot model and should not try to
    provider_options_json = """
        {
            "grammar": "root ::= object",
            "thinking": {"type": "enabled", "budget_tokens": 1024}
        }
        """

    # when
    sanitized = ProviderOptions.sanitize(provider_options_json)

    # then
    assert sanitized.stripped_keys == ()

    survived = json.loads(sanitized.json)
    assert survived["grammar"] == "root ::= object"
    assert survived["thinking"]["budget_tokens"] == 1024


def test_should_treat_a_malformed_bag_as_nothing_and_say_it_was_malformed():
    # when
    sanitized = ProviderOptions.sanitize("not json at all")

    # then: nothing reaches the wire, and the boundary can say why
    assert sanitized.json is None
    assert sanitized.malformed is True


def test_should_treat_an_absent_bag_as_nothing_quietly():
    # when
    sanitized = ProviderOptions.sanitize(None)

    # then
    assert sanitized.json is None
    assert sanitized.stripped_keys == ()
    assert sanitized.malformed is False


def test_should_merge_sanitized_keys_onto_the_request_whole():
    # given: the request the broker built, and a sanitized bag
    request = {
        "model": "test",
        "temperature": 0.7,
    }

    sanitized_json = '{"chat_template_kwargs": {"enable_thinking": false}}'

    # when
    ProviderOptions.merge_into(request, sanitized_json)

    # then: the engine key landed and the core's keys stand untouched
    assert request["chat_template_kwargs"]["enable_thinking"] is False
    assert request["temperature"] == 0.7
    assert request["model"] == "test"
