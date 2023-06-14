import re

codeblock_regex = re.compile(r"```.*?```", re.DOTALL)
link_regex = re.compile(r"!?\[[^\n\]]*\]\(\s*[^\)\s]*\s*\)")

escape_trans = str.maketrans({
        '\\': '\\\\',
        '"': '\\"',
        '\n': '\\n',
        '\r': '\\r',
        '\t': '\\t',
        '\b': '\\b',
        '\f': '\\f'
    })

def format_to_quote(x: str) -> str:
    """
    format_to_quote formats the string to a markdown quote.

    args:
        x: str - the string to be formatted
    """
    return ">"+x.replace("\n", "\n>")

def escape_special_chars(s: str) -> str:
    """
    escape_special_chars escapes the special characters in the given string to be used in a graphql query.

    args:
        s: str - the string to be escaped
    """
    return s.translate(escape_trans)
