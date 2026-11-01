# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# No C# twin: the stdio broker over a real server process, started from its command. C# stops
# that process and every process it started (Process.Kill(entireProcessTree: true)) when the
# host exits; Python gives the same stop a lifecycle of its own, aclose() and async with, so a
# host or a test does not leave the tree running until the interpreter exits.

import asyncio
import os
import sys

from standard_agents.brokers.mcps.stdio_mcp_broker import StdioMcpBroker

SERVER_PATH = os.path.join(os.path.dirname(__file__), "stdio_process_server.py")


def create_broker() -> StdioMcpBroker:
    return StdioMcpBroker(command=sys.executable, arguments=[SERVER_PATH], timeout_seconds=30)


async def process_ids_of(broker: StdioMcpBroker) -> list[int]:
    """The server's process id and its child's, as the server lists them."""
    tools = await broker.list_tools()

    return [int(tool.name.split("-")[1]) for tool in tools]


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


async def test_should_stop_the_server_and_every_process_it_started_when_closed():
    # given: a server that started a child of its own
    broker = create_broker()
    process_ids = await process_ids_of(broker)

    # when
    await broker.aclose()

    # then: the whole tree is gone
    assert await have_stopped(process_ids)


async def test_should_stop_the_server_and_every_process_it_started_when_its_block_ends():
    # given, when: a server that started a child of its own, used inside an async with block
    async with create_broker() as broker:
        process_ids = await process_ids_of(broker)

    # then: the whole tree is gone
    assert await have_stopped(process_ids)


async def test_should_start_a_server_named_on_the_path_without_arguments(tmp_path, monkeypatch):
    # given: a launcher found by its bare name on PATH and started with no arguments, as npx is;
    # on Windows through PATHEXT, as ResolveCommand finds npx.cmd
    if os.name == "nt":
        launcher = tmp_path / "wire-process-server.cmd"
        launcher.write_text(f'@"{sys.executable}" "{SERVER_PATH}"\n', encoding="utf-8")
    else:
        launcher = tmp_path / "wire-process-server"
        launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{SERVER_PATH}"\n')
        launcher.chmod(0o755)

    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")

    # when
    async with StdioMcpBroker(command="wire-process-server", timeout_seconds=30) as broker:
        actual_tools = await broker.list_tools()

    # then
    assert [tool.name.split("-")[0] for tool in actual_tools] == ["server", "child"]
