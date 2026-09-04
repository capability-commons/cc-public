"""
---

id_self:                pym_cc_public.workflow.generate
guid_self:              pym_a86fa5f35bc04b99b229b128907d8adf
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Generator
brief:                  |
                        Turn a prompt and some inputs into the text of
                        the fields of one item.
description:            |
                        A generator answers with text for named fields
                        and nothing else. The tool has already made
                        the item and decides where the text goes.
                        Asked for a slug, it may also propose the
                        readable name of a new item.

...
"""


import typing


ID_MODEL_NULL = 'null'
FIELD_SLUG    = 'slug'
INPUT_NONE    = 'request'


# -----------------------------------------------------------------------------
class Generator(typing.Protocol):
    """
    The one thing a generator does.

    """

    id_model: str

    def produce(self, prompt, map_input, list_field, want_slug) -> dict:
        ...


# -----------------------------------------------------------------------------
class NullGenerator:
    """
    A generator that produces nothing, for a dry run.

    """

    id_model = ID_MODEL_NULL

    def produce(self, prompt, map_input, list_field, want_slug):
        return {}


# -----------------------------------------------------------------------------
class DspyGenerator:
    """
    A generator that puts the prompt to a language model.

    """

    def __init__(self, id_model):

        import dspy

        self.id_model = id_model
        self._lm      = dspy.LM(id_model, cache = False)

    # -------------------------------------------------------------------------
    def produce(self, prompt, map_input, list_field, want_slug):
        """
        Return {field: text} for the fields asked for, and slug if wanted.

        The signature is built for the call: the input ports are its
        inputs and the empty fields its outputs, so the model answers
        exactly the question the item leaves open.

        """

        import dspy

        list_input  = list(map_input) or [INPUT_NONE]
        list_output = list(list_field) + ([FIELD_SLUG] if want_slug else [])
        text        = ', '.join(list_input) + ' -> ' + ', '.join(list_output)

        signature = dspy.Signature(text, prompt + (
            '\n\nAnswer each output field with plain prose for that field '
            'alone. ' +
            ('slug is a short lowercase name of letters, digits and '
             'underscores for the item as a whole, beginning with a letter.'
             if want_slug else '')))

        kwargs = dict(map_input) or {INPUT_NONE: prompt}

        with dspy.context(lm = self._lm):
            answer = dspy.Predict(signature)(**kwargs)

        return {field: str(getattr(answer, field, '') or '')
                for field in list_output}


# -----------------------------------------------------------------------------
def build(id_model):
    """
    Return the generator the named model asks for.

    """

    if not id_model or id_model == ID_MODEL_NULL:
        return NullGenerator()

    return DspyGenerator(id_model)
