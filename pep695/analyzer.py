from __future__ import annotations

import multiprocessing
import os
import platform
import logging
import typing as t

import libcst as cst
from libcst.metadata import PositionProvider

from pep695.check import CheckPEP695Visitor
from pep695.format import PEP695Formatter
from pep695.ux import init_logging, BOLD, RESET, BLUE

if t.TYPE_CHECKING:
    from pathlib import Path


def debug_path_format(path: Path) -> str:
    return f"'{BOLD}{BLUE}{path}{RESET}'"


def _check_valid_paths(paths: t.Iterable[Path]) -> bool:
    for path in paths:
        if not path.exists():
            logging.error(f"The specified path '{path}' does not exist.")
            return False

    return True


def format_code(code: str) -> str:
    tree: cst.Module = cst.parse_module(code)
    transformer = PEP695Formatter()
    new_tree = tree.visit(transformer)

    return new_tree.code


def _format_file(path: Path) -> None:
    logging.debug("Analyzing file %s", debug_path_format(path))
    with open(path, "r+") as f:
        code = format_code(f.read())
        f.seek(0)
        f.write(code)
        f.truncate()


def _format_dir(path: Path) -> None:
    logging.debug("Analyzing directory %s", debug_path_format(path))
    for p in path.iterdir():
        if p.is_dir():
            _format_dir(p)

        if p.is_file() and _has_valid_extension(p):
            _format_file(p)


def _has_valid_extension(path: Path) -> bool:
    return path.suffix in (".py", ".pyi")


def _get_all_files(paths: t.Iterable[Path]) -> t.Iterable[Path]:
    for path in paths:
        if path.is_file() and _has_valid_extension(path):
            yield path

        else:
            yield from (p for p in path.rglob("*") if _has_valid_extension(p))


def _parallel_format_paths(paths: t.Iterable[Path], processes: t.Optional[int]) -> None:
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
        pool.map(_format_file, _get_all_files(paths))


def format_paths(paths: t.Iterable[Path], parallel: t.Union[bool, int]) -> None:
    if not _check_valid_paths(paths):
        return

    if parallel is not False:
        _parallel_format_paths(
            paths=paths, processes=None if parallel is True else parallel
        )
        return

    for path in paths:
        if path.is_file() and _has_valid_extension(path):
            _format_file(path)

        elif path.is_dir():
            _format_dir(path)


def _check_code(code: str, file_path: str, silent: bool) -> int:
    tree: cst.Module = cst.parse_module(code)
    if not silent:
        setattr(CheckPEP695Visitor, "METADATA_DEPENDENCIES", (PositionProvider,))
        tree = cst.MetadataWrapper(tree)  # type: ignore

    transformer = CheckPEP695Visitor(file_path, silent=silent)
    tree.visit(transformer)

    return transformer.errors


def _check_file(path: Path, silent: bool) -> int:
    logging.debug("Analyzing file %s", debug_path_format(path))
    with open(path, "r+") as f:
        return _check_code(f.read(), str(path), silent)


def _check_dir(path: Path, silent: bool) -> int:
    errors = 0
    logging.debug("Analyzing directory %s", debug_path_format(path))
    for p in path.iterdir():
        if p.is_dir():
            errors += _check_dir(p, silent)

        if p.is_file() and _has_valid_extension(p):
            errors += _check_file(p, silent)

    return errors


def check_paths(paths: t.Iterable[Path], silent: bool) -> t.Optional[int]:
    errors = 0
    if not _check_valid_paths(paths):
        return None

    for path in paths:
        if path.is_file() and _has_valid_extension(path):
            errors += _check_file(path, silent)

        elif path.is_dir():
            errors += _check_dir(path, silent)

    return errors
