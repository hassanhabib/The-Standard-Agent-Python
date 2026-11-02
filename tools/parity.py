# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# python tools/parity.py <path to Standard.Agents.Tests.Unit> [--missing] [--class <name>]
#
# Measures test parity with the C# reference implementation: every [Fact] and [Theory] in the C#
# unit test project, matched by name to a Python test. ShouldAddMemoryAsync is ported when a test
# named test_should_add_memory exists anywhere under tests/. A C# theory counts once, however many
# cases it carries, because its Python port is one parametrized test.

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

CSHARP_TEST = re.compile(
    r"\[(?:Fact|Theory)[^\]]*\](?:\s*\[[^\]]*\])*\s*public\s+(?:async\s+)?[\w<>]+\s+(\w+)\s*\(",
    re.MULTILINE)

PYTHON_TEST = re.compile(r"^\s*(?:async\s+)?def (test_\w+)\s*\(", re.MULTILINE)


def python_name(csharp_name: str) -> str:
    name = csharp_name.removesuffix("Async")
    words = re.findall(r"[A-Z]+\d*(?=[A-Z][a-z]|\b)|[A-Z]?[a-z]+\d*|\d+|[A-Z]+\d*", name)

    return "test_" + "_".join(word.lower() for word in words)


def csharp_tests(tests_root: Path) -> dict[str, list[str]]:
    tests_by_class = defaultdict(list)

    for source in sorted(tests_root.rglob("*.cs")):
        if "obj" in source.parts or "bin" in source.parts:
            continue

        class_name = source.name.split(".")[0]

        for match in CSHARP_TEST.finditer(source.read_text(encoding="utf-8-sig")):
            tests_by_class[class_name].append(match.group(1))

    return tests_by_class


def python_tests(tests_root: Path) -> set[str]:
    names = set()

    for source in tests_root.rglob("*.py"):
        names.update(PYTHON_TEST.findall(source.read_text(encoding="utf-8")))

    return names


def main() -> int:
    parser = argparse.ArgumentParser(prog="python tools/parity.py")
    parser.add_argument("csharp_tests", type=Path)
    parser.add_argument("--python-tests", type=Path, default=Path("tests"))
    parser.add_argument("--missing", action="store_true")
    parser.add_argument("--class", dest="class_name")
    arguments = parser.parse_args()

    tests_by_class = csharp_tests(arguments.csharp_tests)
    ported = python_tests(arguments.python_tests)
    total, matched = 0, 0

    for class_name in sorted(tests_by_class):
        if arguments.class_name and class_name != arguments.class_name:
            continue

        names = sorted(set(tests_by_class[class_name]))
        missing = [name for name in names if python_name(name) not in ported]
        total += len(names)
        matched += len(names) - len(missing)
        print(f"{len(names) - len(missing):4}/{len(names):<4} {class_name}")

        if arguments.missing:
            for name in missing:
                print(f"            {name}  ->  {python_name(name)}")

    percentage = 100 * matched / total if total else 100.0
    print(f"\nparity: {matched}/{total} C# tests ({percentage:.1f}%)")

    return 0 if matched == total else 1


if __name__ == "__main__":
    sys.exit(main())
