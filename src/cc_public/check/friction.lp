% ---
%
% id_self:                lpf_cc_public.check.friction
% guid_self:              lpf_d9c23da939fe4361a3adaa3c6b93a879
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Friction rules
% brief:                  |
%                         Signals of friction in the graph of data
%                         items: places where something may be bent to
%                         fit an earlier choice, or waits for a
%                         decision.
% description:            |
%                         Each shown predicate is one signal, and each
%                         row of it is one place to look at. A row is
%                         not a failure. The scheduled reviews read the
%                         signals and decide which are tensions worth a
%                         decision.
% usage:                  |
%                         Evaluated by pym_cc_public.check.friction,
%                         after the facts of the base predicates and the
%                         rules of lpf_cc_public.graph.derive.
% edge:                   []
%
% ...

% -----------------------------------------------------------------------------
% A preferred or admitted term that two concepts share. A reader, or a
% check, must be told which is meant wherever the word is a term.
%
% decl shared_term(form:     symbol,
%                  concept:  symbol,
%                  other:    symbol)
% did  {concept} and {other} share the term {form}.
% fix  Decide whether one concept should give up the term, or accept
%      the shared term as a tension worth keeping.
#show shared_term/3.

shared_term(Form, Concept, Other) :-
    designation(Concept, Term, Rating),
    Rating != "deprecated",
    term_form(Term, Form),
    designation(Other, Designation, Rating2),
    Rating2 != "deprecated",
    term_form(Designation, Form),
    Concept < Other.


% -----------------------------------------------------------------------------
% A type whose prefix breaks the prefix rule, and the reason it gives:
% a rule that needs an exception.
%
% decl rule_exception(type:   symbol,
%                     reason: symbol)
% did  {type} is an exception to the prefix rule: {reason}
% fix  Decide whether the prefix rule should change so that it no
%      longer needs the exception.
#show rule_exception/2.

rule_exception(Type, Reason) :-
    prefix_exception(Type, Reason).


% -----------------------------------------------------------------------------
% A decision that no ruling has settled yet: it waits for the
% maintainer.
%
% decl open_decision(decision: symbol,
%                    file:     symbol,
%                    line:     number)
% did  {decision} has no ruling yet.
% fix  Rule on it, or say what it waits for.
#show open_decision/3.

settled(Decision) :-
    settles(_, Option),
    decision_of(Option, Decision).

open_decision(Decision, File, Line) :-
    has_type(Decision, "type_decision"),
    item(Decision, _, _, File, Line),
    not settled(Decision).
