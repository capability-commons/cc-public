"""
---

id_self:                pym_test.test_restatement
guid_self:              pym_d7c92909cf9d4b91907a2e88f7ba1853
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Restatement projection tests
brief:                  |
                        Tests that two function bodies of one shape
                        are reported and two of different shapes are
                        not.
description:            |
                        Three properties over python written into a
                        temporary directory: two bodies differing only
                        in what they call things are reported as one
                        shape, a body of another shape beside them
                        adds nothing, and two identical bodies under
                        the token floor are passed over.
relation:               []

...
"""


import cc_public.restatement


SAME = '''
def first(alpha, beta):
    out = []
    for one in alpha:
        if one in beta:
            out.append(one)
        else:
            out.append(None)
    return sorted(out)


def second(left, right):
    held = []
    for each in left:
        if each in right:
            held.append(each)
        else:
            held.append(None)
    return sorted(held)
'''

OTHER = '''
def third(mapping):
    total = 0
    while total < 10:
        total = total + len(mapping)
        mapping.pop()
    try:
        return {key: value for (key, value) in mapping}
    except KeyError:
        return None
'''

SHORT = '''
def fourth(one):
    return one + 1


def fifth(two):
    return two + 1
'''


def _pairs(tmp_path, text, threshold = 0.8):
    (tmp_path / 'subject.py').write_text(text)

    return cc_public.restatement.similar([tmp_path], threshold)


def test_two_bodies_of_one_shape_are_reported(tmp_path):
    found = _pairs(tmp_path, SAME)

    assert len(found) == 1, found
    assert found[0].score == 1.0
    assert {found[0].first.split('::')[1],
            found[0].second.split('::')[1]} == {'first', 'second'}


def test_two_bodies_of_different_shapes_are_not_reported(tmp_path):
    assert _pairs(tmp_path, SAME + OTHER) == _pairs(tmp_path, SAME)


def test_a_body_under_the_floor_is_not_compared(tmp_path):
    # Two short bodies are identical and are passed over, because
    # every short body looks like every other (ddr_restated_fact).
    assert _pairs(tmp_path, SHORT) == []
