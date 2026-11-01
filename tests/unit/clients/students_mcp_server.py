# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""A real MCP server over standard input and output, for the tests that start one.

The Python twin of Standard.Agents.Tests.McpServer: it offers one tool, find_student, and
answers with the school from its environment and the term from its first argument, so a test can
see both reached the process.
"""

import json
import os
import sys

_INITIALIZE = {
    "protocolVersion": "2025-06-18",
    "capabilities": {"tools": {}},
    "serverInfo": {"name": "students", "version": "1.0.0"},
}

_TOOLS = {
    "tools": [{
        "name": "find_student",
        "description": "Finds a student by their id.",
        "inputSchema": {"type": "object", "properties": {"id": {"type": "integer"}}},
    }],
}


def main() -> None:
    school = os.environ.get("STUDENTS_SCHOOL", "no school")
    term = sys.argv[1] if len(sys.argv) > 1 else "no term"

    for line in sys.stdin:
        message = json.loads(line)

        if message.get("id") is None:
            continue

        method = message["method"]

        if method == "initialize":
            result = _INITIALIZE
        elif method == "tools/list":
            result = _TOOLS
        else:
            result = _find_student(message.get("params", {}).get("arguments"), school, term)

        answer = {"jsonrpc": "2.0", "id": message["id"], "result": result}
        sys.stdout.write(json.dumps(answer, separators=(",", ":")) + "\n")
        sys.stdout.flush()


def _find_student(arguments: dict | None, school: str, term: str) -> dict:
    arguments = arguments or {}
    student_id = arguments.get("id", arguments.get("input"))
    student = "unknown" if student_id is None else student_id
    text = f"student {student} is Hassan, at {school}, for the {term} term"

    return {"content": [{"type": "text", "text": text}]}


if __name__ == "__main__":
    main()
