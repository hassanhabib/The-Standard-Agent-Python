# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import codecs
import json

from restfulsense.exceptions import (
    HttpResponseBadGatewayException,
    HttpResponseBadRequestException,
    HttpResponseConflictException,
    HttpResponseException,
    HttpResponseExpectationFailedException,
    HttpResponseFailedDependencyException,
    HttpResponseForbiddenException,
    HttpResponseGatewayTimeoutException,
    HttpResponseGoneException,
    HttpResponseHttpVersionNotSupportedException,
    HttpResponseInsufficientStorageException,
    HttpResponseInternalServerErrorException,
    HttpResponseLengthRequiredException,
    HttpResponseLockedException,
    HttpResponseLoopDetectedException,
    HttpResponseMethodNotAllowedException,
    HttpResponseMisdirectedRequestException,
    HttpResponseNetworkAuthenticationRequiredException,
    HttpResponseNotAcceptableException,
    HttpResponseNotExtendedException,
    HttpResponseNotFoundException,
    HttpResponseNotImplementedException,
    HttpResponsePaymentRequiredException,
    HttpResponsePreconditionFailedException,
    HttpResponsePreconditionRequiredException,
    HttpResponseProxyAuthenticationRequiredException,
    HttpResponseRequestedRangeNotSatisfiableException,
    HttpResponseRequestEntityTooLargeException,
    HttpResponseRequestHeaderFieldsTooLargeException,
    HttpResponseRequestTimeoutException,
    HttpResponseRequestUriTooLongException,
    HttpResponseServiceUnavailableException,
    HttpResponseTooManyRequestsException,
    HttpResponseUnauthorizedException,
    HttpResponseUnavailableForLegalReasonsException,
    HttpResponseUnprocessableEntityException,
    HttpResponseUnsupportedMediaTypeException,
    HttpResponseUpgradeRequiredException,
    HttpResponseUrlNotFoundException,
    HttpResponseVariantAlsoNegotiatesException)

# The Python stand-in for RESTFulSense.Services.ValidationService (3.2.0): one exception type per
# status it knows, and nothing for a status it does not. The rules below were read off the real
# library by probing it, not from its documentation.

DEFAULT_PROBLEM_TITLE = "One or more validation errors occurred."

_STATUS_EXCEPTIONS: dict[int, type[HttpResponseException]] = {
    400: HttpResponseBadRequestException,
    401: HttpResponseUnauthorizedException,
    402: HttpResponsePaymentRequiredException,
    403: HttpResponseForbiddenException,
    404: HttpResponseNotFoundException,
    405: HttpResponseMethodNotAllowedException,
    406: HttpResponseNotAcceptableException,
    407: HttpResponseProxyAuthenticationRequiredException,
    408: HttpResponseRequestTimeoutException,
    409: HttpResponseConflictException,
    410: HttpResponseGoneException,
    411: HttpResponseLengthRequiredException,
    412: HttpResponsePreconditionFailedException,
    413: HttpResponseRequestEntityTooLargeException,
    414: HttpResponseRequestUriTooLongException,
    415: HttpResponseUnsupportedMediaTypeException,
    416: HttpResponseRequestedRangeNotSatisfiableException,
    417: HttpResponseExpectationFailedException,
    421: HttpResponseMisdirectedRequestException,
    422: HttpResponseUnprocessableEntityException,
    423: HttpResponseLockedException,
    424: HttpResponseFailedDependencyException,
    426: HttpResponseUpgradeRequiredException,
    428: HttpResponsePreconditionRequiredException,
    429: HttpResponseTooManyRequestsException,
    431: HttpResponseRequestHeaderFieldsTooLargeException,
    451: HttpResponseUnavailableForLegalReasonsException,
    500: HttpResponseInternalServerErrorException,
    501: HttpResponseNotImplementedException,
    502: HttpResponseBadGatewayException,
    503: HttpResponseServiceUnavailableException,
    504: HttpResponseGatewayTimeoutException,
    505: HttpResponseHttpVersionNotSupportedException,
    506: HttpResponseVariantAlsoNegotiatesException,
    507: HttpResponseInsufficientStorageException,
    508: HttpResponseLoopDetectedException,
    510: HttpResponseNotExtendedException,
    511: HttpResponseNetworkAuthenticationRequiredException,
}

_BYTE_ORDER_MARKS = (
    (codecs.BOM_UTF8, "utf-8"),
    (codecs.BOM_UTF32_LE, "utf-32-le"),
    (codecs.BOM_UTF32_BE, "utf-32-be"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
)


# HttpContent.ReadAsStringAsync: a byte order mark decides first, then the charset of the
# Content-Type, then UTF-8. Bytes that do not decode become U+FFFD, as .NET's decoders do.
def read_as_string(body: bytes, content_type: str | None) -> str:
    for byte_order_mark, encoding in _BYTE_ORDER_MARKS:
        if body.startswith(byte_order_mark):
            return body[len(byte_order_mark):].decode(encoding, errors="replace")

    encoding = _charset_of(content_type) or "utf-8"

    try:
        codecs.lookup(encoding)
    except LookupError:
        encoding = "utf-8"

    return body.decode(encoding, errors="replace")


# ValidateHttpResponseAsync. content_type is the response's Content-Type header, None when it
# sent none; content is its body as read_as_string reads it.
def validate_http_response(status_code: int, content_type: str | None, content: str) -> None:
    exception_type = _STATUS_EXCEPTIONS.get(status_code)

    if exception_type is None:
        return

    # A 404 whose response declares no content type is an address nothing answers at, whatever
    # the body: RESTFulSense keys this on the missing Content-Type, not on an empty body.
    if status_code == 404 and content_type is None:
        exception_type = HttpResponseUrlNotFoundException

    if _is_problem_detail(content):
        title, errors = _map_to_problem_details(content)
        exception = exception_type(title, status_code, content)

        for key, values in errors.items():
            exception.data[key] = values

        raise exception

    raise exception_type(content, status_code, content)


# RESTFulSense's test is textual: the body mentions both a "type": and a "title": member,
# ignoring case and with no space before the colon. Anywhere in the body, nested included.
def _is_problem_detail(content: str) -> bool:
    lowered = content.lower()

    return '"type":' in lowered and '"title":' in lowered


class _Members(list):
    pass


# Newtonsoft's ValidationProblemDetails read: members match ignoring case, the last title wins,
# every errors object is merged in, a scalar keeps the text of its token, an errors member that
# is not an object or an array is skipped, and a null error list is an empty one.
def _map_to_problem_details(content: str) -> tuple[str, dict[str, list[str | None]]]:
    problem = json.loads(
        content,
        object_pairs_hook=_Members,
        parse_int=str,
        parse_float=str)

    if not isinstance(problem, _Members):
        raise ValueError(
            "Cannot deserialize the current JSON value into type "
            "'Microsoft.AspNetCore.Mvc.ValidationProblemDetails'.")

    title: str | None = DEFAULT_PROBLEM_TITLE
    errors: dict[str, list[str | None]] = {}

    for name, value in problem:
        if name.lower() == "title":
            title = _to_text(value, "title")

        elif name.lower() == "errors":
            if isinstance(value, _Members):
                for key, messages in value:
                    errors[key] = _to_messages(messages, f"errors.{key}")

            elif isinstance(value, list):
                raise ValueError(
                    "Cannot deserialize the current JSON array into type "
                    "'System.Collections.Generic.IDictionary`2[System.String,System.String[]]'.")

    return (DEFAULT_PROBLEM_TITLE if title is None else title), errors


def _to_messages(value: object, path: str) -> list[str | None]:
    if value is None:
        return []

    if not isinstance(value, list) or isinstance(value, _Members):
        raise ValueError(f"Error converting value to type 'System.String[]'. Path '{path}'.")

    return [_to_text(item, path) for item in value]


def _to_text(value: object, path: str) -> str | None:
    if value is None or isinstance(value, str):
        return value

    if isinstance(value, bool):
        return "true" if value else "false"

    raise ValueError(f"Unexpected character encountered while parsing value. Path '{path}'.")


def _charset_of(content_type: str | None) -> str | None:
    if content_type is None:
        return None

    for parameter in content_type.split(";")[1:]:
        name, _, value = parameter.partition("=")

        if name.strip().lower() == "charset":
            return value.strip().strip('"') or None

    return None
