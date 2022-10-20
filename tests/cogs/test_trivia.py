import textwrap

import yaml
from schema import SchemaError


def test_trivia_lists():
    from redbot.cogs.trivia import InvalidListError, get_core_lists, get_list

    list_names = get_core_lists()
    assert list_names
    problem_lists = []
    for l in list_names:
        try:
            get_list(l)
        except InvalidListError as exc:
            e = exc.__cause__
            if isinstance(e, SchemaError):
                problem_lists.append((l.stem, f"SCHEMA error:\n{e!s}"))
            else:
                problem_lists.append((l.stem, f"YAML error:\n{e!s}"))

    if problem_lists:
        msg = ""
        for name, error in problem_lists:
            msg += f"- {name}:\n{textwrap.indent(error, '    ')}"
        raise TypeError("The following lists contain errors:\n" + msg)
