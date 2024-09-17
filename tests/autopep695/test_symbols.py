# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from unittest.mock import Mock
from copy import deepcopy

import libcst as cst
import pytest

from autopep695.symbols import (
    Symbol,
    TypeVarSymbol,
    TypeVarTupleSymbol,
    ParamSpecSymbol,
)

expr = cst.parse_expression


@pytest.fixture()
def symbol():
    class GoodSymbol(Symbol):
        name = "hi"

    return GoodSymbol()


def _gen_symbolmock(sym_name: str):
    class SymbolMock(Mock, Symbol):
        name = sym_name

    return SymbolMock()


@pytest.mark.parametrize(
    "mock, expected",
    [
        (_gen_symbolmock("hi"), True),
        (_gen_symbolmock("a"), False),
        (Mock(), False),
    ],
)
def test_symbol_eq(symbol: Symbol, mock: Symbol, expected: bool) -> None:
    assert (symbol == mock) is expected


def test_symbol_deepcopy(symbol: Symbol) -> None:
    assert id(deepcopy(symbol)) == id(symbol)


def test_symbol_hash(symbol: Symbol) -> None:
    assert hash(symbol) == id(symbol)

    d = {symbol: "a"}
    assert d.get(symbol) == "a"
    assert d.get(_gen_symbolmock("hi")) is None


@pytest.mark.parametrize(
    "object, repr_string",
    [
        (
            TypeVarSymbol("T", [expr("int")], expr("int"), expr("int")),
            "TypeVar(name='T', constraints=(int), bound=int, default=int)",
        ),
        (
            TypeVarSymbol("V", [], None, None),
            "TypeVar(name='V', constraints=(), bound=None, default=None)",
        ),
        (
            TypeVarSymbol(
                "K", [expr("int"), expr("str")], bound=None, default=expr("int")
            ),
            "TypeVar(name='K', constraints=(int, str), bound=None, default=int)",
        ),
        (
            TypeVarSymbol("A", [], expr("t.Any"), None),
            "TypeVar(name='A', constraints=(), bound=t.Any, default=None)",
        ),
    ],
)
def test_TypeVarSymbol_repr(object: TypeVarSymbol, repr_string: str) -> None:
    assert repr(object) == repr_string


@pytest.mark.parametrize(
    "object, repr_string",
    [
        (
            ParamSpecSymbol("P", default=expr("Callable[..., None]")),
            "ParamSpec(name='P', default=Callable[..., None])",
        ),
        (ParamSpecSymbol("A", None), "ParamSpec(name='A', default=None)"),
    ],
)
def test_ParamSpecSymbol_repr(object: ParamSpecSymbol, repr_string: str) -> None:
    assert repr(object) == repr_string


@pytest.mark.parametrize(
    "object, repr_string",
    [
        (
            TypeVarTupleSymbol("Ts", default=expr("Unpack[tuple[T, ...]]")),
            "TypeVarTuple(name='Ts', default=Unpack[tuple[T, ...]])",
        ),
        (TypeVarTupleSymbol("I", None), "TypeVarTuple(name='I', default=None)"),
    ],
)
def test_TypeVarTuple_repr(object: ParamSpecSymbol, repr_string: str) -> None:
    assert repr(object) == repr_string
