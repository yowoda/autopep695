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


class Symbol(t.Protocol):
    name: str


@dataclass(frozen=True, repr=False)
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

        if self.bound is not None:
            bound_repr = empty_module.code_for_node(self.bound)

        return f"TypeVar(name={self.name!r}, constraints=({', '.join(constraints_repr)}), bound={bound_repr})"


@dataclass(frozen=True, repr=False)
class TypeVarTupleSymbol(Symbol):
    name: str
    default: t.Optional[cst.BaseExpression]


@dataclass(frozen=True, repr=False)
class ParamSpecSymbol(Symbol):
    name: str
    default: t.Optional[cst.BaseExpression]
