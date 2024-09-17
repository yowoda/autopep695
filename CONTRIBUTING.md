# How to contribute to `autopep695`
Thanks for being interested in improving autopep695, your effort is very much appreciated.

Start off by forking this repository and cloning your fork using `git clone`.

# How `autopep695` works
Here is a summary of how autopep695 works so you can get familiar with the internals:

`autopep695` uses `libcst` internally to build a CST from the given code and modify it to conform to PEP 695.

The entry point of the `autopep695` command is `autopep695.cli:main`. `autopep695/cli.py` contains the CLI-Argument Parser, setting up the subparser to parse and process individual subcommands such as `format` or `check`. It also contains the code for filtering the input paths in regards to the `--exclude`, `--extend-exclude`, `--include` and `--extend-include` flags, which are then passed to the code analyzers in `autopep695/analyzer.py`.

`autopep695/analyzer.py` contains the public python API to analyze files or code. `autopep695.analyzer.check_paths` is the equivalent of `autopep695 check`, `autopep695.analyzer.format_paths` the equivalent of `autopep695.analyzer.format_paths`. The latter has the special ability to distribute the given files across multiple processes. For this `_parallel_format_paths` is used. In addition, there are two more public functions for developers to use, which are also the base for the functions above: `format_code` and `check_code` where you can pass the code as a string.

`format_code` and `check_code` both built upon the `BaseVisitor` from `autopep695/base.py`. This is the core class of `autopep695`, responsible for processing import statements, type parameter assignments, type alias assignments, resolving type parameters from class and function definitions and transpiling them to PEP 695-like type parameters.

It does this by:
1. Keeping track of the scopes entered when visiting one of the following nodes: `libcst.Module`, `libcst.ClassDef`, `libcst.FunctionDef` and removing the most recent scope when leaving the respective node.
2. Tracking imports of the following names: `TypeVar`, `TypeVarTuple`, `ParamSpec`, `TypeAlias`, `Protocol`, `Generic` from `typing` or `typing_extensions`:
3. Finding valid type parameter assignments that contain one of the aliases for `TypeVar`, `TypeVarTuple` or `ParamSpec`. Valid as in the variable name and the `name` argument for the type parameter constructor have to match. The created type parameter is stored using one of `TypeVarSymbol`, `TypeVarTupleSymbol`, `ParamSpecSymbol` from `autopep695/symbols.py`. The symbol is only added to the current scope if the assignment does not contain a `# pep695-ignore` comment. The given assignment, if not ignored by a `pep695-ignore` comment, is immediately considered "unused".
4. Finding assignments annotated using one of the aliases for `TypeAlias`. After resolving type parameters on the right hand side of the assignment, we check whether the assignment has to be ignored or not. A `TypeAlias` annotated assignment is ignored if either:<br>
A. The assignment contains a `pep695-ignore` comment as mentioned previously<br>
B. The `unsafe` option is disabled.<br>
If one of these is true, all the type parameter assignments that are referenced in this type alias are now considered "used".
If both of these are false, the resolved type parameters are added to a new `libcst.TypeAlias` node and the names are eventually cleaned up if one of `remove_variance`, `remove_private` was specified.
5. Finding class definitions that contain type parameters in their bases. If the class should be ignored using `# pep695-ignore`, the type parameters are not added to the class scope and any referenced type parameter assignments are marked as "used".
6. Finding functions definitions that contain type parameters in the parameter annotations or the return type annotation. Functions have the ability to "inherit" type parameters from the outer scope, which is why we have to check if any of these type parameters have already been introduced. `# pep695-ignore` has the same functionality here as for class definitions.

`autopep695/check.py` extends the `BaseVisitor`'s functionality with `CheckPEP695Visitor`. It simply makes sure to generate diagnostics and produce the fancy diff output when running `autopep695 check`. `autopep695/format.py` however contains `PEP695Formatter` which extends the `BaseVisitor`'s behaviour for classes: It checks whether the bases contain one of the aliases for `Generic` and `Protocol` and removes the base completely for the former and the type subscript for the latter.

# Making your first contribution

After cloning your very own fork of `autopep695`, create a new branch where you are going to work in. Branch names should follow the following conventions:
1. `feature/*` for any new features
2. `bugfix/*` for bugfixes
3. `task/*` if your solution does not fit into either.

`autopep695` uses [`uv`](https://docs.astral.sh/uv/) for dependency management, follow the installation guide [here](https://docs.astral.sh/uv/getting-started/installation/). After installing `uv`, run `uv sync --frozen`. This will install build dependencies as well as development dependencies in the project environment. Now after making the desired changes to the code, run `uv run nox`. This will run all neccessary pipelines that also need to pass on github.

The following jobs are used in the default `nox` configuration:
- `format_fix`: Fixes formatting of the code using [`ruff`](https://docs.astral.sh/ruff/)
- `typecheck`: Strict typechecking using [`pyright`](https://github.com/microsoft/pyright)
- `slotscheck`: Correct slots usage checking using [`slotscheck`](https://github.com/ariebovenberg/slotscheck)
- `copyright`: Checks whether the copyright notice is placed in all tracked files
- `test`: Checks whether all the tests are passing using [`pytest`](https://docs.pytest.org/en/stable/)

You can run individual jobs by passing job names to `uv run nox -s` like this: `uv run nox -s typecheck`.

Make sure of all these pass before commiting! If everything works as expected, push your branch to remote and make a PR comparing the remote branch against `master`. Please note that PRs usually require issues to be created beforehand, unless the PR fixes simple typos or the change is not "issue-worthy". Keep your PRs short and focus on a single issue rather than trying to fix multiple problems at once, this makes reviewing your changes much easier and you won't have to wait as long to get your PR merged.