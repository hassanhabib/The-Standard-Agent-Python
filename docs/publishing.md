# Publishing to PyPI

Three distributions, three repositories, one order. Each one depends on the one before it, so each
must be on PyPI before the next is released:

| Order | Distribution | Repository | Depends on |
|---|---|---|---|
| 1 | `xeption` 1.0.0.0 | [Xeption-Python](https://github.com/hassanhabib/Xeption-Python) | nothing |
| 2 | `restfulsense` 1.0.0.0 | [RESTFulSense-Python](https://github.com/hassanhabib/RESTFulSense-Python) | `xeption` |
| 3 | `the-standard-agent` 6.0.0.0 | this repository | `xeption`, `restfulsense` |

Every repository publishes the same way, with `.github/workflows/publish.yml` and PyPI Trusted
Publishing. No token exists anywhere: PyPI trusts the repository, the workflow file and the
GitHub environment, and GitHub proves all three with a short-lived OIDC token.

- Running the workflow by hand (Actions, Publish To PyPI, Run workflow) uploads to TestPyPI
  through the `testpypi` environment. This is the dry run.
- Publishing a GitHub release uploads to PyPI through the `pypi` environment.

Both build only after the tests pass and `twine check --strict` passes.

## One-time setup, per repository

These need the owner's own PyPI, TestPyPI and GitHub accounts.

1. **Pending publisher on PyPI.** At https://pypi.org/manage/account/publishing/ add a pending
   publisher: the project name (`xeption`, `restfulsense` or `the-standard-agent`), owner
   `hassanhabib`, the repository name, workflow `publish.yml`, environment `pypi`. A pending
   publisher reserves nothing until the first upload, so the first release should follow soon.
2. **Pending publisher on TestPyPI.** The same at https://test.pypi.org/manage/account/publishing/,
   with environment `testpypi`. TestPyPI is a separate account.
3. **GitHub environments.** In the repository's Settings, Environments, create `testpypi` and
   `pypi`. On `pypi`, add yourself as a required reviewer so no release uploads without a click.
4. Two-factor authentication must be on for both PyPI accounts.

## Releasing, in order

For each distribution, `xeption` first:

1. Run the publish workflow by hand and check the TestPyPI page.
2. Draft a GitHub release with a tag matching the version in `pyproject.toml` (for example
   `v1.0.0.0`) and publish it. Approve the `pypi` deployment when asked.
3. Check the PyPI page, then `pip install <name>` in a clean environment.

A version can be uploaded to PyPI once. A mistake after upload is fixed with a new version, not a
replacement, so the TestPyPI dry run comes first.

## After xeption and restfulsense are published

CI here and in RESTFulSense-Python installs the dependencies from their repositories, because they
are not on PyPI yet. Once they are, remove those steps:

- RESTFulSense-Python: the `Installing Xeption` step in `python.yml` and `publish.yml`.
- This repository: the `Installing Xeption And RESTFulSense` step in `python.yml` and
  `publish.yml`, and the matching note in CONTRIBUTING.md.
