# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import enum
import functools
import multiprocessing
import os
import platform
import logging
import traceback
import typing as t
from urllib.parse import urlencode
from dataclasses import dataclass

import libcst as cst
from libcst.metadata import PositionProvider

from autopep695.check import CheckPEP695Visitor, Diagnostic
from autopep695.format import PEP695Formatter
from autopep695.ux import (
    init_logging,
    format_special,
    create_hyperlink,
    get_system_info,
)
from autopep695.errors import ParsingError
from autopep695.base import RemoveAssignments

if t.TYPE_CHECKING:
    from pathlib import Path


class FileStatus(enum.Enum):
    SUCCESS = enum.auto()
    """All PEP 695 checks passed"""
    FAILED = enum.auto()
    """The file does not conform to PEP 695"""
    INTERNAL_ERROR = enum.auto()
    """There was an internal error while processing the file"""
    PARSING_ERROR = enum.auto()
    """The file could not be parsed"""


@dataclass
class FileDiagnostic:
    status: FileStatus
    errors: list[Diagnostic]
    silent_errors: int


def _show_debug_traceback_note() -> str:
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        return ""

    return f"View the full traceback by passing the {format_special('--debug', '`')} flag\n"


def _show_internal_error_report_note(
    *, title: str, command: str, settings: dict[str, t.Any]
) -> str:
    settings_repr = "\n".join(f"{name}={value}" for name, value in settings.items())
    params = urlencode(
        {
            "title": title,
            "reproduction-steps": f"Run `{command}` with:\n```\n{settings_repr}\n```",
            "expected-result": "The command works or an informative error is shown.",
            "actual-result": f"Internal error:\n```\n{traceback.format_exc()}```",
            "system-info": get_system_info(),
        }
    )
    link = f"https://github.com/yowoda/autopep695/issues/new?assignees=&labels=bug&projects=&template=bug_report.yml&{params}"
    return f"Please report this issue on {create_hyperlink(link, 'Github')}."


def _file_aware_parse_code(code: str, path: Path) -> cst.Module:
    try:
        tree = cst.parse_module(code)

    except Exception as e:
        logging.error(
            f"Failed parsing code from {format_special(path)}\n{e}\n{_show_debug_traceback_note()}"
        )
        logging.debug("Full Traceback for the error above:", exc_info=e)
        raise ParsingError

    return tree


def format_code(
    code: str,
    *,
    file_path: Path,
    unsafe: bool,
    remove_variance: bool,
    remove_private: bool,
    keep_assignments: bool,
) -> str:
    """
    Format `code` according to the PEP 695 specification. `file_path` is not validated, which means it does not have
    to represent an existing file in case you're just formatting a string of code. `unsafe`, `remove_variance`, `remove_private`
    and `keep_assignments` have the same effect as in the command-line.
    """
    tree = _file_aware_parse_code(code, file_path)
    transformer = PEP695Formatter(
        file_path,
        unsafe=unsafe,
        remove_variance=remove_variance,
        remove_private=remove_private,
    )
    new_tree = tree.visit(transformer)
    if not keep_assignments:
        new_tree = new_tree.visit(
            RemoveAssignments(set(transformer.unused_assignments.values()))
        )

    return new_tree.code


def _format_file(
    path: Path,
    *,
    unsafe: bool,
    remove_variance: bool,
    remove_private: bool,
    keep_assignments: bool,
) -> None:
    logging.debug("Analyzing file %s", format_special(path))
    with path.open("r+", encoding="utf-8") as f:
        try:
            code = format_code(
                f.read(),
                file_path=path,
                unsafe=unsafe,
                remove_variance=remove_variance,
                remove_private=remove_private,
                keep_assignments=keep_assignments,
            )

        except ParsingError:  # catch the exception so the file can be skipped and the whole process isn't terminated
            return

        except Exception as e:
            github_report_note = _show_internal_error_report_note(
                title="Internal error while formatting code",
                command="autopep695 format",
                settings={
                    "unsafe": unsafe,
                    "remove_variance": remove_variance,
                    "remove_private": remove_private,
                    "keep_assignments": keep_assignments,
                },
            )
            logging.error(
                f"Internal error while formatting code in {format_special(path)}\n{github_report_note}\n{_show_debug_traceback_note()}"
            )
            logging.debug("Full traceback for the error above:", exc_info=e)
            return

        f.seek(0)
        f.write(code)
        f.truncate()


def _format_file_wrapper(
    unsafe: bool,
    remove_variance: bool,
    remove_private: bool,
    keep_assignments: bool,
    path: Path,
) -> None:
    """
    A `_format_file` wrapper that modifes the order of arguments.
    This is neccessary because pool.map can only pass one argument to the mapped function
    which in this case is the path to the file, so other arguments need to be passed
    using functools.partial
    """
    return _format_file(
        path,
        unsafe=unsafe,
        remove_variance=remove_variance,
        remove_private=remove_private,
        keep_assignments=keep_assignments,
    )


def _parallel_format_paths(
    paths: t.Iterable[Path],
    *,
    processes: t.Optional[int],
    unsafe: bool,
    remove_variance: bool,
    remove_private: bool,
    keep_assignments: bool,
) -> None:
    if processes is None:
        processes = os.cpu_count() or 1

    _has_debug = logging.getLogger().isEnabledFor(logging.DEBUG)

    # on Windows and macOS,subprocesses are created using `spawn`, starting a new python interpreter
    # for each worker. Unlike `fork`, the interpreter process doesn't inherit the logging config from
    # the main process, which is why need to pass a `init_logging` wrapper to the initializer arg of the pool,
    # so the logging config is set for each worker

    if platform.system() in ("Windows", "Darwin"):
        initializer = init_logging
        initargs = (_has_debug,)

    else:
        initializer = None
        initargs = ()

    with multiprocessing.Pool(
        processes, initializer=initializer, initargs=initargs
    ) as pool:
        logging.debug("Run with --parallel, Starting %s processes...", processes)
        pool.map(
            functools.partial(
                _format_file_wrapper,
                unsafe,
                remove_variance,
                remove_private,
                keep_assignments,
            ),
            paths,
        )


def format_paths(
    paths: t.Iterable[Path],
    *,
    parallel: t.Union[bool, int],
    unsafe: bool,
    remove_variance: bool,
    remove_private: bool,
    keep_assignments: bool,
) -> None:
    if parallel is not False:
        _parallel_format_paths(
            paths=paths,
            processes=None if parallel is True else parallel,
            unsafe=unsafe,
            remove_variance=remove_variance,
            remove_private=remove_private,
            keep_assignments=keep_assignments,
        )

    else:
        for path in paths:
            _format_file(
                path,
                unsafe=unsafe,
                remove_variance=remove_variance,
                remove_private=remove_private,
                keep_assignments=keep_assignments,
            )


def check_code(
    code: str, *, file_path: Path, silent: bool
) -> tuple[list[Diagnostic], int]:
    """
    Check whether `code` conforms to autopep695. `file_path` is used purely for formatting diagnostics,
    whether it points to a valid file or not is not checked, so you may leave out the semantic value of this parameter
    if you only want to check the given code string. `silent` will have the same effect as in the command-line

    Returns a tuple of length 2, the first element being the list of `Diagnostic` objects and the second element being
    the number of silent errors.
    """
    tree = _file_aware_parse_code(code, file_path)
    if not silent:
        setattr(CheckPEP695Visitor, "METADATA_DEPENDENCIES", (PositionProvider,))
        tree = cst.MetadataWrapper(tree)  # type: ignore

    transformer = CheckPEP695Visitor(file_path, silent=silent)
    tree.visit(transformer)

    return transformer.diagnostics, transformer.silent_errors


def _check_file(path: Path, *, silent: bool) -> FileDiagnostic:
    logging.debug("Analyzing file %s", format_special(path))
    try:
        errors, silent_errors = check_code(
            path.read_text(encoding="utf-8"), file_path=path, silent=silent
        )

    except ParsingError:
        return FileDiagnostic(FileStatus.PARSING_ERROR, [], 0)

    except Exception as e:
        github_report_note = _show_internal_error_report_note(
            title="Internal error while checking code",
            command="autopep695 check",
            settings={"silent": silent},
        )
        logging.error(
            f"Internal error while checking code in {format_special(path)}\n{github_report_note}\n{_show_debug_traceback_note()}"
        )
        logging.debug("Full traceback for the error above:", exc_info=e)
        return FileDiagnostic(FileStatus.INTERNAL_ERROR, [], 0)

    else:
        status = (
            FileStatus.FAILED if (errors or silent_errors > 0) else FileStatus.SUCCESS
        )
        return FileDiagnostic(status, errors, silent_errors)


def check_paths(paths: t.Iterable[Path], *, silent: bool) -> list[FileDiagnostic]:
    return [_check_file(p, silent=silent) for p in paths]
