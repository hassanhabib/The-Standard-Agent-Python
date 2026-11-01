# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""python -m conformance <vectors-folder> [--profile Core|Reliable|Enterprise|Critical]

The vectors are the specification's executable half and live with the reference implementation
(hassanhabib/The-Standard-Agent, conformance/vectors), with the readiness profiles beside them in
conformance/profiles. Nothing here is private: anyone can clone that repository and run this
command (SPEC.md 1.1). The exit code is zero only when every vector passed and the named profile,
if any, certified.
"""

import argparse
import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

from conformance import report
from conformance.certification import certify


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m conformance")
    parser.add_argument("vectors")
    parser.add_argument("--profile")
    arguments = parser.parse_args()

    # A character the console cannot show is shown as a replacement, never a crash halfway
    # through the report.
    sys.stdout.reconfigure(errors="replace")

    report.print_header(arguments.vectors, arguments.profile)

    vectors_path = Path(arguments.vectors).resolve()
    profiles_path = vectors_path.parent / "profiles"

    # The folder a vector's files are written to, and the working directory the agent resolves
    # relative names against: the reference runner's application base directory.
    base_directory = Path(tempfile.mkdtemp(prefix="standard-agents-conformance-"))
    working_directory = os.getcwd()
    os.chdir(base_directory)

    try:
        return asyncio.run(certify(vectors_path, profiles_path, arguments.profile, base_directory))
    finally:
        os.chdir(working_directory)
        shutil.rmtree(base_directory, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
