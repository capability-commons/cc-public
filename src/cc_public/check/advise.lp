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
%                         Each shown predicate is one kind of advice,
%                         and each row of it is one piece of advice.
%                         Advice is reported by cctool check but is not
%                         a failure: it names something that may be
%                         right here and is worth a look, such as a
%                         protective mark held in a partner's register,
%                         a decision with no options yet, a concept an
%                         item uses with no link to it, or a term
%                         written without a link where the item declares
%                         its concept.
% usage:                  |
%                         Evaluated by pym_cc_public.check.check in the
%                         same program as lpf_cc_public.check.check,
%                         after the facts of the base predicates and the
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


% -----------------------------------------------------------------------------
% An item that uses a concept links one of its terms somewhere in its
% text, or the edge says nothing a reader can see.
%
% decl concept_used_without_link(holder:  symbol,
%                                concept: symbol)
% did  {holder} uses {concept}, and no link in its text is to it.
% fix  Write a link [[term]] where the text means the concept, or take
%      the edge out.
#show concept_used_without_link/2.

concept_used_without_link(Holder, Concept) :-
    primary_edge(Holder, "relation_uses_concept", Concept),
    not links_to(Holder, Concept).


% -----------------------------------------------------------------------------
% The text of the item, or of an item it holds, links to the concept.
%
% decl links_to(holder:  symbol,
%               concept: symbol)

links_to(Holder, Concept) :-
    term_sense(Holder, _, Concept).

links_to(Holder, Concept) :-
    term_link(Holder, _, Concept, _, _).

links_to(Holder, Concept) :-
    item(Inner, _, Holder, _, _),
    links_to(Inner, Concept).



% -----------------------------------------------------------------------------
% An item that declares it uses a concept, and writes a term of the
% concept without a link, may mean the concept there. Prose outside the
% strict fields may use the word in its everyday sense, so this is
% advice, not a failure. Titles are left to the checks of titles.
%
% decl term_to_link(holder: symbol,
%                   field:  symbol,
%                   term:   symbol,
%                   file:   symbol,
%                   line:   number)
% did  The {field} of {holder} uses "{term}", a term of a concept it
%      declares, without a link.
% fix  Write the term as a link if the concept is meant, or nothing if the word
%      is meant in its everyday sense.
#show term_to_link/5.

term_to_link(Holder, Field, Term, File, Line) :-
    term_word(Holder, Field, Term, File, Line),
    not strict_field(Holder, Field),
    Field != "title",
    declares_concept(Holder, Concept),
    designation(Concept, Term, Rating),
    Rating != "deprecated",
    not designation(Holder, Term, _).


% -----------------------------------------------------------------------------
% The concept of a type of data item has a match in an external class,
% so that a reader who knows the release can place the type. A related
% match does not place it. Until the mappings cover every type, a type
% without one is advice, not a failure.
%
% decl unmapped_concept(type:    symbol,
%                       concept: symbol)
% did  {concept}, the concept of {type}, has no exact, close, broad or
%      narrow match in an external class.
% fix  Add the match that says how {concept} relates to the nearest
%      class of the release, with an annotation that gives the reason.
#show unmapped_concept/2.

unmapped_concept(Type, Concept) :-
    register_entry_key("reg_data_item_type", _, Type),
    reference(Type, "concept", Concept, _, _, _),
    not placed_concept(Concept).


% -----------------------------------------------------------------------------
% The concept has a match other than a related one.
%
% decl placed_concept(concept: symbol)

placed_concept(Concept) :-
    match(Concept, Grade, _),
    Grade != "related".


% -----------------------------------------------------------------------------
% A narrower-than or subclass-of edge that a chain of edges of the same
% relation already implies. It is not false, so this is advice: either
% the edge is redundant, or the chain is the thing that is wrong.
%
% decl redundant_hierarchy_edge(source:   symbol,
%                               relation: symbol,
%                               target:   symbol)
% did  The edge {source} {relation} {target} says what a chain of its
%      edges already says.
% fix  Remove the edge, unless the chain is the thing that is wrong.
#show redundant_hierarchy_edge/3.

redundant_hierarchy_edge(Source, Relation, Target) :-
    hierarchy_relation(Relation),
    primary_edge(Source, Relation, Target),
    primary_edge(Source, Relation, Middle),
    Middle != Target,
    reaches(Relation, Middle, Target).


% -----------------------------------------------------------------------------
% A relation that orders concepts or classes from narrow to broad.
%
% decl hierarchy_relation(relation: symbol)

hierarchy_relation("relation_is_narrower_than").
hierarchy_relation("relation_is_subclass_of").
