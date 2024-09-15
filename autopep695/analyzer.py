# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import functools
import multiprocessing
import os
import platform
import logging
import typing as t

import libcst as cst
from libcst.metadata import PositionProvider

from autopep695.check import CheckPEP695Visitor
from autopep695.format import PEP695Formatter
from autopep695.ux import init_logging, format_special
from autopep695.errors import ParsingError
from autopep695.base import RemoveAssignments

if t.TYPE_CHECKING:
    from pathlib import Path


def _show_debug_traceback_note():
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        return ""

    return f"View the full traceback by passing the {format_special('--debug', '`')} flag\n"


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
            logging.error(
                f"Internal error while formatting code in {format_special(path)}\n{_show_debug_traceback_note()}"
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


def _check_code(code: str, *, file_path: Path, silent: bool) -> int:
    tree = _file_aware_parse_code(code, file_path)
    if not silent:
        setattr(CheckPEP695Visitor, "METADATA_DEPENDENCIES", (PositionProvider,))
        tree = cst.MetadataWrapper(tree)  # type: ignore

    transformer = CheckPEP695Visitor(file_path, silent=silent)
    tree.visit(transformer)

    return transformer.errors


def _check_file(path: Path, *, silent: bool) -> int:
    logging.debug("Analyzing file %s", format_special(path))
    try:
        return _check_code(
            path.read_text(encoding="utf-8"), file_path=path, silent=silent
        )

    except ParsingError:
        return 0

    except Exception as e:
        logging.error(
            f"Internal error while checking code in {format_special(path)}\n{_show_debug_traceback_note()}"
        )
        logging.debug("Full traceback for the error above:", exc_info=e)
        return 0


def check_paths(paths: t.Iterable[Path], *, silent: bool) -> int:
    return sum(_check_file(p, silent=silent) for p in paths)
