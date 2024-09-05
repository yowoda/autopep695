import typing as t

import libcst as cst
from libcst import matchers as m

from pep695.base import BaseVisitor, GenericInfo, ProtocolInfo, _TYPE_PARAM_CLASSES
from pep695.aliases import get_qualified_name

class PEP695Formatter(BaseVisitor):
    def leave_Assign(
        self, original_node: cst.Assign, updated_node: cst.Assign
    ) -> t.Union[cst.RemovalSentinel, cst.Assign]:
        if self._should_ignore_statement(original_node):
            return updated_node

        if isinstance(original_node.value, cst.Call) and self._is_typeparam_assign(
            original_node.value
        ):
            return cst.RemoveFromParent()

        return updated_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        return self._add_typeparameters(
            original_node,
            updated_node,
            self._new_typevars_for_node[original_node],
            self._new_paramspecs_for_node[original_node],
            self._new_typevartuples_for_node[original_node],
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
        )
    
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
            for param in _TYPE_PARAM_CLASSES:
                if self._resolve_symbols_used(
                    self._type_collection.get(param).symbols,
                    predicate=lambda sym: self._contains_symbol_name(subscript, sym)
                ):
                    return cst.RemoveFromParent()

        if name in self._type_collection.get(ProtocolInfo).aliases:
            for param in _TYPE_PARAM_CLASSES:
                if self._resolve_symbols_used(
                    self._type_collection.get(param).symbols,
                    predicate=lambda sym: self._contains_symbol_name(subscript, sym)
                ):
                    return updated_node.with_changes(
                        value=cst.ensure_type(original_node.value, cst.Subscript).value
                    )

        return updated_node
