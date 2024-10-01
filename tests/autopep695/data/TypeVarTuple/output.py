# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import typing as t
from typing_extensions import TypeVarTuple, Unpack

def func[*As](a: tuple[Unpack[As]]):
    ...

def func[*Ts = Unpack[tuple[int, ...]]](a: tuple[str, Unpack[Ts]]):
    ...

def func_with_multiple_tvartuples[*As, *Ts = Unpack[tuple[int, ...]]](a: tuple[Unpack[As]], b: tuple[Unpack[Ts]]):
    ...

class SomeClass[*Ts = Unpack[tuple[int, ...]]](t.Protocol):
    ...