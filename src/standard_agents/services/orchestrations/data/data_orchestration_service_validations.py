# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.data.exceptions import NullAgentContextException


# Circuit-breaking: there is nothing to recall into without a context.
def validate_context(context: AgentContext) -> None:
    if context is None:
        raise NullAgentContextException(message="Agent context is null.")
