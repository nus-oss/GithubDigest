import re
import string

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
    return x.replace("\n", "\n>")

def binary_search(getter_fn: callable, start: int, end: int) -> int:
    """
    binary_search performs a binary search to find the largest index i such that getter_fn(i) is true.

    args:
        getter_fn: callable - a function that takes an index i checks if the condition is satisfied
        target: int - the target value
        start: int - the start index
        end: int - the end index
    """

    if start == end:
        return start

    mid = (start + end) // 2

    if getter_fn(mid):
        return binary_search(getter_fn, mid+1, end)
    else:
        return binary_search(getter_fn, start, mid)
    
def build_prefix_sum(arr: list[int]) -> list[int]:
    """
    build_prefix_sum builds a prefix sum array from the given array.

    args:
        arr: list[int] - the array to be converted
    """

    prefix_sum = [0 for _ in range(len(arr)+1)]
    for i in range(len(arr)):
        prefix_sum[i+1] = prefix_sum[i] + arr[i]
    return prefix_sum

def escape_special_chars(s: str) -> str:
    """
    escape_special_chars escapes the special characters in the given string to be used in a graphql query.

    args:
        s: str - the string to be escaped
    """
    return s.translate(escape_trans)

def find_all_code_blocks(comment: str) -> list[tuple[int, int]]:
    """
    find_all_code_blocks finds all code blocks in the given comment.

    args:
        comment: str - the comment to be searched
    """

    ret = []
    start = 0
    while True:
        start = comment.find("```", start)
        if start == -1:
            break
        end = comment.find("```", start+3)
        if end == -1:
            break
        ret.append((start, end+3))
        start = end+3
    return ret

def convert_comment_to_ignore_values(comment: str) -> tuple[str, list[tuple[int, int]]]:
    """
    Finds all
    - markdown links
    - markdown images

    and add their index range to the ignore list as a tuple.

    args:
        comment: str - the comment to be converted
    """
    
    comment = ">" + comment.strip()
    link_blocks: list[tuple[int,int]] = []
    formatted_text_list: list[str] = []
    last_end_index = 0
    new_end_index = 0

    for matched_link in link_regex.finditer(comment):
        i, j = matched_link.span() # pos of link in original comment
        link_txt = matched_link.group()
        formatted_text_list.append(format_to_quote(comment[last_end_index:i]))
        new_end_index += len(formatted_text_list[-1])
        link_blocks.append((new_end_index, new_end_index + len(link_txt)))
        new_end_index += len(link_txt)
        formatted_text_list.append(link_txt)
        last_end_index = j
    
    formatted_text_list.append(format_to_quote(comment[last_end_index:]))

    return "".join(formatted_text_list), link_blocks

def update_counter_arr(count_arr: list[int], size: int, ignores:list[tuple[int, int]]) -> None:
    """
    Updates the counter array with the given size and ignores.
    Elements inside the ignore range will be treated as a single character of that size
    """
    assert size <= len(count_arr)
    i = 0
    for (start, end) in ignores:
        for j in range(i, start):
            count_arr[j] += 1
        count_arr[end - 1] += end - start # this index denotes a the range of elements as a single character
        i = end
    if i < size:
        for j in range(i, size):
            count_arr[j] += 1

