# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import typing as t
from typing_extensions import TypeVar

SomeDefaultT = TypeVar("SomeDefaultT", default=int)

SimpleT = TypeVar("SimpleT")
ConstrainedT = TypeVar("ConstrainedT", str, int)
BoundT = TypeVar("BoundT", bound=int)
DefaultT = TypeVar("DefaultT", default=str)

def func(x: SimpleT) -> SimpleT:
    ...

def func(b: ConstrainedT, c: BoundT, d: DefaultT):
    ...

class GenericClass(t.Generic[SimpleT]):
    ...

class GenericClassWithMethods(t.Generic[DefaultT]):
    def somefunc(self, x: DefaultT) -> DefaultT:
        ...

class SomeClass:
    def somefunc(self, x: BoundT) -> BoundT:
        ...

def func(x: SimpleT) -> SimpleT:
    class ThatCantReuseSimpleT(t.Generic[SimpleT]):
        a: SimpleT

def func(x: DefaultT) -> DefaultT:
    def nested_func_that_reuses_DefaultT(a: DefaultT):
        ...

class WithOverridenTypeVar:
    SimpleT = t.TypeVar("SimpleT", bound=str)

    def IUseSimpleT(self, this: SimpleT, that: SimpleT) -> SimpleT:
        return this
    
class ThatUsesMultipleTypeVars(t.Generic[SimpleT, ConstrainedT, BoundT, DefaultT], int):
    ...


def func(a: BoundT):
    class SomeProtocol(t.Protocol[BoundT]):
        def protocol_method(self, arg: BoundT) -> BoundT:
            ...

IgnoredCovarianceT = TypeVar("IgnoredCovarianceT", covariant=True)
IgnoredContravarianceT = TypeVar("IgnoredContravarianceT", contravariant=True)

def func(a: IgnoredContravarianceT, b: IgnoredCovarianceT):
    ...

IgnoredTypeVar = TypeVar("IgnoredTypeVar") # pep695-ignore

def func(a: IgnoredTypeVar) -> IgnoredTypeVar:
    return a

def ignored_typevar_mixed(a: IgnoredTypeVar, b: SimpleT):
    ...

def func_with_pep695_syntax[A](a: A, b: SimpleT):
    ...

class WithIgnoredTypeVar(t.Generic[IgnoredTypeVar]):
    ...

class WithIgnoredTypeVarMixed(t.Generic[SimpleT, IgnoredTypeVar]):
    ...

KeptT = TypeVar("KeptT")

def ignored_func(a: KeptT): # pep695-ignore
    ...

def func_that_uses_keptT(a: KeptT):
    ...

KeptT_2 = TypeVar("KeptT_2")

class KeepsT_2(t.Generic[KeptT_2]): ... # pep695-ignore

class IgnoredClass(t.Protocol[KeptT_2]): # pep695-ignore
    def method_that_uses_KeptT_2(self, a: KeepsT_2):
        ...

class SomeClass:
    KeptT = TypeVar("KeptT") # pep695-ignore

    def func(a: KeptT): ...

class WithPEP695Syntax[A, B](t.Protocol[BoundT], t.Generic[SimpleT]):
    ...

def func():
    ConstrainedTWithDefault = TypeVar("ConstrainedTWithDefault", str, int, default=int)

    def inner(a: ConstrainedTWithDefault):
        ...

def otherfunc(a: ConstrainedTWithDefault): ...

UnusedT = TypeVar("UnusedT")