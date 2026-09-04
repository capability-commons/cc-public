"""
---

id_self:                pym_cc_public.path
guid_self:              pym_e24ddb2009814f23aef8b97317e013d5
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Paths
brief:                  |
                        Name a place inside a document, and select
                        places by pattern.
description:            |
                        A path is field names joined by full stops,
                        with a bare integer where the step is into a
                        list:

                          table.t_type.relation.0.guid_target

                        The empty path is the document itself.

                        A pattern is a path in which a step may be a
                        star, matching any one step, or a double star,
                        matching any number of steps including none.

                        One notation serves both, so a path read in a
                        report can be pasted into a pattern without
                        translation.

...
"""


DELIM_PATH = '.'

STEP_ONE   = '*'
STEP_ANY   = '**'

# Returned in place of a value that a selection removes, since None is
# a value a document may legitimately hold.
#
DROP       = object()


# -----------------------------------------------------------------------------
def join(path, step):
    """
    Return path with step appended.

    A step that itself contains the delimiter -- a key such as
    draft.output.record -- is wrapped in double quotes, so that the
    path it appears in still splits back into the same steps.

    """

    step = str(step)

    if DELIM_PATH in step:
        step = '"' + step + '"'

    return step if not path else path + DELIM_PATH + step


# -----------------------------------------------------------------------------
def concat(path, other):
    """
    Return path followed by other, both of them paths.

    join appends one step; this appends every step of another path,
    so that a path into an item and a path within it make one path.

    """

    out = path

    for step in split(other):
        out = join(out, step)

    return out


# -----------------------------------------------------------------------------
def split(path):
    """
    Return the steps of path.

    A step wrapped in double quotes is one step whatever it contains.

    """

    if not path:
        return []

    list_step = []
    step      = ''
    is_quoted = False

    for char in path:
        if char == '"':
            is_quoted = not is_quoted
        elif char == DELIM_PATH and not is_quoted:
            list_step.append(step)
            step = ''
        else:
            step += char

    list_step.append(step)

    return list_step


# -----------------------------------------------------------------------------
def is_match(pattern, path):
    """
    Return whether path matches pattern.

    """

    return _is_match(split(pattern), split(path))


# -----------------------------------------------------------------------------
def is_match_any(tuple_pattern, path):
    """
    Return whether path matches any of the patterns.

    """

    return any(is_match(pattern, path) for pattern in tuple_pattern)


# -----------------------------------------------------------------------------
def _is_match(list_step_pattern, list_step):
    """
    Return whether the steps of a path match the steps of a pattern.

    """

    if not list_step_pattern:
        return not list_step

    step = list_step_pattern[0]

    if step == STEP_ANY:
        return any(_is_match(list_step_pattern[1:], list_step[idx:])
                        for idx in range(len(list_step) + 1))

    if not list_step:
        return False

    if step in (STEP_ONE, list_step[0]):
        return _is_match(list_step_pattern[1:], list_step[1:])

    return False


# -----------------------------------------------------------------------------
def select(node, tuple_include = (), tuple_exclude = (), path = ''):
    """
    Return node with only the places the patterns select.

    A place is kept where some include pattern matches it, or where an
    include pattern matches something under it. An empty include keeps
    everything. An exclude removes a place and everything under it, and
    is applied after the include, so a narrow exclusion can be written
    against a broad inclusion.

    Returns DROP where nothing under this place survives, since a
    caller must be able to tell an empty result from a null value.

    """

    if is_match_any(tuple_exclude, path):
        return DROP

    if (not tuple_include) or is_match_any(tuple_include, path):
        return _strip(node, tuple_exclude, path)

    if isinstance(node, dict):

        node_out = {}

        for (key, value) in node.items():
            child = select(value, tuple_include, tuple_exclude,
                           join(path, key))
            if child is not DROP:
                node_out[key] = child

        return node_out or DROP

    if isinstance(node, list):

        list_out = []

        for (idx, value) in enumerate(node):
            child = select(value, tuple_include, tuple_exclude,
                           join(path, idx))
            if child is not DROP:
                list_out.append(child)

        return list_out or DROP

    return DROP


# -----------------------------------------------------------------------------
def write(node, path, value):
    """
    Set value at path within node, and return node.

    Every step but the last must already exist: a path into a missing
    parent is a mistake to report, not a structure to invent. The last
    step is created where absent. A sequence step is an index, and may
    be one past the end to append.

    """

    list_step = split(path)

    if not list_step:
        raise KeyError('An empty path names the whole node, which cannot '
                       'be replaced in place.')

    parent = node

    for step in list_step[:-1]:
        parent = _child(parent, step, path)

    last = list_step[-1]

    if isinstance(parent, list):
        index = int(last)
        if index == len(parent):
            parent.append(value)
        else:
            parent[index] = value
    else:
        parent[last] = value

    return node


# -----------------------------------------------------------------------------
def _child(node, step, path):
    """
    Return the child of node at step, or raise naming the path.

    """

    try:
        if isinstance(node, list):
            return node[int(step)]
        return node[step]
    except (KeyError, IndexError, ValueError, TypeError):
        raise KeyError('No {step} at {path}.'.format(step = step,
                                                    path = path)) from None


# -----------------------------------------------------------------------------
def _strip(node, tuple_exclude, path):
    """
    Return node with the excluded places removed.

    """

    if isinstance(node, dict):
        return {key: _strip(value, tuple_exclude, join(path, key))
                    for (key, value) in node.items()
                    if  not is_match_any(tuple_exclude, join(path, key))}

    if isinstance(node, list):
        return [_strip(value, tuple_exclude, join(path, idx))
                    for (idx, value) in enumerate(node)
                    if  not is_match_any(tuple_exclude, join(path, idx))]

    return node
