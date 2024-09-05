import argparse
from pathlib import Path

from pep695 import analyzer, __version__
from pep695.ux import init_logging, RED, RESET, BLUE, BOLD


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
    format_parser = subparsers.add_parser(
        "format",
        help="Format the code to comply with pep695",
        description="Implement suggestions made by `pep695 check`",
    )
    format_parser.add_argument(
        "paths",
        nargs="*",
        help="Paths to a directory or a file that contains code using the old type annotation syntax",
        type=Path,
        default=[Path.cwd()],
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
    subparsers.add_parser("info", help="Show information related to the tool")

    args = parser.parse_args()
    if args.subparser is None:
        parser.print_help()

    elif args.subparser == "check":
        init_logging(silent=args.silent)
        errors = analyzer.check_paths(args.paths, args.silent)
        if errors is None:
            return

        if errors == 0:
            print("All checks passed!")

        else:
            print(
                f"Found {BOLD}{RED}{errors}{RESET} errors. Fix them using `{BOLD}{BLUE}pep695 format{RESET}`."
            )

    elif args.subparser == "format":
        analyzer.format_paths(args.paths, args.parallel)

    elif args.subparser == "info":
        import os
        import platform

        path = os.path.abspath(os.path.dirname(__file__))
        py_impl = platform.python_implementation()
        py_ver = platform.python_version()
        py_compiler = platform.python_compiler()
        plat_info = platform.uname()
        print(f"pep695 {__version__} at {path}")
        print(f"{py_impl} {py_ver} {py_compiler}")
        print(f"{plat_info.system} {plat_info.version} {plat_info.machine}")
