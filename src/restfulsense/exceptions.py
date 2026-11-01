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


# .NET's HttpRequestException: the request never got an answer (refused, unresolved, timed out).
# It is not a Xeption in .NET, so it is not one here.
class HttpRequestException(Exception):
    def __init__(self, message: str = "", status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
