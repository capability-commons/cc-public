"""
---

id_self:                pym_cctool.web.light
guid_self:              pym_51384e356cdb4c08aafcffedb4aa973e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Lighting of chains across a page
brief:                  |
                        Light the chain of an argument that reaches a
                        part of a diagram or of the decision matrix,
                        while a mark of it is hovered over or it is
                        pinned, and dim the rest.
description:            |
                        Each chain has a name that is the same
                        everywhere on the page: the id of an option,
                        concern or annotation, or of the part of an
                        option or annotation that one role reaches. A
                        mark in the chain carries the name as a class,
                        and, if the chain shades it, the name with its
                        net effect on what the chain reaches. A mark
                        that shows the chain carries a class that
                        names it, and lights the chain in every
                        diagram and in the matrix while it is hovered
                        over. The element whose id is the name pins
                        the chain while it is the target of the
                        address, so no script is needed. Hovering wins
                        over a pin. While a chain is lit, each region
                        it reaches, a diagram or the matrix, dims
                        every mark in it outside the chain; how a mark
                        dims is up to its class, and is set in
                        review.css.
edge:                   []

...
"""


import string
import typing

import htpy


ROLE_FOR          = 'for'
ROLE_AGAINST      = 'against'
SIGN_MIXED        = 'mixed'
GLYPH_FOR         = '✓'
GLYPH_AGAINST     = '✗'
CSS_DIMS          = 'dims'
CSS_MUTES         = 'mutes'
CSS_FADES         = 'fades'
CSS_REGION        = 'lit-region'
CSS_SHOW          = 'lit-show'
CSS_PIN           = 'lit-pin'
PREFIX_LIT        = 'lit-'
PREFIX_SHOW       = 'show-'
DELIM_ROLE        = '--'
KEY_UNPIN         = 'unpin'

# The characters a name keeps in a style rule. Any other is written as
# a CSS escape of its code point, so that no id can end the rule, the
# style element, or a format of the rule.
#
SET_PLAIN         = frozenset(string.ascii_letters + string.digits + '-_')


# -----------------------------------------------------------------------------
class _Css(str):
    """
    Style rules written into a page as they are: htpy escapes text, and
    a rule may hold characters that escaping would change.

    """

    def __html__(self) -> str:
        return str(self)


# -----------------------------------------------------------------------------
def times(role_first: str, role_second: str) -> str:
    """
    Return the net effect of role_second carried through role_first: a
    challenge of a challenge is support.

    """

    return ROLE_FOR if (role_first == ROLE_FOR) == (role_second == ROLE_FOR) else ROLE_AGAINST


# -----------------------------------------------------------------------------
def css(map_sign: dict[str, set[str]]) -> list[str]:
    """
    Return the classes of a mark from the names of the chains it is in,
    each with the net effects that shade it there: none, one, or both,
    which is mixed.

    """

    list_css = []
    for (name, set_sign) in sorted(map_sign.items()):
        list_css.append(PREFIX_LIT + name)
        if len(set_sign) == 1:
            list_css.append(_shade(next(iter(set_sign)), name))
        elif set_sign:
            list_css.append(_shade(SIGN_MIXED, name))
    return list_css


# -----------------------------------------------------------------------------
def add(map_sign: dict[str, set[str]], name: str, sign: str | None) -> None:
    """
    Put the mark of map_sign in the chain called name, shaded by sign
    unless it is None.

    """

    set_sign = map_sign.setdefault(name, set())
    if sign is not None:
        set_sign.add(sign)


# -----------------------------------------------------------------------------
def chain(id_item: str, role: str | None = None) -> str:
    """
    Return the name of the chains into id_item: all of them, or with
    role only those that reach it with that role.

    """

    return id_item if role is None else id_item + DELIM_ROLE + role


# -----------------------------------------------------------------------------
def show(name: str) -> str:
    """
    Return the classes of a mark that lights the chain called name, in
    every diagram and in the matrix, while it is hovered over.

    """

    return '{show} {prefix}{name}'.format(show = CSS_SHOW, prefix = PREFIX_SHOW, name = name)


# -----------------------------------------------------------------------------
def pins(list_name: list[str]) -> typing.Any:
    """
    Return an element for each name in list_name, with the name as its
    id, that pins the chain while it is the target of the address. A
    name that is already the id of something on the page needs none.

    """

    return htpy.div(class_ = 'lit-pins', hidden = True)[
        [htpy.i(id = name, class_ = CSS_PIN) for name in list_name]]


# -----------------------------------------------------------------------------
def style(list_name: list[str]) -> typing.Any:
    """
    Return the rules that light the chain called each name in list_name
    while a mark that shows it is hovered over, or while the element
    with the name as its id is the target of the address and no mark
    that shows a chain is hovered over. A lit mark is in full; one
    shaded for a net effect takes the custom properties --lit (a fill)
    and --lit-ink (an ink) of that effect. Each region the chain
    reaches is away from the rest, and a mark that shows the chain is
    at it.

    """

    list_rule = []
    for name in list_name:
        ident       = _escaped(name)
        when        = (':root:is(:has(.{prefix}{name}:hover), '
                       ':has(#{name}:target):not(:has(.{show}:hover)))').format(
                           prefix = PREFIX_SHOW,
                           name   = ident,
                           show   = CSS_SHOW)
        list_nested = ['& .{lit}{name} {{ --lit-on: 1; }}'.format(lit = PREFIX_LIT, name = ident),
                       '& .{region}:has(.{lit}{name}) {{ --lit-away: 1; }}'.format(
                           region = CSS_REGION,
                           lit    = PREFIX_LIT,
                           name   = ident),
                       '& .{prefix}{name} {{ --lit-at: 1; }}'.format(prefix = PREFIX_SHOW,
                                                                     name   = ident)]
        list_nested += ['& .{shade} {{ --lit: var(--net-{sign}); '
                        '--lit-ink: var(--ink-{sign}); }}'.format(
                            shade = _escaped(_shade(sign, name)),
                            sign  = sign)
                        for sign in (ROLE_FOR, ROLE_AGAINST, SIGN_MIXED)]
        list_rule.append('{when} {{ {body} }}'.format(when = when, body = ' '.join(list_nested)))
    return htpy.style[_Css('\n'.join(list_rule))]


# -----------------------------------------------------------------------------
def _escaped(name: str) -> str:
    """
    Return name as a style rule writes it: each character but a letter,
    a digit, - and _ as the CSS escape of its code point.

    """

    return ''.join(char if char in SET_PLAIN else '\\{code:x} '.format(code = ord(char))
                   for char in name)


# -----------------------------------------------------------------------------
def _shade(sign: str, name: str) -> str:
    """
    Return the class of a mark that the chain called name shades with
    sign.

    """

    return '{lit}{sign}-{name}'.format(lit = PREFIX_LIT, sign = sign, name = name)
