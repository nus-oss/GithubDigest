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

def replace_references(x: str) -> str:
    """
    replace_references replaces all @ sign in the given string with a placeholder ＠ which will
    not trigger Github's markdown parser to reference the actual user.
    """
    return x.replace("@", "＠")

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
