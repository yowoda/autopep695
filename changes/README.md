This directory contains the documentation of changes that have been made since the last release of `autopep695`. This happens in form of markdown files that should be added and then built using [`towncrier`](https://towncrier.readthedocs.io/en/stable/index.html). If you are making a change that is worthy of being documented and mentioned in the changelog for the next release, follow these steps:

## 1. Choose the type that summarizes your change
- `breaking` - a breaking change
- `removal` - removal of a feature
- `deprecation` - a deprecation
- `feature` - addition of a feature
- `bugfix` - a bugfix
- `doc` - notable changes to the documentation
- `misc` - miscellaneous changes that do not fit the types above

## 2. Create a file that documents the change in your PR and your change only
The file name should match the following pattern: `<pr-number>.<type>.md`. Now it's hard to specify a PR number before creating the PR itself, so there are 2 options:
1. You guess the PR number by adding 1 to the last issue number
2. You create the file after opening the PR

The file content should be the documentation of your change.

You can also run `uv run towncrier create --content "documentation for your change" <pr-number>.<type>.md` if you prefer using the command line.

**Example:** ``uv run towncrier create --content "Format `TypeAlias` annotated assignments to `type`-statements" 1.feature.md``

As already mentioned, not every change is worthy of being documented, for example typos do not require documentation. If you think that your change fits into that category, ask a maintainer to add the `skip-changelog-check` label so the github pipeline is skipped.