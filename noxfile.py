# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os

import nox
from nox import options

SCRIPT_PATHS = [
    os.path.join(".", "autopep695"),
    "noxfile.py",
]

options.sessions = ["format_fix", "typecheck", "slotscheck"]


@nox.session()
def format_fix(session: nox.Session) -> None:
    session.install(".[dev.format]")
    session.run("python", "-m", "ruff", "format", *SCRIPT_PATHS)
    session.run("python", "-m", "ruff", "check", "--fix", *SCRIPT_PATHS)


@nox.session()
def format_check(session: nox.Session) -> None:
    session.install(".[dev.format]")
    session.run("python", "-m", "ruff", "format", *SCRIPT_PATHS, "--check")
    session.run(
        "python", "-m", "ruff", "check", "--output-format", "github", *SCRIPT_PATHS
    )


@nox.session()
def typecheck(session: nox.Session) -> None:
    session.install(".[dev.typecheck]")
    session.run("python", "-m", "pyright")


@nox.session()
def slotscheck(session: nox.Session) -> None:
    session.install(".[dev.slotscheck]")
    session.run("python", "-m", "slotscheck", "-m", "autopep695")
