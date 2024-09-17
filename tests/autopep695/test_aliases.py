# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
import pytest

from autopep695.aliases import AliasCollection, get_qualified_name


def test_AliasCollection():
    collection = AliasCollection()
    collection.add_if_not_none(None)
    assert collection == set()

    collection.add_if_not_none("a")
    assert collection == {"a"}


@pytest.mark.parametrize(
    "expression, expected",
    [
        (cst.parse_expression("typing.TypeVar"), "typing.TypeVar"),
        (cst.parse_expression("TypeVar"), "TypeVar"),
        (cst.parse_expression("this.that"), "this.that"),
        (cst.parse_expression("1"), ""),
        (cst.parse_expression("1 .__dir__"), ""),
    ],
)
def test_get_qualified_name(expression: cst.BaseExpression, expected: str):
    assert get_qualified_name(expression) == expected
