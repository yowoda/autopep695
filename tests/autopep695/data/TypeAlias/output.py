# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import typing_extensions as t

Alias: t.TypeAlias = str 

UsedT = t.TypeVar("UsedT")

AliasThatUsesT: t.TypeAlias = UsedT

def func[UsedT](x: UsedT) -> UsedT:
    ...