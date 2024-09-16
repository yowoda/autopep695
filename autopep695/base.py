# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import abc
from dataclasses import dataclass, field
import inspect
import logging
from copy import deepcopy

import typing as t

import libcst as cst
from libcst import matchers as m

from autopep695.symbols import (
    Symbol,
    TypeVarSymbol,
    ParamSpecSymbol,
    TypeVarTupleSymbol,
)
from autopep695.aliases import AliasCollection, get_qualified_name
from autopep695.ux import format_special
from autopep695.errors import TypeParamMismatch
from autopep695.helpers import ensure_type, make_clean_name

if t.TYPE_CHECKING:
    from pathlib import Path


class TypeParamAware(t.Protocol):
    """
    A protocol that represents a node that supports pep695-like type
    parameters.
    """

    @property
    def type_parameters(self) -> t.Optional[cst.TypeParameters]: ...

    def with_changes(
        self, *args: t.Any, type_parameters: cst.TypeParameters, **kwargs: t.Any
    ) -> TypeParamAware: ...


_SupportsTypeParameterT = t.TypeVar("_SupportsTypeParameterT", bound=TypeParamAware)
_SymbolT = t.TypeVar("_SymbolT", bound=Symbol)
_IGNORE_COMMENTS_RULES: t.Final[t.Sequence[str]] = ("pep695-ignore",)


def _get_args_kwargs(
    args: t.Sequence[cst.Arg],
) -> tuple[list[cst.BaseExpression], dict[str, cst.BaseExpression]]:
    parsed_args: list[cst.BaseExpression] = []
    parsed_kwargs: dict[str, cst.BaseExpression] = {}

    for argument in args:
        if argument.keyword is None:
            parsed_args.append(argument.value)

        else:
            parsed_kwargs[argument.keyword.value] = argument.value

    return parsed_args, parsed_kwargs


_typing_class_info_collection: list[type[TypingClassInfo]] = []


@dataclass
class TypingClassInfo:
    """
    The base class for collecting information about the usage of a `typing.X` or `typing_extensions.X` name.
    """

    name: str = field(init=False)
    """The original name to collect information about e.g. `TypeVar` or `TypeAlias`"""
    aliases: AliasCollection = field(default_factory=AliasCollection)
    """
    Aliases for this name. Currently an alias can only be made from an import statement e.g.
    import typing as t
    from typing_extensions import ParamSpec

    Creates the following aliases for `ParamSpec`: `t.ParamSpec`, `ParamSpec`.
    """

    def __init_subclass__(cls) -> None:
        if not inspect.isabstract(cls):
            _typing_class_info_collection.append(cls)


@dataclass
class TypingParameterClassInfo(t.Generic[_SymbolT], TypingClassInfo, abc.ABC):
    symbols: dict[str, _SymbolT] = field(default_factory=dict)
    """
    A mapping of symbol name to symbol instance. Example for `TypeVar`:
    import typing as t

    T = t.TypeVar("T")
    R = t.TypeVar("R")

    creates the following mapping for this module (unused TypeVar args/kwargs are left out):
    {"T": TypeVarSymbol("T"), "R": TypeVarSymbol("R")}
    """

    @abc.abstractmethod
    def build(
        self, symbol: _SymbolT, *, remove_variance: bool, remove_private: bool
    ) -> cst.TypeParam:
        """Build and return the node from a given symbol"""

    @abc.abstractmethod
    def build_symbol_from_assignment(
        self, name: str, arguments: t.Sequence[cst.Arg]
    ) -> _SymbolT:
        """
        Build a symbol from the a type parameter assignment, where `name` is variable name
        and `arguments` the list of arguments that are passed to the type param constructor.
        Raises TypeParamMismatch if the `name` and the name passed in the list of arguments don't match.
        """


class TypeVarInfo(TypingParameterClassInfo[TypeVarSymbol]):
    name = "TypeVar"

    def build(
        self, symbol: TypeVarSymbol, *, remove_variance: bool, remove_private: bool
    ) -> cst.TypeParam:
        bound = symbol.bound
        if bound is None and symbol.constraints:
            elements: list[cst.Element] = []
            for constraint in symbol.constraints:
                elements.append(cst.Element(value=constraint))

            bound = cst.Tuple(elements)

        name = make_clean_name(
            symbol.name, variance=remove_variance, private=remove_private
        )

        return cst.TypeParam(
            param=cst.TypeVar(name=cst.Name(value=name), bound=bound),
            default=symbol.default,
        )

    def build_symbol_from_assignment(
        self, name: str, arguments: t.Sequence[cst.Arg]
    ) -> TypeVarSymbol:
        args, kwargs = _get_args_kwargs(arguments)
        arg_name = cst.ensure_type(args[0], cst.SimpleString).raw_value
        if arg_name != name:
            raise TypeParamMismatch(arg_name)

        constraints: list[cst.BaseExpression] = [] if len(args) == 1 else args[1:]
        return TypeVarSymbol(
            name=name,
            constraints=constraints,
            bound=kwargs.get("bound"),
            default=kwargs.get("default"),
        )


class ParamSpecInfo(TypingParameterClassInfo[ParamSpecSymbol]):
    name = "ParamSpec"

    def build(
        self, symbol: ParamSpecSymbol, *, remove_variance: bool, remove_private: bool
    ) -> cst.TypeParam:
        name = make_clean_name(
            symbol.name, variance=remove_variance, private=remove_private
        )

        return cst.TypeParam(
            param=cst.ParamSpec(name=cst.Name(value=name)),
            default=symbol.default,
        )

    def build_symbol_from_assignment(
        self, name: str, arguments: t.Sequence[cst.Arg]
    ) -> ParamSpecSymbol:
        args, kwargs = _get_args_kwargs(arguments)
        arg_name = cst.ensure_type(args[0], cst.SimpleString).raw_value
        if arg_name != name:
            raise TypeParamMismatch(arg_name)

        return ParamSpecSymbol(
            name=name,
            default=kwargs.get("default"),
        )


class TypeVarTupleInfo(TypingParameterClassInfo[TypeVarTupleSymbol]):
    name = "TypeVarTuple"

    def build(
        self, symbol: TypeVarTupleSymbol, *, remove_variance: bool, remove_private: bool
    ) -> cst.TypeParam:
        name = make_clean_name(
            symbol.name, variance=remove_variance, private=remove_private
        )

        return cst.TypeParam(
            param=cst.TypeVarTuple(name=cst.Name(value=name)),
            default=symbol.default,
        )

    def build_symbol_from_assignment(
        self, name: str, arguments: t.Sequence[cst.Arg]
    ) -> TypeVarTupleSymbol:
        args, kwargs = _get_args_kwargs(arguments)
        arg_name = cst.ensure_type(args[0], cst.SimpleString).raw_value
        if arg_name != name:
            raise TypeParamMismatch(arg_name)

        return TypeVarTupleSymbol(
            name=name,
            default=kwargs.get("default"),
        )


class GenericInfo(TypingClassInfo):
    name = "Generic"


class TypeAliasInfo(TypingClassInfo):
    name = "TypeAlias"


class ProtocolInfo(TypingClassInfo):
    name = "Protocol"


TYPE_PARAM_CLASSES = t.cast(
    t.Sequence[type[TypingParameterClassInfo[Symbol]]],
    (TypeVarInfo, ParamSpecInfo, TypeVarTupleInfo),
)


class TypeClassCollection:
    """
    A manager for all `TypingClassInfo` instances in a module:
    """

    __slots__: t.Sequence[str] = ("_data",)

    def __init__(
        self, data: t.Optional[dict[type[TypingClassInfo], TypingClassInfo]] = None
    ) -> None:
        self._data: dict[type[TypingClassInfo], TypingClassInfo] = data or {
            cls: cls() for cls in _typing_class_info_collection
        }

    @property
    def data(self) -> dict[type[TypingClassInfo], TypingClassInfo]:
        return self._data

    @t.overload
    def get(
        self, cls: type[TypingParameterClassInfo[_SymbolT]]
    ) -> TypingParameterClassInfo[_SymbolT]: ...

    @t.overload
    def get(self, cls: type[TypingClassInfo]) -> TypingClassInfo: ...

    @t.no_type_check
    def get(self, cls):
        return self._data[cls]

    def update_aliases(self, namespace: str = "") -> None:
        """
        Update aliases for all managed names.
        namespace is an empty string if a star import has been made e.g.
        from typing import * or from typing_extensions import *

        namespace is not empty if a simple `import` statement was used e.g.
        import typing -> namespace=typing, import typing as t -> namespace=t, import typing_extensions as A -> namespace=A
        """
        if namespace != "":
            namespace += "."

        for cls, info in self._data.items():
            info.aliases.add(f"{namespace}{cls.name}")

    def update_aliases_from_import_info(self, import_info: dict[str, str]) -> None:
        """
        Update aliases given a mapping of the original import name to the alias.
        This happens if you import a specific name from `typing` or `typing_extensions` e.g.:
        from typing import Mapping

        If import_info = {"Mapping": "Mapping", "TypeVar": "T"} then this will add the alias "T" to the `TypeVarInfo` instance
        """
        for cls, info in self._data.items():
            info.aliases.add_if_not_none(import_info.get(cls.name))


@dataclass
class TypeParamCollection(t.Generic[_SupportsTypeParameterT], abc.ABC):
    """
    A class that manages type parameters for any node that supports pep695-like type parameters
    """

    node: _SupportsTypeParameterT
    typevars_used: list[TypeVarSymbol] = field(default_factory=list)
    paramspecs_used: list[ParamSpecSymbol] = field(default_factory=list)
    typevartuples_used: list[TypeVarTupleSymbol] = field(default_factory=list)

    pep695_typeparameters: list[str] = field(init=False, default_factory=list)

    def __post_init__(self):
        if self.node.type_parameters is None:
            return

        names = t.cast(
            t.Sequence[cst.Name], m.findall(self.node.type_parameters, m.Name())
        )
        self.pep695_typeparameters = [name.value for name in names]


class ClassTypeParamCollection(TypeParamCollection[cst.ClassDef]):
    """
    Stores type parameters used in a python class
    """


class FunctionTypeParamCollection(TypeParamCollection[cst.FunctionDef]):
    """
    Stores type parameters used in a python function
    """


class ScopeContainer:
    """
    A container that stores one of the following scopes:
    - module-level:     cst.Module, any type parameter assignments that happened at module level which is the most common

    - class-level:      cst.ClassDef, any type parameter assignments that happened within
                        a class and are only available to nested classes and methods

    - function-level:   cst.FunctionDef, any type parameter assignments that happened within
                        a function and are only available to nested classes and methods
    """

    def __init__(
        self,
        node: t.Union[
            ClassTypeParamCollection, FunctionTypeParamCollection, cst.Module
        ],
        type_collection: t.Optional[TypeClassCollection] = None,
    ) -> None:
        self._node = node

        data = None if not type_collection else deepcopy(type_collection.data)
        """
        We want to deepcopy the data because we don't want the inner scope to add symbols or aliases to the outer scope
        """
        self._type_collection = TypeClassCollection(data=data)

    @property
    def node(
        self,
    ) -> t.Union[ClassTypeParamCollection, FunctionTypeParamCollection, cst.Module]:
        return self._node

    @property
    def type_collection(self) -> TypeClassCollection:
        return self._type_collection


class BaseVisitor(m.MatcherDecoratableTransformer):
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path

        self._node_to_parent: dict[cst.CSTNode, cst.CSTNode] = {}
        self._scope_stack: list[ScopeContainer] = []
        # A stack to store entered scopes
        # When visiting a module, class or function, the respective container is pushed onto the stack
        # When leaving a module, class or function, we will pop() from the stack

        self._unused_assignments: dict[Symbol, cst.Assign] = {}
        # Mutable mapping that maps a symbol to the Assign node that it was created in
        # We need to keep track of this because we don't want to delete assignments that are important
        # because the defined symbol is still used

        super().__init__()

    @property
    def current_typecollection(self) -> TypeClassCollection:
        return self._scope_stack[-1].type_collection

    @property
    def current_node(
        self,
    ) -> t.Union[ClassTypeParamCollection, FunctionTypeParamCollection, cst.Module]:
        return self._scope_stack[-1].node

    @property
    def unused_assignments(self) -> dict[Symbol, cst.Assign]:
        return self._unused_assignments

    def on_visit(self, node: cst.CSTNode) -> bool:
        for child in node.children:
            self._node_to_parent[child] = node

        return super().on_visit(node)

    def visit_Module(self, node: cst.Module) -> None:
        self._scope_stack.append(ScopeContainer(node))

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        self._scope_stack.pop()
        return updated_node

    def _get_import_symbols(
        self, node: t.Union[cst.Import, cst.ImportFrom]
    ) -> dict[str, str]:
        assert not isinstance(node.names, cst.ImportStar)
        _name_to_id_mapping: dict[str, str] = {}

        for alias in node.names:
            id_ = origin_name = t.cast(str, alias.name.value)

            if alias.asname is not None:
                id_ = cst.ensure_type(alias.asname.name, cst.Name).value

            _name_to_id_mapping[origin_name] = id_

        return _name_to_id_mapping

    def visit_Import(self, node: cst.Import) -> None:
        import_info = self._get_import_symbols(node)
        namespaces: list[str] = []
        if typing_import := import_info.get("typing"):
            namespaces.append(typing_import)

        if typing_extensions_import := import_info.get("typing_extensions"):
            namespaces.append(typing_extensions_import)

        for namespace in namespaces:
            self.current_typecollection.update_aliases(namespace)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.module is None:
            return

        if node.module.value not in ("typing", "typing_extensions"):
            return

        if isinstance(node.names, cst.ImportStar):
            self.current_typecollection.update_aliases()

        else:
            import_info = self._get_import_symbols(node)
            self.current_typecollection.update_aliases_from_import_info(import_info)

    def _process_typeparam_assign(self, node: cst.Assign) -> bool:
        if not m.matches(
            node,
            m.Assign(
                targets=[m.AssignTarget(m.Name())],
                value=m.Call(m.Attribute() | m.Name()),
            ),
        ):
            return False

        call = cst.ensure_type(node.value, cst.Call)
        target = cst.ensure_type(node.targets[0].target, cst.Name)

        var_name = target.value
        func_name = get_qualified_name(call.func)

        for typeparam in TYPE_PARAM_CLASSES:
            info = self.current_typecollection.get(typeparam)
            if func_name in info.aliases:
                try:
                    symbol = info.build_symbol_from_assignment(var_name, call.args)
                except TypeParamMismatch as e:
                    logging.error(
                        f"Type Error in {format_special(self._file_path)}: Can't assign variable {var_name} to {info.name}({e.arg_name!r})"
                    )
                    return False

                if self.should_ignore_assign(node):
                    # Since we ignore a valid type parameter assignment
                    # we need to make sure that if a symbol from outer scope with the same name exists
                    # it is still overriden which is why we need to remove the symbol from the mapping
                    # so it is not encounted for when we inspect the type parameters used for classes and functions later
                    info.symbols.pop(symbol.name, None)
                    return False

                info.symbols[symbol.name] = symbol
                self._unused_assignments[symbol] = node
                return True

        return False

    def visit_Assign(self, node: cst.Assign) -> None:
        self._process_typeparam_assign(node)

    # We need to specify a `leave_Assign` because otherwise libcst defaults to creating a new `libcst.Assign` instance with a new memory address
    # This is not what we want, because when comparing assignment nodes in the second visitor pass, the IDs don't match and we can't remove unused assignments
    def leave_Assign(
        self, original_node: cst.Assign, updated_node: cst.Assign
    ) -> cst.Assign:
        return original_node

    def _assign_is_typealias(self, node: cst.AnnAssign) -> bool:
        if not m.matches(node.annotation, m.Annotation(m.Attribute() | m.Name())):
            return False

        name = get_qualified_name(node.annotation.annotation)

        return name in self.current_typecollection.get(TypeAliasInfo).aliases

    def process_TypeAlias_node(
        self,
        original_node: cst.AnnAssign,
        updated_node: cst.AnnAssign,
        *,
        ignore: bool,
        remove_variance: bool = False,
        remove_private: bool = False,
    ) -> t.Union[cst.AnnAssign, cst.TypeAlias]:
        if not self._assign_is_typealias(original_node) or original_node.value is None:
            return updated_node

        _used_typevars = self._resolve_assign_type_parameter_used(
            original_node, self.current_typecollection.get(TypeVarInfo).symbols.values()
        )
        _used_paramspecs = self._resolve_assign_type_parameter_used(
            original_node,
            self.current_typecollection.get(ParamSpecInfo).symbols.values(),
        )
        _used_typevartuples = self._resolve_assign_type_parameter_used(
            original_node,
            self.current_typecollection.get(TypeVarTupleInfo).symbols.values(),
        )

        if ignore:
            for sym in (*_used_typevars, *_used_paramspecs, *_used_typevartuples):
                # if we are going to ignore the TypeAlias then the symbol is no longer unused
                # and the type parameter assignment should not be deleted
                self._unused_assignments.pop(sym, None)

            return updated_node

        _TypeAliasNode = cst.TypeAlias(
            name=cst.ensure_type(original_node.target, cst.Name),
            value=original_node.value,
        )
        new_node = self.add_typeparameters(
            _TypeAliasNode,
            _TypeAliasNode,
            _used_typevars,
            _used_paramspecs,
            _used_typevartuples,
            remove_variance=remove_variance,
            remove_private=remove_private,
        )
        if remove_variance or remove_private:
            new_node = new_node.with_changes(
                value=new_node.value.visit(
                    CleanNameTransformer(
                        self.current_typecollection, remove_variance, remove_private
                    )
                )
            )

        return new_node

    def _should_ignore_comment(self, comment: t.Optional[cst.Comment]) -> bool:
        if comment is None:
            return False

        return comment.value[1:].strip() in _IGNORE_COMMENTS_RULES

    def should_ignore_assign(self, node: t.Union[cst.Assign, cst.AnnAssign]) -> bool:
        parent = ensure_type(
            self._node_to_parent[node],
            cst.SimpleStatementLine,
            cst.SimpleStatementSuite,
        )

        return self._should_ignore_comment(parent.trailing_whitespace.comment)

    def _should_ignore_compound_statement(
        self, node: cst.BaseCompoundStatement
    ) -> bool:
        body = ensure_type(node.body, cst.SimpleStatementSuite, cst.IndentedBlock)

        if isinstance(body, cst.SimpleStatementSuite):
            return self._should_ignore_comment(body.trailing_whitespace.comment)

        else:
            return self._should_ignore_comment(body.header.comment)

    def _contains_symbol_name(self, node: cst.CSTNode, sym: Symbol) -> bool:
        return bool(m.findall(node, m.Name(sym.name)))

    def _resolve_symbols_used(
        self, symbols: t.Iterable[_SymbolT], predicate: t.Callable[[_SymbolT], bool]
    ) -> list[_SymbolT]:
        _matched_symbols: list[_SymbolT] = []
        for sym in symbols:
            if predicate(sym):
                _matched_symbols.append(sym)

        return _matched_symbols

    def _resolve_assign_type_parameter_used(
        self, node: cst.AnnAssign, symbols: t.Iterable[_SymbolT]
    ) -> list[_SymbolT]:
        def condition(sym: Symbol) -> bool:
            return self._contains_symbol_name(node, sym)

        return self._resolve_symbols_used(symbols, condition)

    def _resolve_class_type_parameter_used(
        self, node: cst.ClassDef, symbols: t.Iterable[_SymbolT]
    ) -> list[_SymbolT]:
        def condition(sym: _SymbolT) -> bool:
            for base in node.bases:
                if self._contains_symbol_name(base, sym):
                    return True

            return False

        return self._resolve_symbols_used(symbols, condition)

    def _resolve_function_type_parameter_used(
        self, node: cst.FunctionDef, symbols: t.Iterable[_SymbolT]
    ) -> list[_SymbolT]:
        def condition(sym: Symbol) -> bool:
            return self._contains_symbol_name(node.params, sym) or (
                node.returns is not None
                and self._contains_symbol_name(node.returns, sym)
            )

        return self._resolve_symbols_used(symbols, condition)

    def update_param_collection(
        self,
        collection: TypeParamCollection[_SupportsTypeParameterT],
        *,
        condition: t.Callable[[Symbol], bool],
        resolver: t.Callable[[_SupportsTypeParameterT, list[Symbol]], list[Symbol]],
        ignore: bool,
    ) -> None:
        pep695_typeparams: list[str] = []
        for param, param_collection in zip(
            TYPE_PARAM_CLASSES,
            (
                collection.typevars_used,
                collection.paramspecs_used,
                collection.typevartuples_used,
            ),
        ):
            param_collection = t.cast(list[Symbol], param_collection)
            symbols = resolver(
                collection.node,
                list(self.current_typecollection.get(param).symbols.values()),
            )
            new_symbols = [sym for sym in symbols if condition(sym)]
            if ignore is True:
                for sym in new_symbols:
                    self._unused_assignments.pop(sym, None)
                    pep695_typeparams.append(sym.name)
                    # ugly hack to make sure the typevars are still accounted for in inner classes/functions
                    # can't put them in `*_used` because we don't want to transpile them later

            else:
                param_collection.extend(new_symbols)

        collection.pep695_typeparameters.extend(pep695_typeparams)

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self._scope_stack.append(
            ScopeContainer(
                ClassTypeParamCollection(node),
                type_collection=self.current_typecollection,
            )
        )

        collection = ensure_type(self.current_node, ClassTypeParamCollection)
        self.update_param_collection(
            collection,
            condition=lambda sym: sym.name not in collection.pep695_typeparameters,
            resolver=self._resolve_class_type_parameter_used,
            ignore=self._should_ignore_compound_statement(node),
        )

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        self._scope_stack.pop()
        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        self._scope_stack.append(
            ScopeContainer(
                FunctionTypeParamCollection(node),
                type_collection=self.current_typecollection,
            )
        )
        collection = ensure_type(self.current_node, FunctionTypeParamCollection)
        _inherited_symbols: dict[type[Symbol], list[Symbol]] = {
            TypeVarSymbol: [],
            ParamSpecSymbol: [],
            TypeVarTupleSymbol: [],
        }
        _inherited_pep695_names: list[str] = [*collection.pep695_typeparameters]

        for container in reversed(self._scope_stack):
            if isinstance(container.node, cst.Module):
                break

            _inherited_pep695_names.extend(container.node.pep695_typeparameters)

            _inherited_symbols[TypeVarSymbol].extend(container.node.typevars_used)
            _inherited_symbols[ParamSpecSymbol].extend(container.node.paramspecs_used)
            _inherited_symbols[TypeVarTupleSymbol].extend(
                container.node.typevartuples_used
            )

            if isinstance(container.node, ClassTypeParamCollection):
                break  # Classes can't re-use type parameters

        self.update_param_collection(
            collection,
            condition=lambda sym: (
                sym.name not in _inherited_pep695_names
                and sym not in _inherited_symbols[type(sym)]
            ),
            resolver=self._resolve_function_type_parameter_used,
            ignore=self._should_ignore_compound_statement(node),
        )

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        self._scope_stack.pop()
        return updated_node

    def add_typeparameters(
        self,
        original_node: _SupportsTypeParameterT,
        updated_node: _SupportsTypeParameterT,
        typevars: list[TypeVarSymbol],
        paramspecs: list[ParamSpecSymbol],
        typevartuples: list[TypeVarTupleSymbol],
        *,
        remove_variance: bool,
        remove_private: bool,
    ) -> _SupportsTypeParameterT:
        if not any((typevars, paramspecs, typevartuples)):
            return updated_node

        params: list[cst.TypeParam] = []
        if original_node.type_parameters is not None:
            params = list(original_node.type_parameters.params)

        for param_type, symbols_used in zip(
            TYPE_PARAM_CLASSES,
            (typevars, paramspecs, typevartuples),
        ):
            for symbol in symbols_used:
                params.append(
                    self.current_typecollection.get(param_type).build(
                        symbol,
                        remove_variance=remove_variance,
                        remove_private=remove_private,
                    )
                )

        return updated_node.with_changes(type_parameters=cst.TypeParameters(params))


class ClassBaseArgTransformer(cst.CSTTransformer):
    def __init__(self, type_collection: TypeClassCollection) -> None:
        self._type_collection = type_collection

        super().__init__()

    def leave_Arg(
        self, original_node: cst.Arg, updated_node: cst.Arg
    ) -> t.Union[cst.Arg, cst.RemovalSentinel]:
        if not isinstance(original_node.value, cst.Subscript):
            return updated_node

        name = get_qualified_name(original_node.value.value)
        if name in self._type_collection.get(GenericInfo).aliases:
            return cst.RemoveFromParent()

        if name in self._type_collection.get(ProtocolInfo).aliases:
            return updated_node.with_changes(value=original_node.value.value)

        return updated_node


class CleanNameTransformer(cst.CSTTransformer):
    def __init__(
        self, type_collection: TypeClassCollection, variance: bool, private: bool
    ) -> None:
        self._type_collection = type_collection
        self._variance = variance
        self._private = private

        super().__init__()

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        for param in TYPE_PARAM_CLASSES:
            names = self._type_collection.get(param).symbols.keys()
            if original_node.value in names:
                return cst.Name(
                    make_clean_name(original_node.value, self._variance, self._private)
                )

        return updated_node


class RemoveAssignments(cst.CSTTransformer):
    def __init__(self, assignments: set[cst.Assign]) -> None:
        self._assignments = assignments

    def leave_Assign(
        self, original_node: cst.Assign, updated_node: cst.Assign
    ) -> t.Union[cst.Assign, cst.RemovalSentinel]:
        if original_node in self._assignments:
            return cst.RemoveFromParent()

        return updated_node
