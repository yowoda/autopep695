# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import typing as t
from typing_extensions import Self
from dataclasses import dataclass

import libcst as cst

from autopep695.helpers import get_code

__all__: t.Sequence[str] = (
    "Symbol",
    "TypeVarSymbol",
    "ParamSpecSymbol",
    "TypeVarTupleSymbol",
)


@t.runtime_checkable
class Symbol(t.Protocol):
    name: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Symbol):
            return False

        return self.name == other.name

    def __deepcopy__(self, memo: object) -> Self:
        """
        Return self as the instance is practically immutable
        """
        return self

    def __hash__(self) -> int:
        """
        The data for a symbol is practically immutable which is why
        it should be fine to implement an "unsafe" hash
        """
        return id(self)


@dataclass(frozen=True, repr=False, eq=False)
class TypeVarSymbol(Symbol):
    name: str
    constraints: list[cst.BaseExpression]
    bound: t.Optional[cst.BaseExpression]
    default: t.Optional[cst.BaseExpression]

    def __repr__(self) -> str:
        bound_repr = get_code(self.bound) if self.bound else "None"
        default_repr = get_code(self.default) if self.default else "None"

        return f"TypeVar(name={self.name!r}, constraints=({get_code(*self.constraints)}), bound={bound_repr}, default={default_repr})"


@dataclass(frozen=True, repr=False, eq=False)
class TypeVarTupleSymbol(Symbol):
    name: str
    default: t.Optional[cst.BaseExpression]

    def __repr__(self) -> str:
        default_repr = get_code(self.default) if self.default else "None"

        return f"TypeVarTuple(name={self.name!r}, default={default_repr})"


@dataclass(frozen=True, repr=False, eq=False)
class ParamSpecSymbol(Symbol):
    name: str
    default: t.Optional[cst.BaseExpression]

    def __repr__(self) -> str:
        default_repr = get_code(self.default) if self.default else "None"

        return f"ParamSpec(name={self.name!r}, default={default_repr})"
