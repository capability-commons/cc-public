% ---
%
% id_self:                lpf_cc_public.check.advise
% guid_self:              lpf_8afffbc6f0254a4389614637ba9b57e6
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Advice
% brief:                  |
%                         Advice over the graph of data items.
% description:            |
%                         Each shown relation is one kind of advice, and
%                         each row of it is one piece of advice. Advice
%                         is reported by cctool check but is not a
%                         failure: it names something that may be right
%                         here and is known to be outside what this tree
%                         can check, such as an entry held in a
%                         partner's register.
% usage:                  |
%                         Evaluated by pym_cc_public.check.check in the
%                         same program as lpf_cc_public.check.check,
%                         after the facts of the base relations and the
%                         rules of lpf_cc_public.graph.derive.
% edge:                   []
%
% ...

% -----------------------------------------------------------------------------
% A protective mark names an entry that is held nowhere here. It may
% be held in a partner's register, so this is advice, not a failure.
% reg_protective_mark asks that, until it resolves, the mark be read
% as more restrictive than any mark that resolves.
%
% decl unresolved_mark(holder: symbol,
%                      id:     symbol,
%                      guid:   symbol,
%                      file:   symbol,
%                      line:   number)
% did  {holder} has the protective mark {id}, which no register here
%      holds.
% fix  Nothing, if a partner holds the mark. Until it resolves, read it
%      as more restrictive than any mark that does.
#show unresolved_mark/5.

unresolved_mark(Holder, Id, Guid, File, Line) :-
    reference(Holder, "mark", Id, Guid, File, Line),
    not item(Id, _, _, _, _),
    not item(_, Guid, _, _, _),
    not alias(_, Id).


% -----------------------------------------------------------------------------
% A decision without options is open, which is normal while it is
% argued. It is reported so that it is not forgotten.
%
% decl decision_without_options(decision: symbol)
% did  The decision {decision} has no options.
% fix  Add its options as the decision is argued.
#show decision_without_options/1.

decision_without_options(Decision) :-
    has_type(Decision, "type_decision"),
    not answers_some(Decision).


% -----------------------------------------------------------------------------
% The decision has an option.
%
% decl answers_some(decision: symbol)

answers_some(Decision) :-
    primary_edge(_, "relation_is_option_for", Decision).
