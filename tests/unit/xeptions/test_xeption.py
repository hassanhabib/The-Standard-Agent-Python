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

    def test_should_tell_whether_exceptions_are_the_same(self) -> None:
        # given
        random_message = create_random_string()
        random_key = create_random_string()
        random_value = create_random_string()
        native_exception = RuntimeError(random_message)

        def create_xeption() -> Xeption:
            inner_xeption = Xeption(
                message=random_message,
                inner_exception=native_exception)

            inner_xeption.upsert_data_list(random_key, random_value)

            return Xeption(message=random_message, inner_exception=inner_xeption)

        expected_xeption = create_xeption()
        same_xeption = create_xeption()
        other_message_xeption = Xeption(message=create_random_string())

        other_inner_xeption = Xeption(
            message=random_message,
            inner_exception=Xeption(message=create_random_string()))

        other_data_xeption = create_xeption()
        other_data_xeption.inner_exception.upsert_data_list(random_key, random_value)

        # when
        actual_results = [
            expected_xeption.same_exception_as(same_xeption),
            expected_xeption.same_exception_as(other_message_xeption),
            expected_xeption.same_exception_as(other_inner_xeption),
            expected_xeption.same_exception_as(other_data_xeption),
            expected_xeption.same_exception_as(None)
        ]

        # then
        assert actual_results == [True, False, False, False, False]
