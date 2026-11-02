# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Whether processes a test started are still running, for the tests that stop them."""

import asyncio
import os


async def have_stopped(process_ids: list[int], timeout_seconds: float = 10) -> bool:
    deadline = asyncio.get_running_loop().time() + timeout_seconds

    while any(is_running(process_id) for process_id in process_ids):
        if asyncio.get_running_loop().time() > deadline:
            return False

        await asyncio.sleep(0.05)

    return True


def is_running(process_id: int) -> bool:
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        query_limited_information = 0x1000
        still_active = 259
        handle = kernel32.OpenProcess(query_limited_information, False, process_id)

        if not handle:
            return False

        try:
            exit_code = ctypes.c_ulong()
            kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))

            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)

    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

    return True
