# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass, field

from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.models.orchestrations.effects.agent_principal import AgentPrincipal
from standard_agents.models.orchestrations.effects.permission_mode import PermissionMode
from standard_agents.models.orchestrations.effects.risk_level import RiskLevel


@dataclass(frozen=True)
class PerimeterPolicy:
    """The perimeter's standing orders, as one datum.

    What mode permission runs in, what each tool declared about itself, and the host's own
    hooks for who is acting and what is explicitly permitted. Policy is Data: these ride
    together as a value the perimeter consults, not as constructor sprawl no dependency count
    can see.

    The three per-tool mappings are keyed by tool name; the C# keys them OrdinalIgnoreCase.
    """

    # What permission means when nothing named the act (SPEC.md 4.9).
    mode: PermissionMode = PermissionMode.OPEN

    # The tools whose acts require approval before running.
    irreversible_tools: Collection[str] = ()

    # Risk the host declared per tool, overriding what the tool says of itself.
    declared_risk: Mapping[str, RiskLevel] = field(default_factory=dict)

    # Risk each tool declares about itself, read once at composition.
    tool_risk: Mapping[str, RiskLevel] = field(default_factory=dict)

    # Each tool's own reading of what an act touches (Tool.ScopeOf). The tool is the only thing
    # that knows what its arguments mean; the framework never parses them.
    tool_scope: Mapping[str, Callable[[str], str]] = field(default_factory=dict)

    # Whether the configured allow-list speaks to an act at all, which the mode needs and a
    # yes/no authorization decision cannot carry. None when no allow-list was configured, so
    # ASK asks about everything.
    explicitly_permits: Callable[[AgentEffect], bool] | None = None

    # Who is acting, asked per act rather than captured at composition, because the principal
    # can change between prompts on a shared agent (SPEC.md 4.4).
    identity_resolver: Callable[[], AgentPrincipal | None] | None = None

    # Whether the run's offering (SPEC.md 4.15) binds at the perimeter. Off by default: an
    # unoffered tool keeps its 6.1 treatment, callable if the Brain names it. On, an act naming
    # an advertised tool the run was not offered is denied (told, non-terminal, recoverable).
    # Caller tools are never subject to selection, and an undescribed tool keeps its 6.1
    # treatment either way.
    enforce_selection: bool = False

    # The advertised tool names (what selection could have offered), so the perimeter can tell
    # a withheld tool from an undescribed one. Derived at composition from the same rendering
    # the catalogs use, so the two can never disagree.
    advertised_tools: Collection[str] = ()
