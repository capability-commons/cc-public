% ---
%
% id_self:                lpf_cc_public.commit.impact
% guid_self:              lpf_bc6a637ef5554f2c9d1880ce35659e3d
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Commit impact rules
% brief:                  |
%                         The items a commit touches, and the untouched
%                         items within a given depth of them.
% description:            |
%                         Each shown relation is one part of the result:
%                         touched holds each item added, removed,
%                         renamed or changed, and neighbour each link
%                         that reaches an untouched item.
% usage:                  |
%                         Evaluated by pym_cc_public.commit.impact. The
%                         facts of the base relations and the rules of
%                         lpf_cc_public.graph.derive come before this
%                         file in the program.
% relation:               []
%
% ...

% -----------------------------------------------------------------------------
% Each item of the graph before the commit, as item gives it after.
%
% decl before_item(id:     symbol,
%                  guid:   symbol,
%                  holder: symbol,
%                  file:   symbol,
%                  line:   number)


% -----------------------------------------------------------------------------
% Each edge, reference and inverse of the graph before the commit, as
% edge, reference and relation_inverse give them after.
%
% decl before_edge(source:   symbol,
%                  relation: symbol,
%                  target:   symbol)

% decl before_reference(holder: symbol,
%                       field:  symbol,
%                       id:     symbol,
%                       guid:   symbol,
%                       file:   symbol,
%                       line:   number)

% decl before_relation_inverse(inverse:  symbol,
%                              relation: symbol)


% -----------------------------------------------------------------------------
% A digest of what each item holds, before the commit and after it: its
% own fields, with each item inside it reduced to its id, and the source
% text of the code or file that holds it, if any.
%
% decl digest(id:     symbol,
%             digest: symbol)

% decl before_digest(id:     symbol,
%                    digest: symbol)


% -----------------------------------------------------------------------------
% How far from a touched item to look, and which way: "in" to the items
% that link to it, "out" to those it links to, or "both".
%
% decl max_depth(depth: number)

% decl direction(direction: symbol)


% -----------------------------------------------------------------------------
% The guids of the graph before the commit, and after it.
%
% decl before_guid(guid: symbol)

before_guid(Guid) :-
    before_item(_, Guid, _, _, _).

% decl after_guid(guid: symbol)

after_guid(Guid) :-
    item(_, Guid, _, _, _).


% -----------------------------------------------------------------------------
% Each item the commit touches, and how. An item keeps its guid when it
% is renamed, so a renamed item is matched by its guid and names the id
% it was. An item renamed and changed is reported as renamed.
%
% decl touched(id:    symbol,
%              delta: symbol,
%              was:   symbol)
#show touched/3.

touched(Id, "added", "") :-
    item(Id, Guid, _, _, _),
    not before_guid(Guid).

touched(Id, "removed", "") :-
    before_item(Id, Guid, _, _, _),
    not after_guid(Guid).

touched(Id, "renamed", Was) :-
    item(Id, Guid, _, _, _),
    before_item(Was, Guid, _, _, _),
    Was != Id.

touched(Id, "changed", "") :-
    item(Id, Guid, _, _, _),
    before_item(Id, Guid, _, _, _),
    digest(Id, Digest),
    before_digest(Id, Before),
    Digest != Before.

% decl is_touched(id: symbol)

is_touched(Id) :-
    touched(Id, _, _).


% -----------------------------------------------------------------------------
% An item links to another by a primary edge, by a reference in a pair
% of id and guid fields that is not part of an edge, by holding it, by
% recording an edge of the relation it is, or by being of the type it
% is. The links of a removed item are those of the graph before the
% commit. An edge recorded with an inverse is read as primary_edge reads
% it.
%
% decl link(source:   symbol,
%           relation: symbol,
%           target:   symbol)

link(Source, Relation, Target) :-
    primary_edge(Source, Relation, Target).

link(Holder, Field, Id) :-
    reference(Holder, Field, Id, _, _, _),
    Field != "relation",
    Field != "target".

link(Holder, "holds", Id) :-
    item(Id, _, Holder, _, _),
    Holder != "".

link(Source, "uses", Relation) :-
    edge(Source, Relation, _),
    item(Relation, _, _, _, _).

link(Id, "has_type", Type) :-
    type_of(Id, Type).

% decl before_link(source:   symbol,
%                  relation: symbol,
%                  target:   symbol)

before_link(Source, Relation, Target) :-
    before_edge(Source, Relation, Target),
    not before_relation_inverse(Relation, _).

before_link(Target, Relation, Source) :-
    before_edge(Source, Inverse, Target),
    before_relation_inverse(Inverse, Relation).

before_link(Holder, Field, Id) :-
    before_reference(Holder, Field, Id, _, _, _),
    Field != "relation",
    Field != "target".

before_link(Holder, "holds", Id) :-
    before_item(Id, _, Holder, _, _),
    Holder != "".

before_link(Source, "uses", Relation) :-
    before_edge(Source, Relation, _),
    before_item(Relation, _, _, _, _).

link(Source, Relation, Target) :-
    before_link(Source, Relation, Target),
    touched(Source, "removed", _).

link(Source, Relation, Target) :-
    before_link(Source, Relation, Target),
    touched(Target, "removed", _).


% -----------------------------------------------------------------------------
% A step from one item to another along a link, out along it or in
% against it, in a direction that is asked for.
%
% decl step(from:      symbol,
%           relation:  symbol,
%           to:        symbol,
%           direction: symbol)

step(From, Relation, To, "out") :-
    link(From, Relation, To),
    direction(("out"; "both")).

step(From, Relation, To, "in") :-
    link(To, Relation, From),
    direction(("in"; "both")).


% -----------------------------------------------------------------------------
% An untouched item that a walk from a touched item reaches, at each
% depth it is reached at, with the item it was reached from. A walk
% keeps the direction of its first step, so that it does not turn back
% through an item that many link to, such as a concern.
%
% decl reached(id:        symbol,
%              depth:     number,
%              via:       symbol,
%              relation:  symbol,
%              direction: symbol)

reached(Id, 1, From, Relation, Direction) :-
    is_touched(From),
    step(From, Relation, Id, Direction),
    item(Id, _, _, _, _),
    not is_touched(Id).

reached(Id, Depth + 1, From, Relation, Direction) :-
    reached(From, Depth, _, _, Direction),
    max_depth(Max),
    Depth < Max,
    step(From, Relation, Id, Direction),
    item(Id, _, _, _, _),
    not is_touched(Id).

% decl nearest(id:    symbol,
%              depth: number)

nearest(Id, Depth) :-
    reached(Id, _, _, _, _),
    Depth = #min { Each : reached(Id, Each, _, _, _) }.


% -----------------------------------------------------------------------------
% Each untouched neighbour of the touched items, at the least depth it
% is reached at, once for each link that reaches it there.
%
% decl neighbour(id:        symbol,
%                depth:     number,
%                via:       symbol,
%                relation:  symbol,
%                direction: symbol)
#show neighbour/5.

neighbour(Id, Depth, Via, Relation, Direction) :-
    nearest(Id, Depth),
    reached(Id, Depth, Via, Relation, Direction).
