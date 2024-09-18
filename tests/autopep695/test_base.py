# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import typing as t

import libcst as cst
import pytest

from autopep695.base import (
    _get_args_kwargs,
    TypingClassInfo,
    _typing_class_info_collection,
    TypeVarInfo,
    TypeVarSymbol,
    ParamSpecInfo,
    ParamSpecSymbol,
    TypeVarTupleInfo,
    TypeVarTupleSymbol,
    GenericInfo,
    ProtocolInfo,
    TypeAliasInfo,
    TypeClassCollection,
    TypeParamCollection,
    ScopeContainer,
)
from autopep695.aliases import AliasCollection
from autopep695.errors import TypeParamMismatch, InvalidTypeParamConstructor

expr = cst.parse_expression


def deep_equals_if_not_none(
    node1: t.Optional[cst.CSTNode], node2: t.Optional[cst.CSTNode]
):
    if node1 is not None:
        assert node2 is not None
        assert node1.deep_equals(node2)

    else:
        assert node2 is None

    return True


@pytest.mark.parametrize(
    "call, expected_args, expected_kwargs",
    [
        (
            expr("TypeVar('T', int, str, default=int)"),
            [expr("'T'"), expr("int"), expr("str")],
            {"default": expr("int")},
        ),
        (
            expr("TypeVar('AAA', bound=int, default=bool)"),
            [expr("'AAA'")],
            {"bound": expr("int"), "default": expr("bool")},
        ),
        (expr("TypeVar()"), [], {}),
        (expr('ParamSpec("P")'), [expr('"P"')], {}),
        (expr("TypeVarTuple(default=int)"), [], {"default": expr("int")}),
        (expr("ParamSpec(*args, **kwargs)"), [expr("args"), expr("kwargs")], {}),
        (expr("x(this=5, this=8)"), [], {"this": expr("8")}),
    ],
)
def test_get_args_kwargs(
    call: cst.Call,
    expected_args: list[cst.BaseExpression],
    expected_kwargs: dict[str, cst.BaseExpression],
):
    args, kwargs = _get_args_kwargs(call.args)
    for arg, expected_arg in zip(args, expected_args):
        assert arg.deep_equals(expected_arg)

    for kwarg, expected_kwarg in zip(kwargs.keys(), expected_kwargs.keys()):
        assert kwarg == expected_kwarg and kwargs[kwarg].deep_equals(
            expected_kwargs[expected_kwarg]
        )


def test_TypingClassInfo():
    info = TypingClassInfo()
    assert info.aliases == AliasCollection()

    class SubclassMock(TypingClassInfo):
        name = "a"

    assert SubclassMock in _typing_class_info_collection
    assert TypingClassInfo(AliasCollection("a")).aliases == AliasCollection("a")


REMOVE_VARIANCE_DATA = [
    ("T", "T"),
    ("T_co", "T"),
    ("_T", "_T"),
    ("_T_contra", "_T"),
    ("T_ka", "T_ka"),
]
REMOVE_PRIVATE_DATA = [
    ("T", "T"),
    ("_T", "T"),
    ("__T", "T"),
    ("___T", "T"),
    ("_a__T", "a__T"),
    ("_My_T_", "My_T_"),
    ("_T_co", "T_co"),
]
REMOVE_VARIANCE_AND_PRIVATE_DATA = [
    ("T", "T"),
    ("_T", "T"),
    ("T_co", "T"),
    ("T_contra", "T"),
    ("_T_co", "T"),
    ("__T_contra", "T"),
    ("_T_Function_co", "T_Function"),
    ("____T_", "T_"),
]


class TestTypeVarInfo:
    @pytest.fixture(scope="function")
    def typevar(self) -> TypeVarInfo:
        return TypeVarInfo()

    def test_name(self, typevar: TypeVarInfo):
        from typing import TypeVar

        assert typevar.name == TypeVar.__name__

    @pytest.mark.parametrize(
        "symbol, typeparam",
        [
            (
                TypeVarSymbol("T", [], None, None),
                cst.TypeParam(
                    param=cst.TypeVar(name=cst.Name("T"), bound=None), default=None
                ),
            ),
            (
                TypeVarSymbol(
                    "A",
                    constraints=[expr("int"), expr("str")],
                    bound=expr("int"),
                    default=expr("int"),
                ),
                cst.TypeParam(
                    param=cst.TypeVar(name=cst.Name("A"), bound=expr("int")),
                    default=expr("int"),
                ),
            ),
            (
                TypeVarSymbol(
                    "B", constraints=[expr("a"), expr("b")], bound=None, default=None
                ),
                cst.TypeParam(
                    param=cst.TypeVar(
                        name=cst.Name("B"),
                        bound=cst.Tuple(
                            (cst.Element(expr("a")), cst.Element(expr("b")))
                        ),
                    ),
                    default=None,
                ),
            ),
            (
                TypeVarSymbol("C", constraints=[], bound=None, default=expr("int")),
                cst.TypeParam(
                    param=cst.TypeVar(name=cst.Name("C"), bound=None),
                    default=expr("int"),
                ),
            ),
        ],
    )
    def test_build(
        self, typevar: TypeVarInfo, symbol: TypeVarSymbol, typeparam: cst.TypeParam
    ):
        assert typevar.build(
            symbol, remove_variance=False, remove_private=False
        ).deep_equals(typeparam)

    @pytest.mark.parametrize("name, expected_name", REMOVE_VARIANCE_DATA)
    def test_build_remove_variance(
        self, typevar: TypeVarInfo, name: str, expected_name: str
    ) -> None:
        symbol = TypeVarSymbol(name, [], None, None)
        assert (
            typevar.build(
                symbol, remove_variance=True, remove_private=False
            ).param.name.value
            == expected_name
        )

    @pytest.mark.parametrize("name, expected_name", REMOVE_PRIVATE_DATA)
    def test_build_remove_private(
        self, typevar: TypeVarInfo, name: str, expected_name: str
    ):
        symbol = TypeVarSymbol(name, [], None, None)
        assert (
            typevar.build(
                symbol, remove_variance=False, remove_private=True
            ).param.name.value
            == expected_name
        )

    @pytest.mark.parametrize(
        "name, expected_name",
        REMOVE_VARIANCE_AND_PRIVATE_DATA,
    )
    def test_build_remove_variance_and_private(
        self, typevar: TypeVarInfo, name: str, expected_name: str
    ):
        symbol = TypeVarSymbol(name, [], None, None)
        assert (
            typevar.build(
                symbol, remove_variance=True, remove_private=True
            ).param.name.value
            == expected_name
        )

    def test_build_symbol_from_assignment_type_error(self, typevar: TypeVarInfo):
        with pytest.raises(Exception):
            typevar.build_symbol_from_assignment("T", (cst.Arg(expr("T")),))

    def test_build_symbol_from_assignment_mismatch(self, typevar: TypeVarInfo):
        with pytest.raises(TypeParamMismatch):
            typevar.build_symbol_from_assignment(
                "T", (cst.Arg(cst.SimpleString("'T_co'")),)
            )

    def test_build_symbol_from_assignment_invalid_constructor(
        self, typevar: TypeVarInfo
    ):
        with pytest.raises(InvalidTypeParamConstructor):
            typevar.build_symbol_from_assignment("T", [])

    @pytest.mark.parametrize(
        "call, expected_symbol",
        [
            (
                expr("TypeVar('a', int, str, default=int)"),
                TypeVarSymbol("a", [expr("int"), expr("str")], None, expr("int")),
            ),
            (expr("TypeVar('b')"), TypeVarSymbol("b", [], None, None)),
            (
                expr("TypeVar('ThisThat', bound=int)"),
                TypeVarSymbol("ThisThat", [], expr("int"), None),
            ),
            (
                expr("TypeVar('lol', default=str)"),
                TypeVarSymbol("lol", [], None, expr("str")),
            ),
            (expr("TypeVar('V', int)"), TypeVarSymbol("V", [expr("int")], None, None)),
            (
                expr("TypeVar('T', unrelated_kwarg=unrelated_value)"),
                TypeVarSymbol("T", [], None, None),
            ),
        ],
    )
    def test_build_symbol_from_assignment(
        self, typevar: TypeVarInfo, call: cst.Call, expected_symbol: TypeVarSymbol
    ):
        built_symbol = typevar.build_symbol_from_assignment(
            expected_symbol.name, call.args
        )
        assert built_symbol.name == expected_symbol.name
        for constraint, expected_constraint in zip(
            built_symbol.constraints, expected_symbol.constraints
        ):
            assert constraint.deep_equals(expected_constraint)

        assert deep_equals_if_not_none(built_symbol.bound, expected_symbol.bound)
        assert deep_equals_if_not_none(built_symbol.default, expected_symbol.default)


class TestParamSpecInfo:
    @pytest.fixture(scope="function")
    def paramspec(self) -> ParamSpecInfo:
        return ParamSpecInfo()

    def test_name(self, paramspec: ParamSpecInfo):
        from typing_extensions import ParamSpec

        assert paramspec.name == ParamSpec.__name__

    @pytest.mark.parametrize(
        "symbol, typeparam",
        [
            (
                ParamSpecSymbol("P", None),
                cst.TypeParam(param=cst.ParamSpec(name=cst.Name("P")), default=None),
            ),
            (
                ParamSpecSymbol("A", default=expr("Callable[..., None]")),
                cst.TypeParam(
                    param=cst.ParamSpec(cst.Name("A")),
                    default=expr("Callable[..., None]"),
                ),
            ),
        ],
    )
    def test_build(
        self,
        paramspec: ParamSpecInfo,
        symbol: ParamSpecSymbol,
        typeparam: cst.TypeParam,
    ):
        assert paramspec.build(
            symbol, remove_variance=False, remove_private=False
        ).deep_equals(typeparam)

    @pytest.mark.parametrize("name, expected_name", REMOVE_VARIANCE_DATA)
    def test_build_remove_variance(
        self, paramspec: ParamSpecInfo, name: str, expected_name: str
    ) -> None:
        symbol = ParamSpecSymbol(name, None)
        assert (
            paramspec.build(
                symbol, remove_variance=True, remove_private=False
            ).param.name.value
            == expected_name
        )

    @pytest.mark.parametrize("name, expected_name", REMOVE_PRIVATE_DATA)
    def test_build_remove_private(
        self, paramspec: ParamSpecInfo, name: str, expected_name: str
    ):
        symbol = ParamSpecSymbol(name, None)
        assert (
            paramspec.build(
                symbol, remove_variance=False, remove_private=True
            ).param.name.value
            == expected_name
        )

    @pytest.mark.parametrize("name, expected_name", REMOVE_VARIANCE_AND_PRIVATE_DATA)
    def test_build_remove_variance_and_private(
        self, paramspec: ParamSpecInfo, name: str, expected_name: str
    ):
        symbol = ParamSpecSymbol(name, None)
        assert (
            paramspec.build(
                symbol, remove_variance=True, remove_private=True
            ).param.name.value
            == expected_name
        )

    def test_build_symbol_from_assignment_type_error(self, paramspec: ParamSpecInfo):
        with pytest.raises(Exception):
            paramspec.build_symbol_from_assignment("P", (cst.Arg(expr("P")),))

    def test_build_symbol_from_assignment_mismatch(self, paramspec: ParamSpecInfo):
        with pytest.raises(TypeParamMismatch):
            paramspec.build_symbol_from_assignment(
                "P", (cst.Arg(cst.SimpleString("'_P'")),)
            )

    def test_build_symbol_from_assignment_invalid_constructor(
        self, paramspec: ParamSpecInfo
    ):
        with pytest.raises(InvalidTypeParamConstructor):
            paramspec.build_symbol_from_assignment("P", [])

    @pytest.mark.parametrize(
        "call, expected_symbol",
        [
            (
                expr("ParamSpec('P')"),
                ParamSpecSymbol("P", None),
            ),
            (
                expr("ParamSpec('A', default=Callable[..., None])"),
                ParamSpecSymbol("A", expr("Callable[..., None]")),
            ),
            (
                expr("ParamSpec('L', unrelated_arg, somekwarg=value)"),
                ParamSpecSymbol("L", None),
            ),
        ],
    )
    def test_build_symbol_from_assignment(
        self, paramspec: ParamSpecInfo, call: cst.Call, expected_symbol: ParamSpecSymbol
    ):
        built_symbol = paramspec.build_symbol_from_assignment(
            expected_symbol.name, call.args
        )
        assert built_symbol.name == expected_symbol.name
        assert deep_equals_if_not_none(built_symbol.default, expected_symbol.default)


class TestTypeVarTupleInfo:
    @pytest.fixture(scope="function")
    def typevartuple(self) -> TypeVarTupleInfo:
        return TypeVarTupleInfo()

    def test_name(self, typevartuple: TypeVarTupleInfo):
        from typing_extensions import TypeVarTuple

        assert typevartuple.name == TypeVarTuple.__name__

    @pytest.mark.parametrize(
        "symbol, typeparam",
        [
            (
                TypeVarTupleSymbol("Ts", None),
                cst.TypeParam(
                    param=cst.TypeVarTuple(name=cst.Name("Ts")), default=None
                ),
            ),
            (
                TypeVarTupleSymbol("As", default=expr("Unpack[tuple[T, ...]]")),
                cst.TypeParam(
                    param=cst.TypeVarTuple(cst.Name("As")),
                    default=expr("Unpack[tuple[T, ...]]"),
                ),
            ),
        ],
    )
    def test_build(
        self,
        typevartuple: TypeVarTupleInfo,
        symbol: TypeVarTupleSymbol,
        typeparam: cst.TypeParam,
    ):
        assert typevartuple.build(
            symbol, remove_variance=False, remove_private=False
        ).deep_equals(typeparam)

    @pytest.mark.parametrize("name, expected_name", REMOVE_VARIANCE_DATA)
    def test_build_remove_variance(
        self, typevartuple: TypeVarTupleInfo, name: str, expected_name: str
    ) -> None:
        symbol = TypeVarTupleSymbol(name, None)
        assert (
            typevartuple.build(
                symbol, remove_variance=True, remove_private=False
            ).param.name.value
            == expected_name
        )

    @pytest.mark.parametrize("name, expected_name", REMOVE_PRIVATE_DATA)
    def test_build_remove_private(
        self, typevartuple: TypeVarTupleInfo, name: str, expected_name: str
    ):
        symbol = TypeVarTupleSymbol(name, None)
        assert (
            typevartuple.build(
                symbol, remove_variance=False, remove_private=True
            ).param.name.value
            == expected_name
        )

    @pytest.mark.parametrize("name, expected_name", REMOVE_VARIANCE_AND_PRIVATE_DATA)
    def test_build_remove_variance_and_private(
        self, typevartuple: TypeVarTupleInfo, name: str, expected_name: str
    ):
        symbol = TypeVarTupleSymbol(name, None)
        assert (
            typevartuple.build(
                symbol, remove_variance=True, remove_private=True
            ).param.name.value
            == expected_name
        )

    def test_build_symbol_from_assignment_type_error(
        self, typevartuple: TypeVarTupleInfo
    ):
        with pytest.raises(Exception):
            typevartuple.build_symbol_from_assignment("Ts", (cst.Arg(expr("Ts")),))

    def test_build_symbol_from_assignment_mismatch(
        self, typevartuple: TypeVarTupleInfo
    ):
        with pytest.raises(TypeParamMismatch):
            typevartuple.build_symbol_from_assignment(
                "Ts", (cst.Arg(cst.SimpleString("'_Ts'")),)
            )

    def test_build_symbol_from_assignment_invalid_constructor(
        self, typevartuple: TypeVarTupleInfo
    ):
        with pytest.raises(InvalidTypeParamConstructor):
            typevartuple.build_symbol_from_assignment("Ts", [])

    @pytest.mark.parametrize(
        "call, expected_symbol",
        [
            (
                expr("TypeVarTuple('Ts')"),
                TypeVarTupleSymbol("Ts", None),
            ),
            (
                expr("TypeVarTuple('As', default=Unpack[tuple[T, ...]])"),
                TypeVarTupleSymbol("As", expr("Unpack[tuple[T, ...]]")),
            ),
            (
                expr("TypeVarTuple('L', unrelated_arg, somekwarg=value)"),
                TypeVarTupleSymbol("L", None),
            ),
        ],
    )
    def test_build_symbol_from_assignment(
        self,
        typevartuple: TypeVarTupleInfo,
        call: cst.Call,
        expected_symbol: TypeVarTupleSymbol,
    ):
        built_symbol = typevartuple.build_symbol_from_assignment(
            expected_symbol.name, call.args
        )
        assert built_symbol.name == expected_symbol.name
        assert deep_equals_if_not_none(built_symbol.default, expected_symbol.default)


class TestGenericInfo:
    def test_name(self):
        from typing import Generic

        assert GenericInfo().name == Generic.__name__


class TestTypeAliasInfo:
    def test_name(self):
        from typing_extensions import TypeAlias

        assert TypeAliasInfo().name == TypeAlias._name


class TestProtocolInfo:
    def test_name(self):
        from typing import Protocol

        assert ProtocolInfo().name == Protocol.__name__


class TestTypeClassCollection:
    @pytest.fixture(scope="function")
    def collection(self) -> TypeClassCollection:
        return TypeClassCollection()

    def test_with_data(self):
        data = {TypingClassInfo: TypingClassInfo()}
        assert TypeClassCollection(data).data == data

    def test_get(self, collection: TypeClassCollection):
        assert isinstance(collection.get(ProtocolInfo), ProtocolInfo)

    def test_get_keyerror(self, collection: TypeClassCollection):
        with pytest.raises(KeyError):
            collection.get(TypingClassInfo)

    def test_update_aliases_without_namespace(self, collection: TypeClassCollection):
        collection.update_aliases()

        for cls in collection.data.keys():
            assert cls.name in collection.data[cls].aliases

    def test_update_aliases_with_namespace(self, collection: TypeClassCollection):
        collection.update_aliases("typing")

        for cls in collection.data.keys():
            assert f"typing.{cls.name}" in collection.data[cls].aliases

    @pytest.mark.parametrize(
        "import_info, expected_aliases",
        [
            ({"TypeVar": "T"}, {TypeVarInfo: "T"}),
            ({"Mapping": "M"}, {}),
            ({"ParamSpec": "ParamSpec"}, {ParamSpecInfo: "ParamSpec"}),
            (
                {"Protocol": "Proto", "TypeAlias": "Alias"},
                {ProtocolInfo: "Proto", TypeAliasInfo: "Alias"},
            ),
        ],
    )
    def test_update_aliases_from_import_info(
        self,
        collection: TypeClassCollection,
        import_info: dict[str, str],
        expected_aliases: dict[type[TypingClassInfo], str],
    ):
        old_aliases: dict[type[TypingClassInfo], AliasCollection] = {}
        for cls, info in collection.data.items():
            old_aliases[cls] = AliasCollection(info.aliases)

        collection.update_aliases_from_import_info(import_info)

        for cls, info in collection.data.items():
            new_aliases = info.aliases - old_aliases[cls]
            if expected_alias := expected_aliases.get(cls):
                assert new_aliases == AliasCollection((expected_alias,))

            else:
                assert new_aliases == AliasCollection()


class TestTypeParamCollection:
    def test_with_pep695_node(self):
        statement = cst.ensure_type(
            cst.parse_statement("type a[T, *Ts, **P] = b"), cst.SimpleStatementLine
        )
        node = cst.ensure_type(statement.body[0], cst.TypeAlias)

        class MockCollection(TypeParamCollection[cst.TypeAlias]): ...

        collection = MockCollection(node)
        assert collection.pep695_typeparameters == ["T", "Ts", "P"]

    def test_without_pep695_node(self):
        statement = cst.ensure_type(
            cst.parse_statement("type a = b"), cst.SimpleStatementLine
        )
        node = cst.ensure_type(statement.body[0], cst.TypeAlias)

        class MockCollection(TypeParamCollection[cst.TypeAlias]): ...

        collection = MockCollection(node)
        assert collection.pep695_typeparameters == []


class TestScopeContainer:
    def test_deepcopy(self):
        type_collection = TypeClassCollection()
        data_id = id(type_collection.data)

        container = ScopeContainer(cst.Module(body=()), type_collection)
        assert id(container.type_collection.data) != data_id
