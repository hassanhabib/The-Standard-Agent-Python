# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from http import HTTPStatus

from standard_agents.host.controllers.action_results import ObjectResult
from standard_agents.host.controllers.home_controller import HomeController


def test_should_get_alive():
    # given
    home_controller = HomeController()
    expected_result = ObjectResult(HTTPStatus.OK, "The Standard Agent is alive.")

    # when
    actual_result = home_controller.get()

    # then: aliveness and nothing else, no security, no dependencies, no claims
    assert actual_result == expected_result
