# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import logging

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker


class LoggingBroker(ILoggingBroker):
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    async def log_information(self, message: str) -> None:
        self.logger.info(message)

    async def log_warning(self, message: str) -> None:
        self.logger.warning(message)

    async def log_error(self, exception: BaseException) -> None:
        self.logger.error(str(exception), exc_info=exception)

    async def log_critical(self, exception: BaseException) -> None:
        self.logger.critical(str(exception), exc_info=exception)

    async def log_turn(self, run_id: str, turn: int) -> None:
        self.logger.info("Turn %d (run %s)", turn, run_id)

    async def log_process(self, actor: str, message: str) -> None:
        self.logger.info("[%s] %s", actor, message)
