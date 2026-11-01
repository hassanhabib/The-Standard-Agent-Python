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
