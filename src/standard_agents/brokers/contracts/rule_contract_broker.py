# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import json
import unicodedata
from typing import Any

from standard_agents.brokers.contracts.icontract_broker import IContractBroker

# JsonDocumentOptions.MaxDepth's default, which JsonDocument.Parse enforces.
_MAX_DEPTH = 64


# The Local mode: a validator in the box, so an answer can be held to a shape without the core
# taking a dependency.
#
# It covers the subset a model actually gets wrong: is it JSON at all, is it the right kind of
# thing, are the required members present, and are their types right. It does NOT implement JSON
# Schema: no $ref, no allOf/anyOf/oneOf, no pattern, no numeric bounds, no nested validation past
# the first level.
#
# That boundary is stated rather than discovered, because a partial validator claiming
# completeness is worse than no validator: it would report an answer as conforming to a schema it
# was never checked against. A host that needs the whole specification supplies a real library
# through use_contract.
class RuleContractBroker(IContractBroker):
    async def validate(self, answer: str, schema: str) -> str | None:
        if _is_null_or_white_space(schema):
            return None

        try:
            schema_root = _parse_document(schema)
        except (ValueError, RecursionError):
            # The schema is the host's, not the model's. A broken one is a configuration error
            # and must not be reported as the model's failure, or every revision chases a fault
            # the model cannot fix.
            raise ValueError(
                "The contract schema is not valid JSON. (Parameter 'schema')") from None

        try:
            answer_root = _parse_document(answer)
        except (ValueError, RecursionError):
            return "the answer is not valid JSON; reply with JSON only and no surrounding prose"

        return _check(answer_root, schema_root)


def _check(answer: Any, schema: Any) -> str | None:
    found, expected_type = _try_get_property(schema, "type")

    if (found
            and _kind_of(expected_type) == "String"
            and _matches(_kind_of(answer), expected_type) is False):
        return (f"expected {expected_type} but the answer was "
            + f"{_describe(_kind_of(answer))}")

    if _kind_of(answer) != "Object":
        return None

    found, required = _try_get_property(schema, "required")

    if found and _kind_of(required) == "Array":
        for member in required:
            name = _get_string(member)

            if (_is_null_or_empty(name) is False
                    and _try_get_property(answer, name)[0] is False):
                return f"the required member '{name}' is missing"

    found, properties = _try_get_property(schema, "properties")

    if found and _kind_of(properties) == "Object":
        for property_name, property_value in properties.pairs:
            has_value, value = _try_get_property(answer, property_name)

            if has_value:
                has_member_type, member_type = _try_get_property(property_value, "type")

                if (has_member_type
                        and _kind_of(member_type) == "String"
                        and _matches(_kind_of(value), member_type) is False):
                    return (f"member '{property_name}' should be {member_type} but was "
                        + f"{_describe(_kind_of(value))}")

    return None


# "integer" is deliberately looser than JSON Schema requires: the parser does not distinguish 1
# from 1.0, and rejecting a whole number because it arrived as a double would send the model
# into a revision it cannot satisfy.
def _matches(kind: str, expected: str | None) -> bool:
    if expected == "object":
        return kind == "Object"

    if expected == "array":
        return kind == "Array"

    if expected == "string":
        return kind == "String"

    if expected in ("number", "integer"):
        return kind == "Number"

    if expected == "boolean":
        return kind in ("True", "False")

    if expected == "null":
        return kind == "Null"

    return True


def _describe(kind: str) -> str:
    if kind == "Object":
        return "an object"

    if kind == "Array":
        return "an array"

    if kind == "String":
        return "a string"

    if kind == "Number":
        return "a number"

    if kind in ("True", "False"):
        return "a boolean"

    if kind == "Null":
        return "null"

    return "nothing"


# A JSON object as JsonDocument keeps it: every member in document order, duplicates included,
# because enumerating an object yields each one.
class _JsonObject:
    def __init__(self, pairs: list[tuple[str, Any]]) -> None:
        self.pairs = pairs


# JsonValueKind, by name.
def _kind_of(element: Any) -> str:
    if isinstance(element, _JsonObject):
        return "Object"

    if isinstance(element, list):
        return "Array"

    if isinstance(element, str):
        return "String"

    if element is True:
        return "True"

    if element is False:
        return "False"

    if element is None:
        return "Null"

    return "Number"


# JsonElement.TryGetProperty: only an object has properties (anything else is an invalid
# operation), names compare ordinally, and of duplicate names the last one wins.
def _try_get_property(element: Any, name: str) -> tuple[bool, Any]:
    if not isinstance(element, _JsonObject):
        raise TypeError(
            "The requested operation requires an element of type 'Object', but the target "
            + f"element has type '{_kind_of(element)}'.")

    for property_name, property_value in reversed(element.pairs):
        if property_name == name:
            return True, property_value

    return False, None


# JsonElement.GetString: a string's value, None for a JSON null, and an invalid operation for
# anything else.
def _get_string(element: Any) -> str | None:
    if element is None or isinstance(element, str):
        return element

    raise TypeError(
        "The requested operation requires an element of type 'String', but the target "
        + f"element has type '{_kind_of(element)}'.")


def _reject_constant(constant: str) -> Any:
    raise ValueError(f"'{constant}' is an invalid JSON literal.")


# JsonDocument.Parse: strict JSON, no NaN or Infinity, nesting no deeper than 64.
def _parse_document(text: str) -> Any:
    root = json.loads(text, object_pairs_hook=_JsonObject, parse_constant=_reject_constant)
    _ensure_depth(root, depth=0)

    return root


def _ensure_depth(element: Any, depth: int) -> None:
    if isinstance(element, (_JsonObject, list)):
        depth += 1

        if depth > _MAX_DEPTH:
            raise ValueError(f"The maximum configured depth of {_MAX_DEPTH} has been exceeded.")

        children = (
            [value for _, value in element.pairs]
            if isinstance(element, _JsonObject)
            else element)

        for child in children:
            _ensure_depth(child, depth)


def _is_null_or_empty(text: str | None) -> bool:
    return text is None or len(text) == 0


# string.IsNullOrWhiteSpace, with char.IsWhiteSpace's own set.
def _is_null_or_white_space(text: str | None) -> bool:
    if text is None:
        return True

    return all(
        character in "\t\n\v\f\r\x85"
        or unicodedata.category(character) in ("Zs", "Zl", "Zp")
        for character in text)
