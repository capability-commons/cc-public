% ---
%
% id_self:                lpf_cctool.graph.derive
% guid_self:              lpf_81439365f84948c691db275c1f6e20fd
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Derived predicates
% brief:                  |
%                         The predicates derived from the base ones, for
%                         every program over the graph of data items.
% description:            |
%                         The base predicates are declared by PREDICATE
%                         in pym_cctool.graph.extract, and their facts
%                         are added by pym_cctool.graph.logic. This file
%                         is placed before the rules in every program:
%                         the checks, a query, and the program that
%                         fills the derived tables for SQL.
% edge:                   []
%
% ...

% -----------------------------------------------------------------------------
% The prefix of an id is that of the type whose prefix and an underscore
% begin it. A prefix holds no underscore, so it is what comes before
% the first one, which the extractor finds once for each id as
% id_prefix rather than each rule trying it against each type.
%
% decl prefix_of(id:     symbol,
%                prefix: symbol)

prefix_of(Id, Prefix) :-
    item(Id, _, _, _, _),
    id_prefix(Id, Prefix),
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
% Every edge of the graph, however it is recorded. An edge in the edge
% field of an item is labeled by its relation, read as primary_edge
% reads it. A pair of reference fields id_<field> and guid_<field>
% outside the edge field is an edge too, labeled by the field.
%
% decl graph_edge(source: symbol,
%                 label:  symbol,
%                 target: symbol)

graph_edge(Source, Relation, Target) :-
    primary_edge(Source, Relation, Target).

graph_edge(Holder, Field, Id) :-
    reference(Holder, Field, Id, _, _, _),
    Field != "relation",
    Field != "target".


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
    not shadow(Id, _),
    has_type(Id, Type),
    primary_edge(Type, "relation_has_items_specified_by_schema", Schema).

document_schema(Id, Schema) :-
    item(Id, _, "", _, _),
    not shadow(Id, _),
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
% is an option for it, an annotation about it, or a ruling that
% settles an option for it.
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


% -----------------------------------------------------------------------------
% The annotation supports or challenges an option.
%
% decl practical(id: symbol)

practical(Id) :-
    has_type(Id, "type_annotation"),
    primary_edge(Id, "relation_supports", Target),
    has_type(Target, "type_option").

practical(Id) :-
    has_type(Id, "type_annotation"),
    primary_edge(Id, "relation_challenges", Target),
    has_type(Target, "type_option").


% -----------------------------------------------------------------------------
% The option, or an alternative to it for the same decision,
% has an annotation that supports or challenges it for the concern.
%
% decl argued(option:  symbol,
%             concern: symbol)

argued(Option, Concern) :-
    primary_edge(Option, "relation_is_option_for", Decision),
    primary_edge(Other, "relation_is_option_for", Decision),
    practical(Id),
    primary_edge(Id, "relation_supports", Other),
    primary_edge(Id, "relation_speaks_for_concern", Concern).

argued(Option, Concern) :-
    primary_edge(Option, "relation_is_option_for", Decision),
    primary_edge(Other, "relation_is_option_for", Decision),
    practical(Id),
    primary_edge(Id, "relation_challenges", Other),
    primary_edge(Id, "relation_speaks_for_concern", Concern).


% -----------------------------------------------------------------------------
% The concern drives the decision: it drives what the decision is
% about, or the decision names it as a driver of its own.
%
% decl driver(decision: symbol,
%             concern:  symbol)

driver(Decision, Concern) :-
    has_type(Decision, "type_decision"),
    primary_edge(Decision, "relation_is_about", Subject),
    primary_edge(Subject, "relation_is_driven_by", Concern).

driver(Decision, Concern) :-
    has_type(Decision, "type_decision"),
    primary_edge(Decision, "relation_is_driven_by", Concern).





% -----------------------------------------------------------------------------
% The logical component of a python module or package is the one that
% the nearest item realizes: the module itself, or else the innermost
% package it is inside that realizes one.
%
% decl python_component(module:    symbol,
%                       component: symbol)

python_component(Module, Component) :-
    nearest_realizer(Module, Depth),
    realizer_at(Module, Depth, Component).


% -----------------------------------------------------------------------------
% The depth of the nearest item that realizes a logical component for a
% python module or package.
%
% decl nearest_realizer(module: symbol,
%                       depth:  number)

nearest_realizer(Module, Depth) :-
    realizer_at(Module, _, _),
    Depth = #max { Below : realizer_at(Module, Below, _) }.


% -----------------------------------------------------------------------------
% A python module or package, or a package it is inside at depth, realizes
% the logical component. The module itself is deeper than any package.
%
% decl realizer_at(module:    symbol,
%                  depth:     number,
%                  component: symbol)

realizer_at(Module, Depth, Component) :-
    python_within(Module, Package, Depth),
    primary_edge(Package, "relation_realizes", Component),
    has_type(Component, "type_logical_component").

realizer_at(Module, 1000, Component) :-
    module_name(Module, _),
    primary_edge(Module, "relation_realizes", Component),
    has_type(Component, "type_logical_component").


% -----------------------------------------------------------------------------
% The lowest maturity level, which a source file that declares none
% has.
%
% decl lowest_maturity(level: number)

lowest_maturity(Level) :-
    maturity_level(_, _),
    Level = #min { Each : maturity_level(_, Each) }.


% -----------------------------------------------------------------------------
% The source file that holds the item id has the maturity level, by
% its number: the greatest it declares by relation_has_maturity, or
% the lowest if it declares none.
%
% decl file_maturity(id:    symbol,
%                    level: number)

file_maturity(Id, Level) :-
    declares_maturity(Id),
    Level = #max { Each : primary_edge(Id, "relation_has_maturity", Entry),
                          maturity_level(Entry, Each) }.

file_maturity(Id, Level) :-
    module_name(Id, _),
    item(Id, _, "", _, _),
    not declares_maturity(Id),
    lowest_maturity(Level).


% -----------------------------------------------------------------------------
% The item id declares a maturity level.
%
% decl declares_maturity(id: symbol)

declares_maturity(Id) :-
    primary_edge(Id, "relation_has_maturity", Entry),
    maturity_level(Entry, _).


% -----------------------------------------------------------------------------
% The maturity of a logical component is that of the most mature python
% module or package in it, computed and never stored.
%
% decl component_maturity(component: symbol,
%                         level:     number)

component_maturity(Component, Level) :-
    python_component(_, Component),
    Level = #max { Each : python_component(Module, Component),
                          file_maturity(Module, Each) }.


% -----------------------------------------------------------------------------
% The lowest criticality, which a requirement that declares none has.
%
% decl lowest_criticality(level: number)

lowest_criticality(Level) :-
    criticality_level(_, _),
    Level = #min { Each : criticality_level(_, Each) }.


% -----------------------------------------------------------------------------
% The requirement has the criticality, by its number: the greatest it
% declares by relation_has_criticality, or the lowest if it declares
% none.
%
% decl requirement_criticality(requirement: symbol,
%                              level:       number)

requirement_criticality(Requirement, Level) :-
    declares_criticality(Requirement),
    Level = #max { Each : primary_edge(Requirement, "relation_has_criticality", Entry),
                          criticality_level(Entry, Each) }.

requirement_criticality(Requirement, Level) :-
    has_type(Requirement, "type_requirement"),
    not declares_criticality(Requirement),
    lowest_criticality(Level).


% -----------------------------------------------------------------------------
% The requirement declares a criticality.
%
% decl declares_criticality(requirement: symbol)

declares_criticality(Requirement) :-
    primary_edge(Requirement, "relation_has_criticality", Entry),
    criticality_level(Entry, _).


% -----------------------------------------------------------------------------
% The source file or definition that holds the item id realizes the
% subject of the requirement: the subject is what it realizes, or the
% logical component it is in.
%
% decl responsible_for(id:          symbol,
%                      requirement: symbol)

responsible_for(Id, Requirement) :-
    module_name(Id, _),
    primary_edge(Id, "relation_realizes", Subject),
    primary_edge(Requirement, "relation_has_subject", Subject).

responsible_for(Id, Requirement) :-
    python_component(Id, Subject),
    primary_edge(Requirement, "relation_has_subject", Subject).


% -----------------------------------------------------------------------------
% The code that holds the item id has the criticality, by its number:
% the greatest among the requirements it is responsible for, or the
% lowest if it is responsible for none. It is derived, never declared.
%
% decl code_criticality(id:    symbol,
%                       level: number)

code_criticality(Id, Level) :-
    responsible_for(Id, _),
    Level = #max { Each : responsible_for(Id, Requirement),
                          requirement_criticality(Requirement, Each) }.

code_criticality(Id, Level) :-
    module_name(Id, _),
    not responsible_for(Id, _),
    lowest_criticality(Level).

