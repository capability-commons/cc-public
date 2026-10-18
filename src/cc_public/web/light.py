"""
---

id_self:                pym_cc_public.web.light
guid_self:              pym_51384e356cdb4c08aafcffedb4aa973e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Lighting of chains in a diagram
brief:                  |
                        Light the chain of an argument that reaches a
                        part of a diagram, while that part is hovered
                        over or pinned, and dim the rest.
description:            |
                        Each chain has a key. A mark in the chain
                        carries the key as a class, and, if the chain
                        shades it, the key and its net effect on the
                        part the chain reaches. A mark that triggers
                        the chain carries a class that names the key,
                        and an element with the key as its id pins the
                        chain while it is the target of the address,
                        so no script is needed. A chain may also have
                        an alias: the id of an element elsewhere on
                        the page, such as a decision shown in the
                        matrix, which pins the chain while it is the
                        target, and marks elsewhere light it while
                        they are hovered over. Hovering wins over a
                        pin. While any chain is lit, every mark that
                        can be dimmed and is outside it is dimmed.
relation:               []

...
"""


ROLE_FOR          = 'for'
ROLE_AGAINST      = 'against'
SIGN_MIXED        = 'mixed'
CSS_TRIGGER       = 'lit-trigger'
CSS_ANCHOR        = 'lit-anchor'
CSS_DIMS          = 'dims'
CSS_SHOW          = 'lit-show'
PREFIX_HOVER      = 'hover-'
PREFIX_SHOW       = 'show-'
DELIM_SIGN        = '--'
KEY_UNPIN         = 'unpin'


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
    Return the classes of a mark from the keys of the chains it is in,
    each with the net effects that shade it there: none, one, or both,
    which is mixed.

    """

    list_css = []
    for (key, set_sign) in sorted(map_sign.items()):
        list_css.append(key)
        if len(set_sign) == 1:
            list_css.append(key + DELIM_SIGN + next(iter(set_sign)))
        elif set_sign:
            list_css.append(key + DELIM_SIGN + SIGN_MIXED)
    return list_css


# -----------------------------------------------------------------------------
def add(map_sign: dict[str, set[str]], key: str, sign: str | None) -> None:
    """
    Put the mark of map_sign in the chain at key, shaded by sign unless
    it is None.

    """

    set_sign = map_sign.setdefault(key, set())
    if sign is not None:
        set_sign.add(sign)


# -----------------------------------------------------------------------------
def trigger(key: str) -> str:
    """
    Return the classes of a mark that lights the chain at key while it
    is hovered over.

    """

    return '{trigger} {hover}{key}'.format(trigger = CSS_TRIGGER, hover = PREFIX_HOVER, key = key)


# -----------------------------------------------------------------------------
def alias(id_decision: str, role: str | None = None) -> str:
    """
    Return the id that shows id_decision in the matrix and pins its
    chains in the diagrams: all of them, or with role only those that
    reach it with that role.

    """

    return id_decision if role is None else id_decision + DELIM_SIGN + role


# -----------------------------------------------------------------------------
def show(alias: str) -> str:
    """
    Return the classes of a mark outside the diagrams that lights the
    chains of alias in them while it is hovered over.

    """

    return '{show} {prefix}{alias}'.format(show = CSS_SHOW, prefix = PREFIX_SHOW, alias = alias)


# -----------------------------------------------------------------------------
def style(scope: str, list_key: list[str], map_alias: dict[str, str] | None = None) -> str:
    """
    Return the rules that light the chain at each key in the diagram
    scope while a trigger of it, or a mark that shows its alias in
    map_alias, is hovered over, or while its anchor or its alias is the
    target of the address and no such mark is hovered over. A lit mark
    shows in full; one shaded for a net effect takes the custom
    properties --lit (a fill) and --lit-ink (an ink) of that effect.

    """

    map_alias = map_alias or {}
    list_rule = []
    for key in list_key:
        list_when = ['{scope} svg:has(.{hover}{key}:hover)',
                     (':root:not(:has(.{show}:hover)) '
                      '{scope} svg:has(#{key}:target):not(:has(.{trigger}:hover))')]
        if key in map_alias:
            list_when += [':root:has(.{prefix}{alias}:hover) {scope} svg',
                          (':root:has(#{alias}:target):not(:has(.{show}:hover)) '
                           '{scope} svg:not(:has(.{trigger}:hover))')]
            rule = (':is(:root:has(#{alias}:target), :root:has(.{prefix}{alias}:hover)) '
                    '{scope} svg .{dims} {{ opacity: var(--dim); }}')
            list_rule.append(rule.format(alias  = map_alias[key],
                                         prefix = PREFIX_SHOW,
                                         scope  = scope,
                                         dims   = CSS_DIMS))
        when = ':is({list_when})'.format(list_when = ', '.join(list_when)).format(
            scope   = scope,
            hover   = PREFIX_HOVER,
            key     = key,
            trigger = CSS_TRIGGER,
            show    = CSS_SHOW,
            prefix  = PREFIX_SHOW,
            alias   = map_alias.get(key))
        list_rule.append('{when} .{key} {{ opacity: 1; }}'.format(when = when, key = key))
        for sign in (ROLE_FOR, ROLE_AGAINST, SIGN_MIXED):
            rule = ('{when} .{key}{delim}{sign} '
                    '{{ --lit: var(--net-{sign}); --lit-ink: var(--ink-{sign}); }}')
            list_rule.append(rule.format(when = when, key = key, delim = DELIM_SIGN, sign = sign))
    return '\n'.join(list_rule)
