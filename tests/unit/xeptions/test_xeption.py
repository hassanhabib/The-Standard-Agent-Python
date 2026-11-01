# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import uuid

from xeptions import Xeption


def create_random_string() -> str:
    return uuid.uuid4().hex


class TestXeption:
    def test_should_upsert_data_list(self) -> None:
        # given
        random_key = create_random_string()
        random_first_value = create_random_string()
        random_second_value = create_random_string()
        xeption = Xeption(message=create_random_string())

        expected_data = {
            random_key: [random_first_value, random_second_value]
        }

        # when
        xeption.upsert_data_list(random_key, random_first_value)
        xeption.upsert_data_list(random_key, random_second_value)

        # then
        assert xeption.data == expected_data

    def test_should_throw_if_contains_errors(self) -> None:
        # given
        xeption = Xeption(message=create_random_string())
        xeption.upsert_data_list(create_random_string(), create_random_string())
        actual_xeption = None

        # when
        try:
            xeption.throw_if_contains_errors()
        except Xeption as raised_xeption:
            actual_xeption = raised_xeption

        # then
        assert actual_xeption is xeption

    def test_should_not_throw_if_contains_no_errors(self) -> None:
        # given
        xeption = Xeption(message=create_random_string())

        # when
        xeption.throw_if_contains_errors()

        # then
        assert xeption.data == {}

    def test_should_add_data(self) -> None:
        # given
        random_key = create_random_string()
        random_existing_value = create_random_string()
        random_added_value = create_random_string()
        xeption = Xeption(message=create_random_string())
        xeption.upsert_data_list(random_key, random_existing_value)
        input_data = {random_key: [random_added_value]}

        expected_data = {
            random_key: [random_existing_value, random_added_value]
        }

        # when
        xeption.add_data(input_data)

        # then
        assert xeption.data == expected_data
