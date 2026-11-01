# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


# The Python stand-in for RESTFulSense's exceptions: one type per HTTP status, each a Xeption
# carrying the response's status code, its body, and any problem details as data, so a foundation
# can localize a failure by its type exactly as the C# framework does.
class HttpResponseException(Xeption):
    def __init__(
        self,
        message: str = "",
        status_code: int = 0,
        content: str = "",
        data: dict[str, list[str]] | None = None) -> None:

        super().__init__(message)
        self.status_code = status_code
        self.content = content

        if data:
            self.add_data(data)


class HttpResponseBadRequestException(HttpResponseException):
    pass


class HttpResponseUnauthorizedException(HttpResponseException):
    pass


class HttpResponseForbiddenException(HttpResponseException):
    pass


# 404 for a resource the server knows it does not have.
class HttpResponseNotFoundException(HttpResponseException):
    pass


# 404 for an address nothing answers at: the route itself does not exist.
class HttpResponseUrlNotFoundException(HttpResponseException):
    pass


class HttpResponseConflictException(HttpResponseException):
    pass


class HttpResponseInternalServerErrorException(HttpResponseException):
    pass


class HttpResponseServiceUnavailableException(HttpResponseException):
    pass


# The rest of the statuses RESTFulSense 3.2.0 gives a type of its own. A status in none of
# these classes is not a failure to RESTFulSense: its ValidationService lets it through.
class HttpResponsePaymentRequiredException(HttpResponseException):
    pass


class HttpResponseMethodNotAllowedException(HttpResponseException):
    pass


class HttpResponseNotAcceptableException(HttpResponseException):
    pass


class HttpResponseProxyAuthenticationRequiredException(HttpResponseException):
    pass


class HttpResponseRequestTimeoutException(HttpResponseException):
    pass


class HttpResponseGoneException(HttpResponseException):
    pass


class HttpResponseLengthRequiredException(HttpResponseException):
    pass


class HttpResponsePreconditionFailedException(HttpResponseException):
    pass


class HttpResponseRequestEntityTooLargeException(HttpResponseException):
    pass


class HttpResponseRequestUriTooLongException(HttpResponseException):
    pass


class HttpResponseUnsupportedMediaTypeException(HttpResponseException):
    pass


class HttpResponseRequestedRangeNotSatisfiableException(HttpResponseException):
    pass


class HttpResponseExpectationFailedException(HttpResponseException):
    pass


class HttpResponseMisdirectedRequestException(HttpResponseException):
    pass


class HttpResponseUnprocessableEntityException(HttpResponseException):
    pass


class HttpResponseLockedException(HttpResponseException):
    pass


class HttpResponseFailedDependencyException(HttpResponseException):
    pass


class HttpResponseUpgradeRequiredException(HttpResponseException):
    pass


class HttpResponsePreconditionRequiredException(HttpResponseException):
    pass


class HttpResponseTooManyRequestsException(HttpResponseException):
    pass


class HttpResponseRequestHeaderFieldsTooLargeException(HttpResponseException):
    pass


class HttpResponseUnavailableForLegalReasonsException(HttpResponseException):
    pass


class HttpResponseNotImplementedException(HttpResponseException):
    pass


class HttpResponseBadGatewayException(HttpResponseException):
    pass


class HttpResponseGatewayTimeoutException(HttpResponseException):
    pass


class HttpResponseHttpVersionNotSupportedException(HttpResponseException):
    pass


class HttpResponseVariantAlsoNegotiatesException(HttpResponseException):
    pass


class HttpResponseInsufficientStorageException(HttpResponseException):
    pass


class HttpResponseLoopDetectedException(HttpResponseException):
    pass


class HttpResponseNotExtendedException(HttpResponseException):
    pass


class HttpResponseNetworkAuthenticationRequiredException(HttpResponseException):
    pass


# .NET's HttpRequestException: the request never got an answer (refused, unresolved, timed out).
# It is not a Xeption in .NET, so it is not one here.
class HttpRequestException(Exception):
    def __init__(self, message: str = "", status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
