# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""A stdlib MCP server the process tests start through the stdio broker.

It starts one child of its own, as npx starts node, and lists its own process id and the
child's as its tools, so a test can tell whether the whole tree is still running. The tools are
described, so an agent advertises them and a test can read the ids from its tool catalog; a
call answers with the same ids, as the server running now has them.
"""

import json
import os
import subprocess
import sys


def main() -> None:
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(120)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)

    while line := sys.stdin.readline():
        message = json.loads(line)

        if "id" not in message:
            continue

        if message.get("method") == "initialize":
            result = {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "processes", "version": "1.0.0"},
            }
        elif message.get("method") == "tools/call":
            process_ids = f"server-{os.getpid()} child-{child.pid}"
            result = {"content": [{"type": "text", "text": process_ids}]}
        else:
            result = {"tools": [
                {"name": f"server-{os.getpid()}", "description": "the server's process id"},
                {"name": f"child-{child.pid}", "description": "its child's process id"},
            ]}

        print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)


if __name__ == "__main__":
    main()
