# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# Found in the 2026-09-04 principal review (F-24): the agent document had no schema an editor
# could read. A hand-written one would drift from the switch that is the truth, so the schema is
# EMITTED from the same table the document is validated against: every key it names composes,
# every key it does not name is refused, and every nested property it lists is one the section
# accepts, because there is only one list.

import json

import pytest

from standard_agents.standard_agent import StandardAgent


def schema() -> dict:
    return json.loads(StandardAgent.document_schema_json())


def test_should_emit_a_closed_schema_for_the_document():
    # when
    document_schema = schema()

    # then: a document is an object with only the keys the builder knows
    assert "json-schema.org" in document_schema["$schema"]
    assert document_schema["type"] == "object"
    assert document_schema["additionalProperties"] is False
    assert len(document_schema["properties"]) > 30


def test_should_compose_every_example_the_schema_carries(tmp_path, monkeypatch):
    # given: each key's example, as the schema shows it to an editor
    monkeypatch.chdir(tmp_path)
    properties = schema()["properties"]

    for key, description in properties.items():
        example = description["examples"][0]
        document = json.dumps({key: example})

        # when . then: an example the builder refuses is a lie in the editor
        try:
            StandardAgent.from_json(document)
        except Exception as exception:
            pytest.fail(f"the schema's example for '{key}' must compose: {exception!r}")
