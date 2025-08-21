import ast


def is_valid_python(code):
    """
    Check if the given code is valid Python syntax.

    :param code: The code to check.
    :type code: str
    :return: True if the code is valid, False otherwise.
    :rtype: bool
    """
    try:
        ast.parse(code)
    except SyntaxError:
        return False
    return True
