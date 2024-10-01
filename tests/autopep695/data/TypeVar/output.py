# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import typing as t
from typing_extensions import TypeVar

def func[SimpleT](x: SimpleT) -> SimpleT:
    ...

def func[ConstrainedT: (str, int), BoundT: int, DefaultT = str](b: ConstrainedT, c: BoundT, d: DefaultT):
    ...

class GenericClass[SimpleT]():
    ...

class GenericClassWithMethods[DefaultT = str]():
    def somefunc(self, x: DefaultT) -> DefaultT:
        ...
        

class SomeClass:
    def somefunc[BoundT: int](self, x: BoundT) -> BoundT:
        ...

def func[SimpleT](x: SimpleT) -> SimpleT:
    class ThatCantReuseSimpleT[SimpleT]():
        a: SimpleT

def func[DefaultT = str](x: DefaultT) -> DefaultT:
    def nested_func_that_reuses_DefaultT(a: DefaultT):
        ...

class WithOverridenTypeVar:
    def IUseSimpleT[SimpleT: str](self, this: SimpleT, that: SimpleT) -> SimpleT:
        return this
    
class ThatUsesMultipleTypeVars[SimpleT, ConstrainedT: (str, int), BoundT: int, DefaultT = str](int):
    ...

def func[BoundT: int](a: BoundT):
    class SomeProtocol[BoundT: int](t.Protocol):
        def protocol_method(self, arg: BoundT) -> BoundT:
            ...

def func[IgnoredCovarianceT, IgnoredContravarianceT](a: IgnoredContravarianceT, b: IgnoredCovarianceT):
    ...

IgnoredTypeVar = TypeVar("IgnoredTypeVar") # pep695-ignore

def func(a: IgnoredTypeVar) -> IgnoredTypeVar:
    return a

def ignored_typevar_mixed[SimpleT](a: IgnoredTypeVar, b: SimpleT):
    ...

def func_with_pep695_syntax[A, SimpleT](a: A, b: SimpleT):
    ...

class WithIgnoredTypeVar(t.Generic[IgnoredTypeVar]):
    ...

class WithIgnoredTypeVarMixed[SimpleT]():
    ...

KeptT = TypeVar("KeptT")

def ignored_func(a: KeptT): # pep695-ignore
    ...

def func_that_uses_keptT[KeptT](a: KeptT):
    ...

KeptT_2 = TypeVar("KeptT_2")

class KeepsT_2(t.Generic[KeptT_2]): ... # pep695-ignore

class IgnoredClass(t.Protocol[KeptT_2]): # pep695-ignore
    def method_that_uses_KeptT_2(self, a: KeepsT_2):
        ...

class SomeClass:
    KeptT = TypeVar("KeptT") # pep695-ignore

    def func(a: KeptT): ...

class WithPEP695Syntax[A, B, SimpleT, BoundT: int](t.Protocol, ):
    ...

def func():
    def inner[ConstrainedTWithDefault: (str, int) = int](a: ConstrainedTWithDefault):
        ...

def otherfunc(a: ConstrainedTWithDefault): ...