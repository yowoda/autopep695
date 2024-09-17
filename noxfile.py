# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import typing as t

import nox
from nox import options

SCRIPT_PATHS = [
    os.path.join(".", "autopep695"),
    os.path.join(".", "scripts"),
    os.path.join(".", "tests"),
    "noxfile.py",
]

options.sessions = ["format_fix", "typecheck", "slotscheck", "copyright_fix", "test"]


def session(
    **kwargs: t.Any,
) -> t.Callable[[t.Callable[[nox.Session], None]], t.Callable[[nox.Session], None]]:
    kwargs.setdefault("venv_backend", "uv|virtualenv")
    kwargs.setdefault("reuse_venv", True)

    def inner(func: t.Callable[[nox.Session], None]) -> t.Callable[[nox.Session], None]:
        return nox.session(**kwargs)(func)

    return inner


@session()
def format_fix(session: nox.Session) -> None:
    session.install(".[dev.format]")
    session.run("python", "-m", "ruff", "format", *SCRIPT_PATHS)
    session.run("python", "-m", "ruff", "check", "--fix", *SCRIPT_PATHS)


@session()
def format_check(session: nox.Session) -> None:
    session.install(".[dev.format]")
    session.run("python", "-m", "ruff", "format", *SCRIPT_PATHS, "--check")
    session.run(
        "python", "-m", "ruff", "check", "--output-format", "github", *SCRIPT_PATHS
    )


@session()
def typecheck(session: nox.Session) -> None:
    session.install(".[dev.typecheck]")
    session.run("python", "-m", "pyright")


@session()
def slotscheck(session: nox.Session) -> None:
    session.install(".[dev.slotscheck]")
    session.run("python", "-m", "slotscheck", "-m", "autopep695")


@session()
def test(session: nox.Session) -> None:
    session.install(".[dev.test]")
    session.run("python", "-m", "pytest", "tests")


@session()
def copyright_fix(session: nox.Session) -> None:
    session.run("python", "scripts/copyright.py", "--fix")
