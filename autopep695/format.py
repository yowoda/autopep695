# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import functools
import typing as t
from typing_extensions import ParamSpec, Concatenate

import libcst as cst
from libcst import matchers as m

from autopep695.base import (
    BaseVisitor,
    GenericInfo,
    ProtocolInfo,
    TYPE_PARAM_CLASSES,
    Symbol,
    make_clean_name,
)
from autopep695.aliases import get_qualified_name

if t.TYPE_CHECKING:
    from pathlib import Path

_T = t.TypeVar("_T")
_P = ParamSpec("_P")
_ClassT = t.TypeVar("_ClassT", bound="PEP695Formatter")


def unsafe(
    func: t.Callable[Concatenate[_ClassT, _P], _T],
) -> t.Callable[Concatenate[_ClassT, _P], _T]:
    """
    A decorator to mark `leave_*` functions as unsafe.
    The function will only run if the --unsafe flag was passed when running `autopep695 format`
    """

    @functools.wraps(func)
    def inner(self: _ClassT, *args: _P.args, **kwargs: _P.kwargs) -> _T:
        if self.unsafe is False:
            return t.cast(_T, kwargs.get("updated_node") or args[1])

        return func(self, *args, **kwargs)

    return inner


class PEP695Formatter(BaseVisitor):
    def __init__(
        self,
        file_path: Path,
        *,
        unsafe: bool,
        remove_variance: bool,
        remove_private: bool,
    ) -> None:
        self.unsafe = unsafe

        self._remove_variance = remove_variance
        self._remove_private = remove_private

        super().__init__(file_path=file_path)

    def leave_Assign(
        self, original_node: cst.Assign, updated_node: cst.Assign
    ) -> t.Union[cst.RemovalSentinel, cst.Assign]:
        if self._should_ignore_statement(original_node):
            return updated_node

        if self._is_typeparam_assign(original_node):
            return cst.RemoveFromParent()

        return updated_node

    @unsafe
    def leave_AnnAssign(
        self, original_node: cst.AnnAssign, updated_node: cst.AnnAssign
    ) -> t.Union[cst.AnnAssign, cst.TypeAlias]:
        return self.maybe_build_TypeAlias_node(
            original_node,
            updated_node,
            remove_variance=self._remove_variance,
            remove_private=self._remove_private,
        )

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        return self._add_typeparameters(
            original_node,
            updated_node,
            self._new_typevars_for_node[original_node],
            self._new_paramspecs_for_node[original_node],
            self._new_typevartuples_for_node[original_node],
            remove_variance=self._remove_variance,
            remove_private=self._remove_private,
        )

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        return self._add_typeparameters(
            original_node,
            updated_node,
            self._new_typevars_for_node[original_node],
            self._new_paramspecs_for_node[original_node],
            self._new_typevartuples_for_node[original_node],
            remove_variance=self._remove_variance,
            remove_private=self._remove_private,
        )

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        if not (self._remove_variance or self._remove_private):
            return updated_node

        def condition(sym: Symbol) -> bool:
            return self._contains_symbol_name(original_node, sym)

        for param in TYPE_PARAM_CLASSES:
            info = self._type_collection.get(param)
            if self._resolve_symbols_used(info.symbols, predicate=condition):
                return cst.Name(
                    make_clean_name(
                        original_node.value,
                        variance=self._remove_variance,
                        private=self._remove_private,
                    )
                )

        return updated_node

    @m.call_if_inside(
        m.ClassDef(bases=[m.AtLeastN(n=1)])
    )  # Match type subscript in class base
    def leave_Arg(
        self, original_node: cst.Arg, updated_node: cst.Arg
    ) -> t.Union[cst.Arg, cst.RemovalSentinel]:
        if not m.matches(original_node, m.Arg(m.Subscript(m.Attribute() | m.Name()))):
            return updated_node

        subscript = cst.ensure_type(original_node.value, cst.Subscript)

        name = get_qualified_name(subscript.value)

        if name in self._type_collection.get(GenericInfo).aliases:
            for param in TYPE_PARAM_CLASSES:
                if self._resolve_symbols_used(
                    self._type_collection.get(param).symbols,
                    predicate=lambda sym: self._contains_symbol_name(subscript, sym),
                ):
                    return cst.RemoveFromParent()

        if name in self._type_collection.get(ProtocolInfo).aliases:
            for param in TYPE_PARAM_CLASSES:
                if self._resolve_symbols_used(
                    self._type_collection.get(param).symbols,
                    predicate=lambda sym: self._contains_symbol_name(subscript, sym),
                ):
                    return updated_node.with_changes(
                        value=cst.ensure_type(original_node.value, cst.Subscript).value
                    )

        return updated_node
