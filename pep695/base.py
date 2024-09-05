from __future__ import annotations

import abc
from dataclasses import dataclass, field
import inspect

import typing as t

import libcst as cst
from libcst import matchers as m

from pep695.symbols import Symbol, TypeVarSymbol, ParamSpecSymbol, TypeVarTupleSymbol
from pep695.aliases import AliasCollection, get_qualified_name

_SupportsTypeParamaterT = t.TypeVar(
    "_SupportsTypeParamaterT", cst.FunctionDef, cst.ClassDef, cst.TypeAlias
)
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
    name: str = field(init=False)
    aliases: AliasCollection = field(default_factory=AliasCollection)

    def __init_subclass__(cls) -> None:
        if not inspect.isabstract(cls):
            _typing_class_info_collection.append(cls)


@dataclass
class TypingParameterClassInfo(t.Generic[_SymbolT], TypingClassInfo, abc.ABC):
    symbols: list[_SymbolT] = field(default_factory=list)

    @abc.abstractmethod
    def build(self, symbol: _SymbolT) -> cst.TypeParam:
        """Build and return the node from a given symbol"""

    @abc.abstractmethod
    def build_symbol_from_args(self, arguments: t.Sequence[cst.Arg]) -> _SymbolT:
        """Build a symbol from the given args"""


class TypeVarInfo(TypingParameterClassInfo[TypeVarSymbol]):
    name = "TypeVar"

    def build(self, symbol: TypeVarSymbol) -> cst.TypeParam:
        bound = symbol.bound
        if bound is None and symbol.constraints:
            elements: list[cst.Element] = []
            for constraint in symbol.constraints:
                elements.append(cst.Element(value=constraint))

            bound = cst.Tuple(elements)

        return cst.TypeParam(
            param=cst.TypeVar(name=cst.Name(value=symbol.name), bound=bound),
            default=symbol.default,
        )

    def build_symbol_from_args(self, arguments: t.Sequence[cst.Arg]) -> TypeVarSymbol:
        args, kwargs = _get_args_kwargs(arguments)
        name = cst.ensure_type(args[0], cst.SimpleString).raw_value
        constraints: list[cst.BaseExpression] = [] if len(args) == 1 else args[1:]
        return TypeVarSymbol(
            name=name,
            constraints=constraints,
            bound=kwargs.get("bound"),
            default=kwargs.get("default"),
        )


class ParamSpecInfo(TypingParameterClassInfo[ParamSpecSymbol]):
    name = "ParamSpec"

    def build(self, symbol: ParamSpecSymbol) -> cst.TypeParam:
        return cst.TypeParam(
            param=cst.ParamSpec(name=cst.Name(value=symbol.name)),
            default=symbol.default,
        )

    def build_symbol_from_args(self, arguments: t.Sequence[cst.Arg]) -> ParamSpecSymbol:
        args, kwargs = _get_args_kwargs(arguments)
        return ParamSpecSymbol(
            name=cst.ensure_type(args[0], cst.SimpleString).raw_value,
            default=kwargs.get("default"),
        )


class TypeVarTupleInfo(TypingParameterClassInfo[TypeVarTupleSymbol]):
    name = "TypeVarTuple"

    def build(self, symbol: TypeVarTupleSymbol) -> cst.TypeParam:
        return cst.TypeParam(
            param=cst.TypeVarTuple(name=cst.Name(value=symbol.name)),
            default=symbol.default,
        )

    def build_symbol_from_args(
        self, arguments: t.Sequence[cst.Arg]
    ) -> TypeVarTupleSymbol:
        args, kwargs = _get_args_kwargs(arguments)
        return TypeVarTupleSymbol(
            name=cst.ensure_type(args[0], cst.SimpleString).raw_value,
            default=kwargs.get("default"),
        )


class GenericInfo(TypingClassInfo):
    name = "Generic"


class TypeAliasInfo(TypingClassInfo):
    name = "TypeAlias"


class ProtocolInfo(TypingClassInfo):
    name = "Protocol"


_TYPE_PARAM_CLASSES = t.cast(
    t.Sequence[type[TypingParameterClassInfo[Symbol]]],
    (TypeVarInfo, ParamSpecInfo, TypeVarTupleInfo),
)


class TypeClassCollection:
    __slots__: t.Sequence[str] = ("_data",)

    def __init__(self) -> None:
        self._data: dict[type[TypingClassInfo], TypingClassInfo] = {
            cls: cls() for cls in _typing_class_info_collection
        }

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
        if namespace != "":
            namespace += "."

        for cls, info in self._data.items():
            info.aliases.add(f"{namespace}{cls.name}")

    def update_aliases_from_import_info(self, import_info: dict[str, str]) -> None:
        for cls, info in self._data.items():
            info.aliases.add_if_not_none(import_info.get(cls.name))


class BaseVisitor(m.MatcherDecoratableTransformer):
    def __init__(self) -> None:
        self._type_collection = TypeClassCollection()

        self._new_typevars_for_node: dict[
            t.Union[cst.FunctionDef, cst.ClassDef], list[TypeVarSymbol]
        ] = {}
        self._new_paramspecs_for_node: dict[
            t.Union[cst.FunctionDef, cst.ClassDef], list[ParamSpecSymbol]
        ] = {}
        self._new_typevartuples_for_node: dict[
            t.Union[cst.FunctionDef, cst.ClassDef], list[TypeVarTupleSymbol]
        ] = {}

        self._node_to_parent: dict[cst.CSTNode, cst.CSTNode] = {}

        super().__init__()

    def on_visit(self, node: cst.CSTNode) -> bool:
        for child in node.children:
            self._node_to_parent[child] = node

        return super().on_visit(node)

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
            self._type_collection.update_aliases(namespace)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.module is None:
            return

        if node.module.value not in ("typing", "typing_extensions"):
            return

        if isinstance(node.names, cst.ImportStar):
            self._type_collection.update_aliases()

        else:
            import_info = self._get_import_symbols(node)
            self._type_collection.update_aliases_from_import_info(import_info)

    def _is_typeparam_assign(self, node: cst.Call) -> bool:
        if not m.matches(node, m.Call(m.Attribute() | m.Name())):
            return False

        name = get_qualified_name(node.func)

        for typeparam in _TYPE_PARAM_CLASSES:
            info = self._type_collection.get(typeparam)
            if name in info.aliases:
                info.symbols.append(info.build_symbol_from_args(node.args))
                return True

        return False

    def _assign_is_typealias(self, node: cst.AnnAssign) -> bool:
        if not m.matches(node.annotation, m.Annotation(m.Attribute() | m.Name())):
            return False

        name = get_qualified_name(node.annotation.annotation)

        return name in self._type_collection.get(TypeAliasInfo).aliases

    def leave_AnnAssign(
        self, original_node: cst.AnnAssign, updated_node: cst.AnnAssign
    ) -> t.Union[cst.AnnAssign, cst.TypeAlias]:
        if self._should_ignore_statement(original_node):
            return updated_node

        if not self._assign_is_typealias(original_node) or original_node.value is None:
            return updated_node

        _used_typevars = self._resolve_assign_type_parameter_used(
            original_node, self._type_collection.get(TypeVarInfo).symbols
        )
        _used_paramspecs = self._resolve_assign_type_parameter_used(
            original_node, self._type_collection.get(ParamSpecInfo).symbols
        )
        _used_typevartuples = self._resolve_assign_type_parameter_used(
            original_node, self._type_collection.get(TypeVarTupleInfo).symbols
        )

        _TypeAliasNode = cst.TypeAlias(
            name=cst.ensure_type(original_node.target, cst.Name),
            value=original_node.value,
        )
        new_node = self._add_typeparameters(
            _TypeAliasNode,
            _TypeAliasNode,
            _used_typevars,
            _used_paramspecs,
            _used_typevartuples,
        )
        return new_node

    def _should_ignore_statement(self, node: cst.CSTNode) -> bool:
        parent = cst.ensure_type(self._node_to_parent[node], cst.SimpleStatementLine)
        if (
            comment := parent.trailing_whitespace.comment
        ) is not None and comment.value[1:].strip() in _IGNORE_COMMENTS_RULES:
            return True

        return False

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
        condition: t.Callable[[Symbol], bool] = lambda sym: self._contains_symbol_name(
            node, sym
        )
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
        condition: t.Callable[[Symbol], bool] = lambda sym: (
            self._contains_symbol_name(node.params, sym)
            or (
                node.returns is not None
                and self._contains_symbol_name(node.returns, sym)
            )
        )

        return self._resolve_symbols_used(symbols, condition)

    def _resolve_pep695_type_parameters(
        self, node: _SupportsTypeParamaterT
    ) -> list[str]:
        if node.type_parameters is None:
            return []

        names = t.cast(t.Sequence[cst.Name], m.findall(node.type_parameters, m.Name()))
        return [name.value for name in names]

    def _set_new_symbols_for(
        self,
        node: _SupportsTypeParamaterT,
        *,
        condition: t.Callable[[Symbol, list[str]], bool],
        resolver: t.Callable[[_SupportsTypeParamaterT, list[Symbol]], list[Symbol]],
    ) -> None:
        _typeparameter_names = self._resolve_pep695_type_parameters(node)

        for cls, new_symbols_for_node in zip(
            _TYPE_PARAM_CLASSES,
            (
                self._new_typevars_for_node,
                self._new_paramspecs_for_node,
                self._new_typevartuples_for_node,
            ),
        ):
            info = self._type_collection.get(cls)
            _new_symbols = resolver(node, info.symbols)
            new_symbols_for_node[node] = [  # type: ignore
                symbol
                for symbol in _new_symbols
                if condition(symbol, _typeparameter_names)
            ]

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self._set_new_symbols_for(
            node,
            condition=lambda sym, type_params: sym.name not in type_params,
            resolver=self._resolve_class_type_parameter_used,
        )

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        parent = self._node_to_parent[node]
        _inherited_symbols: dict[type[Symbol], list[Symbol]] = {
            TypeVarSymbol: [],
            ParamSpecSymbol: [],
            TypeVarTupleSymbol: [],
        }

        while isinstance(parent, cst.Module) is False:
            if isinstance(parent, (cst.ClassDef, cst.FunctionDef)):
                _inherited_symbols[TypeVarSymbol].extend(
                    self._new_typevars_for_node[parent]
                )
                _inherited_symbols[ParamSpecSymbol].extend(
                    self._new_paramspecs_for_node[parent]
                )
                _inherited_symbols[TypeVarTupleSymbol].extend(
                    self._new_typevartuples_for_node[parent]
                )

                if isinstance(parent, cst.ClassDef):
                    break  # Stop here because generic classes can't re-use TypeVars that were already declared in outer scope

            parent = self._node_to_parent[parent]

        self._set_new_symbols_for(
            node,
            condition=lambda sym, type_params: sym not in _inherited_symbols[type(sym)]
            and sym.name not in type_params,
            resolver=self._resolve_function_type_parameter_used,
        )

    def _add_typeparameters(
        self,
        original_node: _SupportsTypeParamaterT,
        updated_node: _SupportsTypeParamaterT,
        typevars: list[TypeVarSymbol],
        paramspecs: list[ParamSpecSymbol],
        typevartuples: list[TypeVarTupleSymbol],
    ) -> _SupportsTypeParamaterT:
        if not any((typevars, paramspecs, typevartuples)):
            return updated_node

        params: list[cst.TypeParam] = []
        if original_node.type_parameters is not None:
            params = list(original_node.type_parameters.params)

        for typevar in typevars:
            params.append(self._type_collection.get(TypeVarInfo).build(typevar))

        for typevartuple in typevartuples:
            params.append(
                self._type_collection.get(TypeVarTupleInfo).build(typevartuple)
            )

        for paramspec in paramspecs:
            params.append(self._type_collection.get(ParamSpecInfo).build(paramspec))

        return updated_node.with_changes(type_parameters=cst.TypeParameters(params))

class RemoveGenericBaseMixin(m.MatcherDecoratableTransformer):
    _type_collection: TypeClassCollection

    @m.call_if_inside(
        m.ClassDef(bases=[m.AtLeastN(n=1)])
    )  # Match type subscript in class base
    def leave_Arg(
        self, original_node: cst.Arg, updated_node: cst.Arg
    ) -> t.Union[cst.Arg, cst.RemovalSentinel]:
        if not m.matches(original_node, m.Arg(m.Subscript(m.Attribute() | m.Name()))):
            return updated_node

        name = get_qualified_name(
            cst.ensure_type(original_node.value, cst.Subscript).value
        )

        if name in self._type_collection.get(GenericInfo).aliases:

            return cst.RemoveFromParent()

        if name in self._type_collection.get(ProtocolInfo).aliases:
            return updated_node.with_changes(
                value=cst.ensure_type(original_node.value, cst.Subscript).value
            )

        return updated_node
