# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.foundations.skills.exceptions import (
    FailedSkillDependencyException,
    SkillDependencyException)
from standard_agents.models.foundations.skills.skill import Skill

_SKILL_SEPARATOR = "\n\n"


class SkillService:
    """The skills the agent reads, composed into one text in name order."""

    def __init__(self, *, skill_broker: SkillBroker, logging_broker: LoggingBroker) -> None:
        self.skill_broker = skill_broker
        self.logging_broker = logging_broker

    async def retrieve_skills(self, route: str = "") -> str:
        async with _handling_exceptions(self.logging_broker):
            skills = await self.skill_broker.select_skills()
            selected_skills = sorted(skills, key=_ordinal_name)

            if route and not route.isspace():
                routed_skills = [
                    skill for skill in selected_skills
                    if _contains_ordinal_ignore_case(skill.name, route)]

                if routed_skills:
                    selected_skills = routed_skills

            return _SKILL_SEPARATOR.join(skill.content for skill in selected_skills)


def _ordinal_name(skill: Skill) -> bytes:
    """The skill's name as StringComparer.Ordinal compares it: by UTF-16 code units."""
    return skill.name.encode("utf-16-be", errors="surrogatepass")


def _contains_ordinal_ignore_case(text: str, value: str) -> bool:
    """string.Contains(value, StringComparison.OrdinalIgnoreCase).

    Each character is compared by its simple (one character) upper-case mapping, never a
    culture's.
    """
    return _to_upper_ordinal(value) in _to_upper_ordinal(text)


def _to_upper_ordinal(text: str) -> str:
    """Uppercases each character on its own, keeping it as it is when its mapping expands."""
    folded: list[str] = []

    for character in text:
        upper = character.upper()
        folded.append(upper if len(upper) == 1 else character)

    return "".join(folded)


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except (FileNotFoundError, NotADirectoryError, PermissionError) as critical_error:
        failed_skill_dependency_exception = FailedSkillDependencyException(
            message="Failed skill dependency error occurred, contact support.",
            inner_exception=critical_error)

        raise await _create_and_log_critical_dependency_exception(
            logging_broker, failed_skill_dependency_exception)
    except OSError as os_error:
        failed_skill_dependency_exception = FailedSkillDependencyException(
            message="Failed skill dependency error occurred, contact support.",
            inner_exception=os_error)

        raise await _create_and_log_dependency_exception(
            logging_broker, failed_skill_dependency_exception)


async def _create_and_log_critical_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> SkillDependencyException:

    skill_dependency_exception = SkillDependencyException(
        message="Skill dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_critical(skill_dependency_exception)

    return skill_dependency_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> SkillDependencyException:

    skill_dependency_exception = SkillDependencyException(
        message="Skill dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(skill_dependency_exception)

    return skill_dependency_exception
