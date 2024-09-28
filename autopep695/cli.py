# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import argparse
import logging
import sys
import textwrap
import typing as t
from pathlib import Path
from collections import Counter
from contextlib import contextmanager

from colorama import just_fix_windows_console

from autopep695 import analyzer
from autopep695.ux import (
    init_logging,
    RED,
    RESET,
    BOLD,
    GREEN,
    format_special,
    get_system_info,
    format_error_count,
    format_success_count,
)
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


class _StdinFileWrapper:
    def read(self, *args: t.Any, **kwargs: t.Any) -> str:
        return sys.stdin.read()

    def write(self, s: str) -> None:
        print(s)

    def seek(self, *args: t.Any, **kwargs: t.Any): ...
    def truncate(self, *args: t.Any, **kwargs: t.Any): ...


class _StdinPathWrapper:
    def read_text(self, *args: t.Any, **kwargs: t.Any) -> str:
        return sys.stdin.read()

    def __repr__(self) -> str:
        return "STDIN"

    @contextmanager
    def open(self, *args: t.Any, **kwargs: t.Any) -> t.Iterator[_StdinFileWrapper]:
        yield _StdinFileWrapper()


def filter_paths(
    paths: t.Iterable[Path], include: t.Iterable[str], exclude: t.Iterable[str]
) -> t.Iterable[Path]:
    for path in paths:
        if repr(path) == "STDIN":
            yield path
            continue

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
        default=[],
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
        default=[],
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

    stdin_path: t.Optional[Path] = (
        None if sys.stdin.isatty() else t.cast(Path, _StdinPathWrapper())
    )

    if args.subparser is None:
        parser.print_help()

    if args.subparser in ("check", "format"):
        if not args.paths and stdin_path is None:
            args.paths = [Path.cwd()]

        elif stdin_path is not None:
            args.paths.append(stdin_path)

    if args.subparser == "check":
        init_logging(debug=args.debug, silent=args.silent)
        paths = filter_paths(
            args.paths,
            include=set((*args.include, *args.extend_include)),
            exclude=set((*args.exclude, *args.extend_exclude)),
        )

        try:
            diagnostics = analyzer.check_paths(paths, silent=args.silent)

        except InvalidPath as e:
            logging.error(
                f"The specified path {format_special(e.path)} does not exist."
            )
            sys.exit(1)

        counter = Counter(d.status for d in diagnostics)
        successful_files = counter[analyzer.FileStatus.SUCCESS]
        failed_files = counter[analyzer.FileStatus.FAILED]
        unparsable_files = counter[analyzer.FileStatus.PARSING_ERROR]
        internal_error_files = counter[analyzer.FileStatus.INTERNAL_ERROR]

        if len(diagnostics) == successful_files:
            print(f"{BOLD}{GREEN}All checks passed!{RESET}")

        else:
            errors = sum(len(d.errors) + d.silent_errors for d in diagnostics)
            suffix = "s" if errors != 1 else ""
            pronoun = "them" if errors != 1 else "it"
            files_report = (
                f"Files that were successful: {format_success_count(successful_files)}\n"
                f"Files that did not conform to PEP 695: {format_error_count(failed_files)}\n"
                f"Files that triggered internal errors: {format_error_count(internal_error_files)}\n"
                f"Files that could not be parsed: {format_error_count(unparsable_files)}\n"
                f"Found {BOLD}{format_error_count(errors)} PEP 695-related error{suffix}."
            )
            if errors > 0:
                files_report += (
                    f" Fix {pronoun} using {format_special('autopep695 format', '`')}."
                )

            print(f"{BOLD}{RED}Check was not successful:{RESET}")
            print(textwrap.indent(files_report, " " * 2))
            sys.exit(1)

    if args.subparser == "format":
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
        print(get_system_info())
