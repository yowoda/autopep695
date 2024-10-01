def remove_empty_lines(text: str) -> str:
    lines = text.splitlines()
    return "\n".join(
        line for line in lines
        if line.strip()
    )