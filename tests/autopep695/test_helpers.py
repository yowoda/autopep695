# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
import pytest

from autopep695.helpers import ensure_type, make_clean_name, get_code

expr = cst.parse_expression


def test_ensure_type():
    assert ensure_type(5, int, str) == 5
    assert ensure_type(7.2, float) == 7.2

    with pytest.raises(
        TypeError, match="Expected object of type 'str | bool', got type 'int'"
    ):
        assert ensure_type(5, str, bool)

    with pytest.raises(
        TypeError, match="Expected object of type 'int', got type 'str'"
    ):
        assert ensure_type("a", int)


def test_make_clean_name() -> None:
    assert make_clean_name("T", variance=True, private=True) == "T"
    assert make_clean_name("T_co", variance=True, private=False) == "T"
    assert make_clean_name("T_contra", variance=True, private=False) == "T"
    assert make_clean_name("_T", variance=False, private=True) == "T"
    assert make_clean_name("__T", variance=False, private=True) == "T"
    assert make_clean_name("__T_co", variance=True, private=True) == "T"
    assert make_clean_name("__T_co", variance=True, private=False) == "__T"
    assert make_clean_name("__T_co", variance=False, private=True) == "T_co"
    assert make_clean_name("__T_co", variance=False, private=False) == "__T_co"


def test_get_code() -> None:
    code = "1 + 1"
    assert get_code(expr(code)) == code
    assert (
        get_code(cst.parse_expression(code), cst.parse_expression(code))
        == f"{code}, {code}"
    )
