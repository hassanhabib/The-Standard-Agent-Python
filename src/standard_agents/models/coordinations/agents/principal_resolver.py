# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Callable

from standard_agents.models.orchestrations.effects.agent_principal import AgentPrincipal


# Who the host says is acting (SPEC.md 4.9), asked per run. A model carrying a delegate rather
# than a naked delegate parameter, because configuration crosses natures where a dependency may
# not. The loop reads it to stamp a session with its owner and to refuse a session another
# principal opened (SPEC.md 4.11).
class PrincipalResolver:
    def __init__(self, resolve: Callable[[], AgentPrincipal | None]) -> None:
        self._resolve = resolve

    def resolve(self) -> AgentPrincipal | None:
        return self._resolve()
