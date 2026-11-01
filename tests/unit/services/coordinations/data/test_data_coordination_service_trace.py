# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call


async def test_should_narrate_processes_to_logging_broker_on_recall(
        data_coordination_service,
        skill_service,
        memory_service,
        logging_broker,
        containing,
        create_random_agent_context,
        create_random_string):
    # given
    input_context = create_random_agent_context()
    skill_service.retrieve_skills.return_value = create_random_string()
    memory_service.recall_memories.return_value = []

    # when
    await data_coordination_service.recall(input_context)

    # then
    assert logging_broker.mock_calls.count(
        call.log_process("Data", containing("memories"))) == 1

    assert logging_broker.mock_calls.count(
        call.log_process("Data", containing("knowledge"))) == 1
