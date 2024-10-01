# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import typing as t
from typing_extensions import TypeAlias

from typing import TypeAlias as AliasTypeHint

type Alias = t.Union[str, int]

type NoneOr[T] = t.Optional[T]

type StringifiedAlias = None

class SomeClass:
    type alias[T: (str, int)] = T

type somealias = str | int

ignored_alias: TypeAlias = None # pep695-ignore

IgnoredT = t.TypeVar("IgnoredT") # pep695-ignore

type alias_with_ignored_param = IgnoredT