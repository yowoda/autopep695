# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import argparse
import subprocess
import sys

from pathlib import Path

COPYRIGHT = "\n".join(
    line for line in Path(__file__).read_text().splitlines()[:4]
)

parser = argparse.ArgumentParser("Copyright analysis")
parser.add_argument(
    "-f", "--fix",
    action="store_true",
    required=False,
    help="Whether to place a short copyright notice at the start of each file"
)

args = parser.parse_args()

output = subprocess.run(
    ["git", "ls-tree", "-r", "--name-only", "HEAD"],
    check=True,
    capture_output=True,
    encoding="utf-8",
)
paths = (
    path
    for line in output.stdout.splitlines()
    if (path := Path(line)) if path.is_file() and path.suffix == ".py"
)

error = 0
for path in paths:
    with path.open("r+") as f:
        text = f.read()

        if COPYRIGHT in text:
            continue

        print(f"{path} is missing copyright")

        if args.fix:
            f.seek(0)
            f.write(COPYRIGHT + "\n\n" + text)
            f.truncate()

            print(f"Fixed {path}")

        else:
            error = 1

sys.exit(error)