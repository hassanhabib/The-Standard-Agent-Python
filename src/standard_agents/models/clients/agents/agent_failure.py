# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass

from standard_agents.models.clients.agents.agent_failure_category import AgentFailureCategory


# Why a run stopped without delivering an answer (SPEC.md 3.6, v1.14), for the caller that
# decides what to do next by switching on a code rather than by reading a sentence.
# category: which kind of stop it was, in the categories every failure uses.
# code: one of AgentFailureCodes, or a code of the host's own.
# message: the sentence a person is shown, the same one the run's result carries.
@dataclass(frozen=True)
class AgentFailure:
    category: AgentFailureCategory
    code: str
    message: str
