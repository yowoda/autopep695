# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import typing as t
from typing_extensions import *

def func[**P](callback: t.Callable[P, t.Any]):
    ...

def func[**DefaultP = ...](callback: t.Callable[DefaultP, t.Any]) -> t.Callable[DefaultP, t.Any]:
    ...

def func_with_multiple_paramspecs[**P, **DefaultP = ...](a: P, b: DefaultP):
    ...

class SomeClass[**P, **DefaultP = ...](): ...