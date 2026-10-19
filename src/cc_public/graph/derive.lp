% ---
%
% id_self:                lpf_cc_public.graph.derive
% guid_self:              lpf_81439365f84948c691db275c1f6e20fd
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Derived relations
% brief:                  |
%                         Relations derived from the base relations, for
%                         every program over the graph of data items.
% description:            |
%                         The base relations are declared by RELATION in
%                         pym_cc_public.graph.extract, and their facts
%                         are added by pym_cc_public.graph.datalog. This
%                         file is placed before the rules in every
%                         program: the checks, a query, and the program
%                         that fills the derived tables for SQL.
% relation:               []
%
% ...

% -----------------------------------------------------------------------------
% The prefix of an id is that of the type whose prefix and an underscore
% begin it. A prefix holds no underscore, so it is what comes before
% the first one, found once for each id rather than tried against
% each type.
%
% decl prefix_of(id:     symbol,
%                prefix: symbol)

prefix_of(Id, Prefix) :-
    item(Id, _, _, _, _),
    Prefix = @prefix(Id),
    type_prefix(_, Prefix, _).


% -----------------------------------------------------------------------------
% The type of an id is the type whose prefix it has.
%
% decl type_of(id:   symbol,
%              type: symbol)

type_of(Id, Type) :-
    prefix_of(Id, Prefix),
    type_prefix(Type, Prefix, _).


% -----------------------------------------------------------------------------
% An edge recorded with an inverse is read as the primary edge in the
% opposite direction.
%
% decl primary_edge(source:   symbol,
%                   relation: symbol,
%                   target:   symbol)

primary_edge(Source, Relation, Target) :-
    edge(Source, Relation, Target),
    not relation_inverse(Relation, _).

primary_edge(Target, Relation, Source) :-
    edge(Source, Inverse, Target),
    relation_inverse(Inverse, Relation).


% -----------------------------------------------------------------------------
% The schemas a document must conform to: the schema its type names for
% the items of that type, and any schema the document names for itself.
% A document is an item held by no other, and the items inside it
% conform as part of it.
%
% decl document_schema(id:     symbol,
%                      schema: symbol)

document_schema(Id, Schema) :-
    item(Id, _, "", _, _),
    type_of(Id, Type),
    primary_edge(Type, "r_has_items_specified_by_schema", Schema).

document_schema(Id, Schema) :-
    item(Id, _, "", _, _),
    primary_edge(Id, "r_is_specified_by_schema", Schema).
