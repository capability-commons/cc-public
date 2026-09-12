"""
---

id_self:                pym_cc_public.restatement
guid_self:              pym_4ea5de3cb15c45bbb2e57d18d1282bbe
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Restatement projection
brief:                  |
                        Function bodies that are the same shape with
                        different names, found by a fingerprint of the
                        syntax tree.
description:            |
                        Two function bodies are one shape when their
                        syntax trees agree once local names are
                        normalised to the order in which they first
                        appear and constants are reduced to their
                        types. The projection fingerprints every body
                        long enough to compare, as the set of
                        overlapping windows of its token sequence, and
                        reports every pair that shares at least a
                        given proportion of those windows. What it
                        finds is one fact written twice in code, which
                        no field a check can read holds. The design
                        decision ddr_restated_fact covers that class
                        by declaration where both sides are in the
                        tree, and by this projection where they are
                        not.
relation:               []

...
"""


import ast
import itertools
import pathlib
import typing


SHINGLE   = 4            # tokens per shingle, the window a pair must share
FLOOR     = 24           # tokens a body needs before it is compared
THRESHOLD = 0.8          # the similarity a pair is reported at
SUFFIX    = '*.py'


# -----------------------------------------------------------------------------
class Similar(typing.NamedTuple):
    """
    Two function bodies of the same shape: how alike the two are,
    between nothing and one, how long the shorter of them is in
    tokens, and where each is defined.

    """

    score:  float
    length: int
    first:  str
    second: str


# -----------------------------------------------------------------------------
class Body(typing.NamedTuple):
    """
    One function body as it is compared: where it is defined, the
    shingles of its normalised token sequence, and how long that
    sequence is.

    """

    name:   str
    piece:  frozenset[tuple[str, ...]]
    length: int


# -----------------------------------------------------------------------------
def similar(list_path, threshold = THRESHOLD):
    """
    Return every pair of function bodies at or above threshold, the
    most alike first.

    A body is normalised before it is compared: a local name becomes
    the order it first appears in, a constant becomes its type, and a
    docstring is dropped, so that two bodies differing only in what
    they call things are one shape (ddr_restated_fact).

    """

    held = []
    for one in list_path:
        held.extend(_body(pathlib.Path(one)))

    out = []
    for (first, second) in itertools.combinations(held, 2):
        score = _alike(first.piece, second.piece)
        if score >= threshold:
            out.append(Similar(score  = score,
                               length = min(first.length, second.length),
                               first  = first.name,
                               second = second.name))

    return sorted(out, key = lambda one: (-one.score, -one.length,
                                          one.first, one.second))


# -----------------------------------------------------------------------------
def _alike(first, second):
    """
    Return the proportion of shingles the two share, of those either
    holds.

    """

    if not first or not second:
        return 0.0

    return len(first & second) / len(first | second)


# -----------------------------------------------------------------------------
def _body(path):
    """
    Yield one Body for every function under path long enough to
    compare.

    """

    for filepath in sorted(path.rglob(SUFFIX)) if path.is_dir() else [path]:

        try:
            parsed = ast.parse(filepath.read_text(encoding = 'utf-8'))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue

        for one in ast.walk(parsed):

            if not isinstance(one, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            token = _token([statement for statement in one.body
                            if not _is_docstring(statement)])
            if len(token) < FLOOR:
                continue

            yield Body(name   = '{p}::{n}'.format(p = filepath, n = one.name),
                       piece  = _shingle(token),
                       length = len(token))


# -----------------------------------------------------------------------------
def _is_docstring(statement):
    """
    Return whether a statement is a bare string, which a docstring is.

    """

    return (isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str))


# -----------------------------------------------------------------------------
def _shingle(token):
    """
    Return the set of overlapping windows of the token sequence.

    """

    return frozenset(tuple(token[i:i + SHINGLE])
                     for i in range(max(len(token) - SHINGLE + 1, 0)))


# -----------------------------------------------------------------------------
def _token(list_statement):
    """
    Return the preorder token sequence of a body, local names
    normalised to the order they first appear in.

    An attribute keeps its name, since what is reached through an
    object is what the body does; a local name and an argument do not,
    since two bodies calling one thing by two names are one shape.

    """

    out  = []
    seen = {}

    def normalised(text):
        return seen.setdefault(text, 'n{n}'.format(n = len(seen)))

    def walk(node):
        if isinstance(node, ast.Name):
            out.append('Name:' + normalised(node.id))
        elif isinstance(node, ast.arg):
            out.append('arg:' + normalised(node.arg))
        elif isinstance(node, ast.Attribute):
            out.append('Attribute:' + node.attr)
        elif isinstance(node, ast.Constant):
            out.append('Constant:' + type(node.value).__name__)
        else:
            out.append(type(node).__name__)
        for child in ast.iter_child_nodes(node):
            walk(child)

    for statement in list_statement:
        walk(statement)

    return out
