# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


class ParsingError(Exception):
    """
    Error to raise if libcst fails to parse the given code
    """


class InvalidPath(Exception):
    """
    Error to raise if a path is passed that doesn't point to a valid directory or file
    """

    def __init__(self, path: str) -> None:
        self.path = path


class TypeParamMismatch(Exception):
    """
    Error to raise if variable name and type param constructor name don't match.
    """

    def __init__(self, arg_name: str) -> None:
        self.arg_name = arg_name
