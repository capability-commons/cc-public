"""
---

id_self:                pym_test.control_adapter
guid_self:              pym_32350f5cc3df47cf902c7df31f757156
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Adapter control functions
brief:                  |
                        Test functions written to produce each outcome
                        the pytest adapter must tell apart, run only
                        by the adapter and never by the suite.
description:            |
                        The adapter maps what pytest reports onto an
                        execution outcome and a conformance result,
                        and every verdict this repository records
                        passes through that mapping. These controls
                        exercise it against a real pytest run. The
                        suite does not collect this file. The adapter
                        reaches each function by an explicit node id.
relation:               []

...
"""


import time

import pytest


@pytest.fixture
def unmakeable():
    """
    A fixture that cannot be made, so setup errors.

    """

    raise RuntimeError('the fixture could not be made')


@pytest.fixture
def unbreakable():
    """
    A fixture that fails as it is torn down, after the call has passed.

    """

    yield
    raise RuntimeError('the fixture could not be torn down')


def test_passes():
    """
    ---

    id_self:                pyf_test.control_adapter.test_passes
    guid_self:              pyf_d3f2de008ddc4fd888662292bd484cff
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A control that passes
    brief:                  |
                            A control that passes, so the adapter reads
                            completed and passed.
    description:            |
                            When this control is run through the adapter,
                            the adapter must read completed and passed.
                            Every other control is defined by how its
                            outcome differs from this one.
    relation:               []

    ...
    """

    assert True


def test_fails():
    """
    ---

    id_self:                pyf_test.control_adapter.test_fails
    guid_self:              pyf_79430ce55df34feab08ac8c92e11de2c
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A control that fails
    brief:                  |
                            A control that fails its assertion, so the
                            adapter reads completed and failed, and
                            carries the assertion into what it observed.
    description:            |
                            When this control is run through the adapter,
                            the adapter must read completed and failed.
                            The text of the failed assertion must reach
                            the observation, because a report quotes the
                            assertion.
    relation:               []

    ...
    """

    observed = 1
    assert observed == 2, 'the control that is meant to fail'


def test_errors_in_setup(unmakeable):
    """
    ---

    id_self:                pyf_test.control_adapter.test_errors_in_setup
    guid_self:              pyf_d38062dbb2b54c6e88c60ec4def8b43b
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A control whose setup errors
    brief:                  |
                            A control whose fixture cannot be made, so
                            nothing about the item under test was
                            observed: the adapter reads an execution error
                            and no conformance result at all.
    description:            |
                            When this control is run through the adapter,
                            the adapter must read an execution error and
                            no conformance result. Nothing about the item
                            under test was observed, so a result of any
                            kind would be a claim the run cannot support.
    relation:               []

    ...
    """

    raise AssertionError('this body never runs')


def test_errors_in_teardown(unbreakable):
    """
    ---

    id_self:                pyf_test.control_adapter.test_errors_in_teardown
    guid_self:              pyf_36fd5a90682545b2abe11540140c4914
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A control whose teardown errors
    brief:                  |
                            A control that passes and then fails as it is
                            torn down. The call observed what it meant to,
                            and the run did not complete, so the adapter
                            reads an execution error and no result.
    description:            |
                            Run through the adapter, this must read an
                            execution error and no conformance result. The
                            call passed, but the run did not complete, and
                            the harness failing is not the item under test
                            failing.
    relation:               []

    ...
    """

    assert True


def test_skips():
    """
    ---

    id_self:                pyf_test.control_adapter.test_skips
    guid_self:              pyf_f6996ac98eed4b58874b19d72b169d17
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A control that skips
    brief:                  |
                            A control that skips, so the adapter reads
                            completed and not applicable: the run happened
                            and observed nothing about the item.
    description:            |
                            When this control is run through the adapter,
                            the adapter must read completed and not
                            applicable. The run happened and observed
                            nothing about the item, which is neither a
                            pass nor a failure.
    relation:               []

    ...
    """

    pytest.skip('a control that does not apply')


@pytest.mark.parametrize('number', [1, 2])
def test_parameterised(number):
    """
    ---

    id_self:                pyf_test.control_adapter.test_parameterised
    guid_self:              pyf_dae018c0ffaa4176916780ae28411a89
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A control run twice
    brief:                  |
                            A control run twice, so the adapter reads one
                            verdict for the function rather than one for
                            each instance.
    description:            |
                            When this control is run through the adapter,
                            the adapter must read one verdict rather than
                            one verdict for each instance. A test function
                            is one item however many times it runs.
    relation:               []

    ...
    """

    assert number


@pytest.mark.parametrize('number', [1, 2])
def test_parameterised_one_fails(number):
    """
    ---

    id_self:                pyf_test.control_adapter.test_parameterised_one_fails
    guid_self:              pyf_6fd8d69c9b7c4d5f9c0f2b5c9c4e7a10
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A control run twice, failing once
    brief:                  |
                            A control run twice whose second instance
                            fails, so the adapter reads the function by
                            every instance and not by the first.
    description:            |
                            When this control is run through the adapter,
                            the adapter must read failed. The function is
                            read by every instance, and not by the first
                            instance alone.
    relation:               []

    ...
    """

    assert number == 1


@pytest.mark.timeout(2)
def test_times_out():
    """
    ---

    id_self:                pyf_test.control_adapter.test_times_out
    guid_self:              pyf_10f95f778e3c4fb9a15fabd90cc0368f
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A control that never finishes
    brief:                  |
                            A control that never finishes, stopped by the
                            timeout.
    description:            |
                            Run through the adapter, this must not become
                            a passing conformance result nor fresh passing
                            evidence. A run stopped by a timeout did not
                            finish, so what it says about the item under
                            test is nothing.
    relation:               []

    ...
    """

    time.sleep(30)
