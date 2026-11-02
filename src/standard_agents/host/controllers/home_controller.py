# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.host.controllers.action_results import ObjectResult


class HomeController:
    """The heartbeat, GET api/home.

    No security, no dependencies, aliveness and nothing else: the endpoint a load balancer or a
    first-day deployment checks before anything harder.
    """

    def get(self) -> ObjectResult:
        raise NotImplementedError
