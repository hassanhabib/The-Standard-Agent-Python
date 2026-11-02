# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""README.md is not only documentation: it is the package page.

pyproject.toml packs it as the long description, so it IS the PyPI page, the first thing anyone
considering the library reads. The C# twin guards the NuGet page; PyPI's renderer fails the same
two ways. It strips or prints raw HTML that GitHub renders, and it has no repository context, so
a relative link resolves to nothing. Neither failure is visible from the repository, which is
exactly why it is a test.
"""

import re
from pathlib import Path

README = Path(__file__).resolve().parents[3] / "README.md"


def _prose() -> str:
    """The README without its code: HTML inside a fence or backticks is shown as code."""
    readme_text = README.read_text(encoding="utf-8")
    without_fences = re.sub(r"```.*?```", "", readme_text, flags=re.DOTALL)

    return re.sub(r"`[^`\n]*`", "", without_fences)


def test_should_carry_no_raw_html_so_the_nu_get_page_does_not_print_the_tags():
    # given
    prose = _prose()

    # when
    tags = re.findall(r"</?[a-zA-Z][^>]*>", prose)

    # then
    assert tags == [], (
        "README.md is the PyPI page, which does not render raw HTML as GitHub does: "
        f"{tags} would not show as written. State it in markdown instead.")

