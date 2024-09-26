v1.1.2 (2024-09-26)

### Features

- Users are now encouraged to report internal errors on GitHub by creating issue template hyperlinks with error-related information already filled out. ([#13](https://github.com/yowoda/autopep695/issues/13))
- Stringified `TypeAlias` annotations (`Alias: "TypeAlias" = str`) are now supported. ([#15](https://github.com/yowoda/autopep695/issues/15))
- Empty type parameter constructors such as `TypeVar()` are now detected and reported.
