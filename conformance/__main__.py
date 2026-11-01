# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import argparse
import asyncio
import sys
from pathlib import Path

from conformance.runner import certify

# python -m conformance <vectors-folder> [--profile Core] [--profiles <profiles-folder>]
#
# The vectors are the specification's executable half and live with the reference
# implementation (hassanhabib/The-Standard-Agent, conformance/vectors). Nothing here is private:
# anyone can clone that repository and run this command (SPEC.md 1.1).


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m conformance")
    parser.add_argument("vectors", type=Path)
    parser.add_argument("--profile")
    parser.add_argument("--profiles", type=Path)
    arguments = parser.parse_args()

    profiles_path = arguments.profiles or arguments.vectors.parent / "profiles"

    return asyncio.run(certify(arguments.vectors, arguments.profile, profiles_path))


if __name__ == "__main__":
    sys.exit(main())
