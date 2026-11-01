# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import call


async def test_should_measure_prompt_and_completion_separately_on_measure(
        usage_service,
        usage_broker,
        logging_broker,
        create_random_string,
        create_random_token_count):

    # given
    random_prompt = create_random_string()
    random_completion = create_random_string()
    random_prompt_tokens = create_random_token_count()
    random_completion_tokens = create_random_token_count()

    usage_broker.count_tokens.side_effect = {
        random_prompt: random_prompt_tokens,
        random_completion: random_completion_tokens}.get

    # when
    actual_usage = await usage_service.measure(random_prompt, random_completion)

    # then
    assert actual_usage.prompt_tokens == random_prompt_tokens
    assert actual_usage.completion_tokens == random_completion_tokens
    assert actual_usage.total_tokens == random_prompt_tokens + random_completion_tokens

    assert usage_broker.mock_calls == [
        call.count_tokens(random_prompt),
        call.count_tokens(random_completion)]

    assert logging_broker.mock_calls == []


async def test_should_mark_a_measured_call_as_estimated_on_measure(
        usage_service, usage_broker, create_random_string, create_random_token_count):
    """Anything this service produces was counted here, so it says so.

    A counted number and a reported one are both usable for a budget, but only one can be
    reconciled against an invoice: a caller that cannot tell them apart will eventually present
    an estimate as a bill.
    """
    # given
    random_prompt = create_random_string()
    random_completion = create_random_string()
    usage_broker.count_tokens.return_value = create_random_token_count()

    # when
    actual_usage = await usage_service.measure(random_prompt, random_completion)

    # then
    assert actual_usage.is_estimated
