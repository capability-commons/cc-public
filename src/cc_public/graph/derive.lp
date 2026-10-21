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
%                         are added by pym_cc_public.graph.logic. This
%                         file is placed before the rules in every
%                         program: the checks, a query, and the program
%                         that fills the derived tables for SQL.
% edge:                   []
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
% decl has_type(id:   symbol,
%               type: symbol)

has_type(Id, Type) :-
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
    not inverse_relation(Relation, _).

primary_edge(Target, Relation, Source) :-
    edge(Source, Inverse, Target),
    inverse_relation(Inverse, Relation).


% -----------------------------------------------------------------------------
% The schemas a YAML document must conform to: the schema its type names
% for the items of that type, and any schema the document names for
% itself. A document is an item held by no other, and the items inside
% it conform as part of it.
%
% decl document_schema(id:     symbol,
%                      schema: symbol)

document_schema(Id, Schema) :-
    item(Id, _, "", _, _),
    has_type(Id, Type),
    primary_edge(Type, "relation_has_items_specified_by_schema", Schema).

document_schema(Id, Schema) :-
    item(Id, _, "", _, _),
    primary_edge(Id, "relation_is_specified_by_schema", Schema).


% -----------------------------------------------------------------------------
% The ruling upholds or rejects the option.
%
% decl settles(ruling: symbol,
%              option: symbol)

settles(Ruling, Option) :-
    has_type(Ruling, "type_ruling"),
    primary_edge(Ruling, "relation_upholds", Option).

settles(Ruling, Option) :-
    has_type(Ruling, "type_ruling"),
    primary_edge(Ruling, "relation_rejects", Option).


% -----------------------------------------------------------------------------
% The item belongs to the decision: it is the decision, an option that
% answers it, an annotation about it, or a ruling that settles
% an option that answers it.
%
% decl decision_of(id:       symbol,
%                  decision: symbol)

decision_of(Id, Id) :-
    has_type(Id, "type_decision").

decision_of(Id, Decision) :-
    has_type(Id, "type_option"),
    primary_edge(Id, "relation_is_option_for", Decision).

decision_of(Id, Decision) :-
    has_type(Id, "type_annotation"),
    primary_edge(Id, "relation_is_about", Decision),
    has_type(Decision, "type_decision").

decision_of(Id, Decision) :-
    settles(Id, Option),
    decision_of(Option, Decision).


% -----------------------------------------------------------------------------
% The interface a node presents is the interface control document it
% realizes.
%
% decl node_interface(node:      symbol,
%                     interface: symbol)

node_interface(Node, Interface) :-
    has_type(Node, "type_dataflow_node"),
    primary_edge(Node, "relation_realizes", Interface),
    has_type(Interface, "type_interface_control_document").


% -----------------------------------------------------------------------------
% Data flows from the node source to the node target along an edge of
% a dataflow graph, feedforward or feedback.
%
% decl feeds(source:    symbol,
%            target:    symbol,
%            direction: symbol)

feeds(Source, Target, Direction) :-
    dataflow_edge(_, Source, _, Target, _, Direction, _, _),
    has_type(Source, "type_dataflow_node"),
    has_type(Target, "type_dataflow_node").


% -----------------------------------------------------------------------------
% Data from the node reaches the node other, through one or more edges
% of either direction.
%
% decl downstream(node:  symbol,
%                 other: symbol)

downstream(Node, Other) :-
    feeds(Node, Other, _).

downstream(Node, Other) :-
    downstream(Node, Between),
    feeds(Between, Other, _).


% -----------------------------------------------------------------------------
% Data from the node other reaches the node.
%
% decl upstream(node:  symbol,
%               other: symbol)

upstream(Node, Other) :-
    downstream(Other, Node).


% -----------------------------------------------------------------------------
% A change to the item changes what the node does: the item is the
% node, or something the node realizes, such as its interface or a
% logical component, or a member of its interface, or code that
% realizes that member.
%
% decl bears_on(item: symbol,
%               node: symbol)

bears_on(Node, Node) :-
    has_type(Node, "type_dataflow_node").

bears_on(Item, Node) :-
    has_type(Node, "type_dataflow_node"),
    primary_edge(Node, "relation_realizes", Item).

bears_on(Member, Node) :-
    node_interface(Node, Interface),
    item(Member, _, Interface, _, _).

bears_on(Code, Node) :-
    node_interface(Node, Interface),
    item(Member, _, Interface, _, _),
    primary_edge(Code, "relation_realizes", Member).


% -----------------------------------------------------------------------------
% The blast radius of a change to the item: every node it bears on,
% and every node downstream of one of those.
%
% decl blast_radius(item: symbol,
%                   node: symbol)

blast_radius(Item, Node) :-
    bears_on(Item, Node).

blast_radius(Item, Other) :-
    bears_on(Item, Node),
    downstream(Node, Other).
