# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import typing as t

import libcst as cst

from autopep695.base import (
    BaseVisitor,
    ClassTypeParamCollection,
    FunctionTypeParamCollection,
    ClassBaseArgTransformer,
    CleanNameTransformer,
)
from autopep695.helpers import ensure_type

if t.TYPE_CHECKING:
    from pathlib import Path


class PEP695Formatter(BaseVisitor):
    def __init__(
        self,
        file_path: Path,
        *,
        unsafe: bool,
        remove_variance: bool,
        remove_private: bool,
    ) -> None:
        self._unsafe = unsafe

        self._remove_variance = remove_variance
        self._remove_private = remove_private

        super().__init__(file_path=file_path)

    def leave_AnnAssign(
        self, original_node: cst.AnnAssign, updated_node: cst.AnnAssign
    ) -> t.Union[cst.AnnAssign, cst.TypeAlias]:
        return self.process_TypeAlias_node(
            original_node,
            updated_node,
            remove_variance=self._remove_variance,
            remove_private=self._remove_private,
            ignore=(not self._unsafe or self.should_ignore_assign(original_node)),
        )

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        node = ensure_type(self.current_node, FunctionTypeParamCollection)
        type_collection = self.current_typecollection

        super().leave_FunctionDef(original_node, updated_node)

        if not any((node.typevars_used, node.paramspecs_used, node.typevartuples_used)):
            return updated_node

        updated_node = ensure_type(
            updated_node.visit(
                CleanNameTransformer(
                    type_collection, self._remove_variance, self._remove_private
                )
            ),
            cst.FunctionDef,
        )
        return self.add_typeparameters(
            updated_node,
            updated_node,
            node.typevars_used,
            node.paramspecs_used,
            node.typevartuples_used,
            remove_variance=self._remove_variance,
            remove_private=self._remove_private,
        )

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        node = ensure_type(self.current_node, ClassTypeParamCollection)
        type_collection = self.current_typecollection

        super().leave_ClassDef(original_node, updated_node)

        if not any((node.typevars_used, node.paramspecs_used, node.typevartuples_used)):
            return updated_node

        bases: list[t.Union[cst.Arg, cst.FlattenSentinel[cst.Arg]]] = []
        for base in original_node.bases:
            new_base = base.visit(ClassBaseArgTransformer(type_collection))
            if not isinstance(new_base, cst.RemovalSentinel):
                bases.append(new_base)

        updated_node = updated_node.with_changes(bases=bases)
        updated_node = ensure_type(
            updated_node.visit(
                CleanNameTransformer(
                    type_collection, self._remove_variance, self._remove_private
                )
            ),
            cst.ClassDef,
        )
        return self.add_typeparameters(
            updated_node,
            updated_node,
            node.typevars_used,
            node.paramspecs_used,
            node.typevartuples_used,
            remove_variance=self._remove_variance,
            remove_private=self._remove_private,
        )
