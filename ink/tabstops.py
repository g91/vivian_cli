"""Port of src/ink/tabstops.ts."""
from .stringWidth import stringWidth
from .termio.tokenize import createTokenizer

DEFAULT_TAB_INTERVAL = 8


def expandTabs(text: str, interval: int = DEFAULT_TAB_INTERVAL) -> str:
    if "\t" not in text:
        return text

    tokenizer = createTokenizer()
    tokens = tokenizer.feed(text)
    tokens.extend(tokenizer.flush())

    result = ""
    column = 0

    for token in tokens:
        if token.type == "sequence":
            result += token.value
        else:
            parts = token.value.split("\t")
            for i, part in enumerate(parts):
                if i > 0:
                    spaces = interval - (column % interval)
                    result += " " * spaces
                    column += spaces
                # Handle embedded newlines
                subparts = part.split("\n")
                for j, sub in enumerate(subparts):
                    if j > 0:
                        result += "\n"
                        column = 0
                    result += sub
                    column += stringWidth(sub)

    return result


expand_tabs = expandTabs
