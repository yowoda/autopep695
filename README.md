# A tool to automatically upgrade python code to the new type parameter syntax introduced in [PEP 695](https://peps.python.org/pep-0695/)

Rewriting your codebase manually to comply with PEP 695 can be very tiring and confusing, especially at a large scale as you have to keep track of all the `TypeVar`s, `ParamSpec`s, `TypeVarTuple`s used and more. This was also the motivation behind this project, which automatically rewrites any code using old type parameter syntax to the new type parameter syntax using square brackets `[]`. 

# Installation
Using `pip`:
```
pip install pep695
```
Using [uv](https://docs.astral.sh/uv/):
```
uv tool install pep695
```
Or if you want to run the tool immediately you can use:
```
uvx pep695
```

# Usage

`pep695` has 2 important commands for you to use on your codebase

## `pep695 check`
Check whether the code makes use of the new type parameter syntax. If not, informative errors are shown that describe the problem (e.g. A class inherits from `typing.Generic[T]`) and include the "proper" implementation using the concepts described in PEP 695.

`pep695 check` accepts multiple paths either pointing to a valid directory or a valid file that contains the code to be checked. A file is valid if it has one of the following extensions: `.py`, `.pyi`. Directories are traversed recursively.

You can also specify the `--silent` (`-s`) flag that silences the errors logged and only shows the number of errors reported.

## `pep695 format`
Rewrite the code to the new type parameter syntax by running the `format` subcommand. This will implement all the suggestions reported in `pep695 check`, so running `pep695 check` after `pep695 format` will not report any errors. `format` however does not require you to run `check` beforehand, it just matches its behaviour.

It is recommended to specify the `--parallel` (`-p`) flag if you're running `format` against a large codebase as the tool is written in pure python and is not optimized for speed. This way, the workload is distributed across multiple subprocesses, each spawning a new python interpreter that formats the assigned files.

# What `pep695` does and what it doesn't

`pep695` does:
- Remove assignments that instantiate `TypeVar`s, `ParamSpec`s or `TypeVarTuple`s from `typing` or `typing_extensions`
- Rewrite type alias statements that are annotated using `typing.TypeAlias` or `typing_extensions.TypeAlias` to a `type` assigment e.g.:
```py
import typing as t
StrOrInt: t.TypeAlias = str | int
```
is turned into
```py
import typing as t
type StrOrInt = str | int
```
- Rewrite class definitions that use `TypeVar`s, `ParamSpec`s or `TypeVarTuple`s to conform to PEP 695 syntax e.g.:
```py
import typing as t

K = t.TypeVar("K")
V = t.TypeVar("V")

class Map(dict[K, V]): ...
```
is rewritten into
```py
import typing as t
class Map[K, V](dict[K, V]): ...
```
- Rewrite function definitions that use `TypeVar`s, `ParamSpec`s or `TypeVarTuple`s to conform to PEP 695, as long as the type parameter is not inherited from the outer annotation scope e.g.
```py
import typing as t
from collections.abc import Callable

T = t.TypeVar("T")
P = ParamSpec("P")

def func(callback: Callable[P, T]) -> T: ...
```
is converted to
```py
import typing as t
from collections.abc import Callable

def func[T, **P](callback: Callable[P, T]) -> T: ...
```
and
```py
import typing as t

T = t.TypeVar("T")

class Collection(t.Generic[T]):
    def add(self, item: T) -> None: ...
```
is correctly converted to
```py
import typing as t

class Collection[T]():
    def add(self, item: T) -> None: ...
```
- Remove `typing.Generic` or `typing_extensions.Generic` as base and the type subscript of `typing.Protocol` or `typing_extensions.Protocol` (`class A(typing.Protocol[T])` -> `class A[T](typing.Protocol)`)
- Correctly compile arguments passed in `TypeVar`, `ParamSpec` or `TypeVarTuple` to the equivalent PEP 695 syntax e.g.:
```py
import typing as t

class Undefined: ...

T = t.TypeVar("T", str, int, default=int)
UndefinedOr: t.TypeAlias = Undefined | T
```
is compiled to
```py
import typing as t

class Undefined: ...

type UndefinedOr[T: (str, int) = int] = Undefined | T
```
- allow you to ignore specific type assignments, simply add a `# pep695-ignore` comment to the line e.g.:
```py
import typing as t

T = t.TypeVar("T") # pep695-ignore

class A(t.Generic[T]): ...
```
will remain the exact same

`pep695` does not:
- Remove unused imports once type assignments are removed, that's out of scope for this project.
- Does not neccesarily follow the style of your next best linter

It is best to format the code with a tool like [ruff](https://docs.astral.sh/ruff/) after running `pep695 format`.