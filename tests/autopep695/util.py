# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


def remove_empty_lines(text: str) -> str:
    lines = text.splitlines()
    return "\n".join(line for line in lines if line.strip())
