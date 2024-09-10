class ParsingError(Exception):
    """
    Error to raise if libcst fails to parse the given code
    """


class InvalidPath(Exception):
    """
    Error to raise if a path is passed that doesn't point to a valid directory or file
    """

    def __init__(self, path: str) -> None:
        self.path = path
