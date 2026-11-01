# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""How a vector or profile document becomes its model: the reference runner's reading, exactly.

Property names match case-insensitively (camelCase in the document, snake_case here), a property
the document leaves out keeps the model's default, or None where the model has none, and a model
that declares REJECTS_UNKNOWN_PROPERTIES refuses a property it does not know. A typo'd field must
fail loudly, not silently delete the assertion or the input it carried: a vector that asserts less
than it appears to reads as coverage (SPEC.md 1.1).

Read the document with json.loads(text, parse_float=Decimal), so a cost survives exactly; a float
field takes the number as a float.
"""

from __future__ import annotations

import dataclasses
import types
import typing
from decimal import Decimal
from typing import Any, TypeVar, Union

Model = TypeVar("Model")


def bind(model_type: type[Model], value: Any) -> Model:
    """The document value as the model it describes."""
    return _bind_value(model_type, value, model_type.__name__)


def _bind_value(value_type: Any, value: Any, path: str) -> Any:
    origin = typing.get_origin(value_type)

    if origin in (Union, types.UnionType):
        if value is None:
            return None

        (inner_type,) = [
            argument for argument in typing.get_args(value_type) if argument is not type(None)]

        return _bind_value(inner_type, value, path)

    if value is None:
        return None

    if origin is list:
        (item_type,) = typing.get_args(value_type)
        _require(isinstance(value, list), path, "an array")

        return [
            _bind_value(item_type, item, f"{path}[{index}]") for index, item in enumerate(value)]

    if origin is dict:
        _, item_type = typing.get_args(value_type)
        _require(isinstance(value, dict), path, "an object")

        return {
            key: _bind_value(item_type, item, f"{path}.{key}") for key, item in value.items()}

    if dataclasses.is_dataclass(value_type):
        return _bind_model(value_type, value, path)

    return _bind_primitive(value_type, value, path)


def _bind_model(model_type: type, value: Any, path: str) -> Any:
    _require(isinstance(value, dict), path, "an object")

    model_fields = {
        model_field.name.replace("_", "").lower(): model_field
        for model_field in dataclasses.fields(model_type)}

    field_types = typing.get_type_hints(model_type)
    arguments: dict[str, Any] = {}

    for property_name, property_value in value.items():
        model_field = model_fields.get(property_name.lower())

        if model_field is None:
            if getattr(model_type, "REJECTS_UNKNOWN_PROPERTIES", False):
                raise ValueError(
                    f"The JSON property '{property_name}' could not be mapped to any field of "
                    + f"'{model_type.__name__}' ({path}).")

            continue

        arguments[model_field.name] = _bind_value(
            field_types[model_field.name], property_value, f"{path}.{property_name}")

    for model_field in dataclasses.fields(model_type):
        has_default = (
            model_field.default is not dataclasses.MISSING
            or model_field.default_factory is not dataclasses.MISSING)

        if model_field.name not in arguments and not has_default:
            arguments[model_field.name] = None

    return model_type(**arguments)


def _bind_primitive(value_type: Any, value: Any, path: str) -> Any:
    if value_type is str:
        _require(isinstance(value, str), path, "a string")

        return value

    if value_type is bool:
        _require(isinstance(value, bool), path, "true or false")

        return value

    if value_type is int:
        _require(isinstance(value, int) and not isinstance(value, bool), path, "an integer")

        return value

    if value_type is float:
        _require(_is_number(value), path, "a number")

        return float(value)

    if value_type is Decimal:
        _require(_is_number(value), path, "a number")

        return Decimal(value)

    raise TypeError(f"No binding for {value_type} ({path}).")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


def _require(condition: bool, path: str, expected: str) -> None:
    if not condition:
        raise ValueError(f"The JSON value at {path} could not be converted: expected {expected}.")
