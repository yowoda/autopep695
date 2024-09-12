# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import typing as t
from dataclasses import dataclass

import libcst as cst

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

@dataclass(frozen=True, repr=False, eq=False)
class TypeVarSymbol(Symbol):
    name: str
    constraints: list[cst.BaseExpression]
    bound: t.Optional[cst.BaseExpression]
    default: t.Optional[cst.BaseExpression]

    def __repr__(self) -> str:
        empty_module = cst.Module(body=())
        constraints_repr: list[str] = []
        for constraint in self.constraints:
            repr_string = empty_module.code_for_node(constraint)
            constraints_repr.append(repr_string)

        bound_repr = "None"
        default_repr = "None"

        if self.bound is not None:
            bound_repr = empty_module.code_for_node(self.bound)

        if self.default is not None:
            default_repr = empty_module.code_for_node(self.default)

        return f"TypeVar(name={self.name!r}, constraints=({', '.join(constraints_repr)}), bound={bound_repr}, default={default_repr})"


@dataclass(frozen=True, repr=False, eq=False)
class TypeVarTupleSymbol(Symbol):
    name: str
    default: t.Optional[cst.BaseExpression]

@dataclass(frozen=True, repr=False, eq=False)
class ParamSpecSymbol(Symbol):
    name: str
    default: t.Optional[cst.BaseExpression]
