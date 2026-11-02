# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""A grounded answer cites its sources (SPEC.md 4.2).

The loop cites, not the model. A model asked to name its sources names them when it feels like
it, so the citation is written by the loop, from the sources Recall put on the run, once the run
has answered: after the Judge, which scores the model's answer and not lines the agent wrote,
and before the Response event and the session write, so every door carries the same text.
"""

import dataclasses

from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.services.managements._text import contains_ignoring_case, is_blank, trim_end


def is_citing_knowledge(configured_cite_knowledge: bool | None, request: PromptRequest) -> bool:
    """Precedence, as every request field obeys it: configured, then requested, then off.

    A deployment that must cite cannot be switched off by a caller, and one that never cites
    cannot be switched on (docs/per-request-inference.md 4).
    """
    if configured_cite_knowledge is not None:
        return configured_cite_knowledge

    return request.cite_knowledge if request.cite_knowledge is not None else False


def with_citations(context: AgentContext, citation_prefix: str) -> AgentContext:
    """The answer with a line for each source it does not already credit.

    Only an answer is cited: a run that refused, asked, is waiting or failed has nothing to
    credit. Nor is an answer held to a response schema, because a line after it breaks the very
    shape the caller was promised.
    """
    response_schema_json = (
        context.inference.response_schema_json if context.inference is not None else None)

    if context.status is not AgentStatus.RESPONDED or not is_blank(response_schema_json):
        return context

    citations = [
        citation for citation in (
            citation_prefix + source for source in context.grounding_sources)
        if not contains_ignoring_case(context.result, citation)]

    if not citations:
        return context

    cited_result = trim_end(context.result) + "\n\n" + "\n".join(citations)

    return dataclasses.replace(context, result=cited_result)
