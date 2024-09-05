import argparse
import re
import sys

VERSION_REGEX = re.compile(r"__version__\s*=\s*\"(?P<version>\d+.\d+.\d+)\"")

parser = argparse.ArgumentParser()
parser.add_argument("type", choices=["major", "minor", "patch", "alpha"])
parser.add_argument("increment")

_noop = lambda n: n  # noqa: E731
_increment = lambda n: str(int(n) + 1)  # noqa: E731
_reset = lambda _: "0"  # noqa: E731

ACTIONS = {
    "major": (_increment, _reset, _reset),
    "minor": (_noop, _increment, _reset),
    "patch": (_noop, _noop, _increment),
}


def run(version_type: str, increment: str) -> None:
    with open("pep695/__init__.py") as fp:
        content = fp.read()

    current_version = VERSION_REGEX.search(content)
    if current_version is None:
        raise RuntimeError("Could not find version in __init__ file")

    version = current_version.groupdict()["version"]

    if increment.lower() != "true":
        return

    major, minor, patch = version.split(".")

    actions = ACTIONS[version_type.lower()]
    major, minor, patch = [a(s) for a, s in zip(actions, [major, minor, patch])]

    new_version = f"{major}.{minor}.{patch}"

    updated_file_content = VERSION_REGEX.sub(f'__version__ = "{new_version}"', content)
    with open("pep695/__init__.py", "w") as fp:
        fp.write(updated_file_content)

if __name__ == "__main__":
    args = parser.parse_args()
    run(args.type, args.increment)