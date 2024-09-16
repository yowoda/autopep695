# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import argparse
import logging
import sys
import typing as t
from pathlib import Path

from colorama import just_fix_windows_console

from autopep695 import analyzer, __version__
from autopep695.ux import init_logging, RED, RESET, BOLD, format_special
from autopep695.errors import InvalidPath

INCLUDE_PATTERNS: t.Final[t.Sequence[str]] = ("*.py", "*.pyi")
EXCLUDE_PATTERNS: t.Final[t.Sequence[str]] = (
    ".bzr",
    ".direnv",
    ".eggs",
    ".git",
    ".git-rewrite",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pants.d",
    ".pytype",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pypackages__",
    "_build",
    "buck-out",
    "dist",
    "node_modules",
    "venv",
    "__pycache__",
)


def filter_paths(
    paths: t.Iterable[Path], include: t.Iterable[str], exclude: t.Iterable[str]
) -> t.Iterable[Path]:
    for path in paths:
        if not path.exists():
            raise InvalidPath(str(path))

        if any((path.match(pattern) for pattern in exclude)):
            continue

        if path.is_file() and any((path.match(pattern) for pattern in include)):
            yield path

        elif path.is_dir():
            yield from filter_paths(path.iterdir(), include=include, exclude=exclude)


def main() -> None:
    parser = argparse.ArgumentParser(
        "PEP695 upgrade tool",
        description="Automatically upgrade to the new type parameter syntax introduced in python 3.12",
    )
    subparsers = parser.add_subparsers(dest="subparser")
    check_parser = subparsers.add_parser(
        "check",
        help="Check code for pep695 compliance",
        description="Find all places where the code still uses old type annotation syntax",
    )
    check_parser.add_argument(
        "paths",
        nargs="*",
        help="Paths to a directory or a file that contains code using the old type annotation syntax",
        type=Path,
        default=[Path.cwd()],
    )
    check_parser.add_argument(
        "-s",
        "--silent",
        required=False,
        action="store_true",
        help="Whether to silent the error reports.",
    )
    check_parser.add_argument(
        "--exclude",
        nargs="+",
        help="Paths or patterns to exclude from being checked",
        required=False,
        default=EXCLUDE_PATTERNS,
    )
    check_parser.add_argument(
        "--extend-exclude",
        nargs="+",
        help="Paths or patterns to exclude from being checked in addition to patterns excluded by default",
        required=False,
        default=(),
    )
    check_parser.add_argument(
        "--include",
        nargs="+",
        help="Paths or patterns to include in being checked",
        required=False,
        default=INCLUDE_PATTERNS,
    )
    check_parser.add_argument(
        "--extend-include",
        nargs="+",
        help="Paths or patterns to include in being checked in addition to patterns included by default",
        required=False,
        default=(),
    )
    check_parser.add_argument(
        "-d",
        "--debug",
        help="Show debug information such as files analyzed",
        action="store_true",
        required=False,
    )
    format_parser = subparsers.add_parser(
        "format",
        help="Format the code to comply with pep695",
        description="Implement suggestions made by `autopep695 check`",
    )
    format_parser.add_argument(
        "paths",
        nargs="*",
        help="Paths to a directory or a file that contains code using the old type annotation syntax",
        type=Path,
        default=[Path.cwd()],
    )
    format_parser.add_argument(
        "-u",
        "--unsafe",
        required=False,
        action="store_true",
        help="Whether to apply unsafe fixes such as type assignments",
    )
    format_parser.add_argument(
        "-p",
        "--parallel",
        required=False,
        nargs="?",
        default=False,
        const=True,
        type=int,
        help="Whether to process the files in parallel. Specify an integer to set the number of processes used.",
    )
    format_parser.add_argument(
        "--exclude",
        nargs="+",
        help="Paths or patterns to exclude from being formatted",
        required=False,
        default=EXCLUDE_PATTERNS,
    )
    format_parser.add_argument(
        "--extend-exclude",
        nargs="+",
        help="Paths or patterns to exclude from being formatted in addition to patterns excluded by default",
        required=False,
        default=(),
    )
    format_parser.add_argument(
        "--include",
        nargs="+",
        help="Paths or patterns to include in being formatted",
        required=False,
        default=INCLUDE_PATTERNS,
    )
    format_parser.add_argument(
        "--extend-include",
        nargs="+",
        help="Paths or patterns to include in being formatted in addition to patterns included by default",
        required=False,
        default=(),
    )
    format_parser.add_argument(
        "--remove-variance",
        help="If given, removes the variance suffixes in the type parameter names",
        action="store_true",
        required=False,
    )
    format_parser.add_argument(
        "--remove-private",
        help="If given, removes the underscore prefixes in the type parameter names",
        action="store_true",
        required=False,
    )
    format_parser.add_argument(
        "--keep-assignments",
        help="Whether to keep unused type parameter assignments",
        action="store_true",
        required=False,
    )
    format_parser.add_argument(
        "-d",
        "--debug",
        help="Show debug information such as files analyzed",
        action="store_true",
        required=False,
    )
    subparsers.add_parser("info", help="Show information related to the tool")

    args = parser.parse_args()

    just_fix_windows_console()

    if args.subparser is None:
        parser.print_help()

    elif args.subparser == "check":
        init_logging(debug=args.debug, silent=args.silent)
        paths = filter_paths(
            args.paths,
            include=set((*args.include, *args.extend_include)),
            exclude=set((*args.exclude, *args.extend_exclude)),
        )

        try:
            errors = analyzer.check_paths(paths, silent=args.silent)

        except InvalidPath as e:
            logging.error(
                f"The specified path {format_special(e.path)} does not exist."
            )
            sys.exit(1)

        if errors == 0:
            print("All checks passed!")

        else:
            suffix = "s" if errors > 1 else ""
            pronoun = "them" if errors > 1 else "it"
            print(
                f"Found {BOLD}{RED}{errors}{RESET} error{suffix}. Fix {pronoun} using {format_special('autopep695 format', '`')}."
            )
            sys.exit(1)

    elif args.subparser == "format":
        init_logging(debug=args.debug)
        paths = filter_paths(
            args.paths,
            include=set((*args.include, *args.extend_include)),
            exclude=set((*args.exclude, *args.extend_exclude)),
        )
        try:
            analyzer.format_paths(
                paths,
                parallel=args.parallel,
                unsafe=args.unsafe,
                remove_variance=args.remove_variance,
                remove_private=args.remove_private,
                keep_assignments=args.keep_assignments,
            )

        except InvalidPath as e:
            logging.error(
                f"The specified path {format_special(e.path)} does not exist."
            )
            sys.exit(1)

    elif args.subparser == "info":
        import os
        import platform

        path = os.path.abspath(os.path.dirname(__file__))
        py_impl = platform.python_implementation()
        py_ver = platform.python_version()
        py_compiler = platform.python_compiler()
        plat_info = platform.uname()
        print(f"autopep695 {__version__} at {path}")
        print(f"{py_impl} {py_ver} {py_compiler}")
        print(f"{plat_info.system} {plat_info.version} {plat_info.machine}")
