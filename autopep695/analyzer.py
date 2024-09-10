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

if t.TYPE_CHECKING:
    from pathlib import Path


def _check_valid_paths(paths: t.Iterable[Path]) -> bool:
    for path in paths:
        if not path.exists():
            logging.error(f"The specified path {format_special(path)} does not exist.")
            return False

    return True


def _file_aware_parse_code(code: str, path: Path) -> cst.Module:
    try:
        tree = cst.parse_module(code)

    except Exception as e:
        logging.error(f"Failed parsing code from {format_special(path)}\n{e}")
        logging.debug("Full Traceback for the error above:", exc_info=e)
        raise ParsingError

    return tree


def format_code(code: str, *, file_path: Path, unsafe: bool) -> str:
    tree = _file_aware_parse_code(code, file_path)
    transformer = PEP695Formatter(file_path, unsafe=unsafe)
    new_tree = tree.visit(transformer)

    return new_tree.code


def _format_file(path: Path, *, unsafe: bool) -> None:
    logging.debug("Analyzing file %s", format_special(path))
    with path.open("r+", encoding="utf-8") as f:
        try:
            code = format_code(f.read(), file_path=path, unsafe=unsafe)

        except ParsingError:  # catch the exception so the file can be skipped and the whole process isn't terminated
            return

        f.seek(0)
        f.write(code)
        f.truncate()


def _format_dir(path: Path, *, unsafe: bool) -> None:
    logging.debug("Analyzing directory %s", format_special(path))
    for p in path.iterdir():
        if p.is_dir():
            _format_dir(p, unsafe=unsafe)

        if p.is_file() and _has_valid_extension(p):
            _format_file(p, unsafe=unsafe)


def _has_valid_extension(path: Path) -> bool:
    return path.suffix in (".py", ".pyi")


def _get_all_files(paths: t.Iterable[Path]) -> t.Iterable[Path]:
    for path in paths:
        if path.is_file() and _has_valid_extension(path):
            yield path

        else:
            yield from (p for p in path.rglob("*") if _has_valid_extension(p))


def _format_file_wrapper(unsafe: bool, path: Path) -> None:
    """
    A `_format_file` wrapper that modifes the order of arguments.
    This is neccessary because pool.map can only pass one argument to the mapped function
    which in this case is the path to the file, so other arguments need to be passed
    using functools.partial
    """
    return _format_file(path, unsafe=unsafe)


def _parallel_format_paths(
    paths: t.Iterable[Path], *, processes: t.Optional[int], unsafe: bool
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
            functools.partial(_format_file_wrapper, unsafe=unsafe),
            _get_all_files(paths),
        )


def format_paths(
    paths: t.Iterable[Path], *, parallel: t.Union[bool, int], unsafe: bool
) -> None:
    if not _check_valid_paths(paths):
        return

    if parallel is not False:
        _parallel_format_paths(
            paths=paths, processes=None if parallel is True else parallel, unsafe=unsafe
        )
        return

    for path in paths:
        if path.is_file() and _has_valid_extension(path):
            _format_file(path, unsafe=unsafe)

        elif path.is_dir():
            _format_dir(path, unsafe=unsafe)


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


def _check_dir(path: Path, *, silent: bool) -> int:
    errors = 0
    logging.debug("Analyzing directory %s", format_special(path))
    for p in path.iterdir():
        if p.is_dir():
            errors += _check_dir(p, silent=silent)

        if p.is_file() and _has_valid_extension(p):
            errors += _check_file(p, silent=silent)

    return errors


def check_paths(paths: t.Iterable[Path], *, silent: bool) -> t.Optional[int]:
    errors = 0
    if not _check_valid_paths(paths):
        return None

    for path in paths:
        if path.is_file() and _has_valid_extension(path):
            errors += _check_file(path, silent=silent)

        elif path.is_dir():
            errors += _check_dir(path, silent=silent)

    return errors
