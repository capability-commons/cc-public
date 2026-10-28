% ---
%
% id_self:                lpf_cctool.check.advise
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
%                         item uses with no wiki link to it, or a term
%                         written without a wiki link where the item
%                         declares its concept.
% usage:                  |
%                         Evaluated by pym_cctool.check.check in the
%                         same program as lpf_cctool.check.check, after
%                         the facts of the base predicates and the rules
%                         of lpf_cctool.graph.derive.
% edge:                   []
%
% ...

% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.advise.unresolved_mark
% guid_self:              lpp_7f764633cd96467f8ec1fb9d4ee56ddc
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unresolved mark
% brief:                  |
%                         A protective mark names an entry that is held
%                         nowhere here. It may be held in a partner's
%                         register, so this is advice, not a failure.
%                         reg_protective_mark asks that, until it
%                         resolves, the mark be read as more restrictive
%                         than any mark that resolves.
% did:                    |
%                         {holder} has the protective mark {id}, which
%                         no register here holds.
% fix:                    |
%                         Nothing, if a partner holds the mark. Until it
%                         resolves, read it as more restrictive than any
%                         mark that does.
% edge:                   []
%
% ...
%
% decl unresolved_mark(holder: symbol,
%                      id:     symbol,
%                      guid:   symbol,
%                      file:   symbol,
%                      line:   number)
#show unresolved_mark/5.

unresolved_mark(Holder, Id, Guid, File, Line) :-
    reference(Holder, "mark", Id, Guid, File, Line),
    not item(Id, _, _, _, _),
    not item(_, Guid, _, _, _),
    not alias(_, Id).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.advise.decision_without_options
% guid_self:              lpp_e123f282b1a646c0a193068b4c509e3c
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Decision without options
% brief:                  |
%                         A decision without options is open, which is
%                         normal while it is argued. It is reported so
%                         that it is not forgotten.
% did:                    |
%                         The decision {decision} has no options.
% fix:                    |
%                         Add its options as the decision is argued.
% edge:                   []
%
% ...
%
% decl decision_without_options(decision: symbol)
#show decision_without_options/1.

decision_without_options(Decision) :-
    has_type(Decision, "type_decision"),
    not has_some_option(Decision).


% -----------------------------------------------------------------------------
% The decision has an option.
%
% decl has_some_option(decision: symbol)

has_some_option(Decision) :-
    primary_edge(_, "relation_is_option_for", Decision).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.advise.concept_used_without_link
% guid_self:              lpp_bf685ecb1c4c43edacab3f7e2a71d3ec
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Concept used without link
% brief:                  |
%                         An item that uses a concept links one of its
%                         terms somewhere in its text, or the edge says
%                         nothing a reader can see.
% did:                    |
%                         {holder} uses {concept}, and no wiki link in
%                         its text is to it.
% fix:                    |
%                         Write a wiki link "[[term]]" where the text
%                         means the concept, or take the edge out.
% edge:                   []
%
% ...
%
% decl concept_used_without_link(holder:  symbol,
%                                concept: symbol)
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
% ---
%
% id_self:                lpp_cctool.check.advise.term_to_link
% guid_self:              lpp_975c0655b9114bf39edb1aece2563420
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Term to link
% brief:                  |
%                         An item that declares it uses a concept, and
%                         writes a term of the concept without a wiki
%                         link, may mean the concept there. Prose
%                         outside the strict fields may use the word in
%                         its everyday sense, so this is advice, not a
%                         failure. Titles are left to the checks of
%                         titles. As in a wiki, the first use is the one
%                         to link: the advice names only the first
%                         unlinked use of each term in an item, and none
%                         once the item, or an item it holds, links the
%                         concept anywhere.
% did:                    |
%                         The {field} of {holder} uses "{term}", a term
%                         of a concept it declares, without a wiki link.
% fix:                    |
%                         Write the term as a wiki link if the concept
%                         is meant, or nothing if the word is meant in
%                         its everyday sense.
% edge:                   []
%
% ...
%
% decl term_to_link(holder: symbol,
%                   field:  symbol,
%                   term:   symbol,
%                   file:   symbol,
%                   line:   number)
#show term_to_link/5.

term_to_link(Holder, Field, Term, File, Line) :-
    unlinked_use(Holder, Field, Term, File, Line),
    Line  = #min { L : unlinked_use(Holder, _, Term, _, L) },
    Field = #min { F : unlinked_use(Holder, F, Term, _, Line) },
    File  = #min { P : unlinked_use(Holder, Field, Term, P, Line) }.


% -----------------------------------------------------------------------------
% A use of a term of a concept that the item declares, outside the strict
% fields and the title, where the item links the concept nowhere.
%
% decl unlinked_use(holder: symbol,
%                   field:  symbol,
%                   term:   symbol,
%                   file:   symbol,
%                   line:   number)

unlinked_use(Holder, Field, Term, File, Line) :-
    term_word(Holder, Field, Term, File, Line),
    not strict_field(Holder, Field),
    Field != "title",
    declares_concept(Holder, Concept),
    designation(Concept, Term, Rating),
    Rating != "deprecated",
    not designation(Holder, Term, _),
    not links_to(Holder, Concept).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.advise.unmapped_concept
% guid_self:              lpp_6fafc9c970e6466e991aabcfe10279cd
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unmapped concept
% brief:                  |
%                         The concept of a type of data item has a match
%                         in an external class, so that a reader who
%                         knows the release can place the type. A
%                         related match does not place it. Until the
%                         mappings cover every type, a type without one
%                         is advice, not a failure.
% did:                    |
%                         {concept}, the concept of {type}, has no
%                         exact, close, broad or narrow match in an
%                         external class.
% fix:                    |
%                         Add the match that says how the concept
%                         relates to the nearest class of the release,
%                         with an annotation that gives the reason.
% edge:                   []
%
% ...
%
% decl unmapped_concept(type:    symbol,
%                       concept: symbol)
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
% ---
%
% id_self:                lpp_cctool.check.advise.redundant_hierarchy_edge
% guid_self:              lpp_2a5dbd6e5ded448296f2c75ad34311e9
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Redundant hierarchy edge
% brief:                  |
%                         A narrower-than or subclass-of edge that a
%                         chain of edges of the same relation already
%                         implies. It is not false, so this is advice:
%                         either the edge is redundant, or the chain is
%                         the thing that is wrong.
% did:                    |
%                         The edge {source} {relation} {target} says
%                         what a chain of its edges already says.
% fix:                    |
%                         Remove the edge, unless the chain is the thing
%                         that is wrong.
% edge:                   []
%
% ...
%
% decl redundant_hierarchy_edge(source:   symbol,
%                               relation: symbol,
%                               target:   symbol)
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


% -----------------------------------------------------------------------------
% The definition of the concept names the other as its genus, the
% broader concept that it narrows, by the link it opens with.
%
% decl genus(concept: symbol,
%            genus:   symbol)

genus(Concept, Genus) :-
    genus_link(Concept, _, Genus),
    Genus != "".

genus(Concept, Genus) :-
    genus_link(Concept, Term, ""),
    term_sense(Concept, Term, Genus).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.advise.unrecorded_genus
% guid_self:              lpp_c627e85816734e96a7991fa16aab1dff
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unrecorded genus
% brief:                  |
%                         A concept whose definition opens with its
%                         genus is narrower than that genus in the
%                         concept register, so that the register keeps
%                         the hierarchy that the definitions state. A
%                         definition may open with a link that is not
%                         its genus, so this is advice, not a failure.
% did:                    |
%                         The definition of {concept} opens with
%                         {genus}, but {concept} is not narrower than
%                         {genus}.
% fix:                    |
%                         Add an edge of relation_is_narrower_than from
%                         the concept to the one its definition opens
%                         with. If that one is not its genus, reword the
%                         definition so that it opens with the genus.
% edge:                   []
%
% ...
%
% decl unrecorded_genus(concept: symbol,
%                       genus:   symbol)
#show unrecorded_genus/2.

unrecorded_genus(Concept, Genus) :-
    has_type(Concept, "type_concept"),
    genus(Concept, Genus),
    Genus != Concept,
    not reaches("relation_is_narrower_than", Concept, Genus).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.advise.ruling_with_unargued_driver
% guid_self:              lpp_adf3da981a7742a789e8acb6317a9e02
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Ruling with unargued driver
% brief:                  |
%                         A ruling upholds an option although a concern
%                         that drives its decision is not argued, most
%                         likely a driver added after the ruling was
%                         made. The ruling stands, since it is judged by
%                         the drivers in force when it was made, but it
%                         is worth a look when the decision is next
%                         reviewed.
% did:                    |
%                         {ruling} upholds {option}, and no annotation
%                         argues {concern}, a driver of its decision,
%                         for it or an alternative to it.
% fix:                    |
%                         Argue the concern on the option or an
%                         alternative, and revisit the ruling if the
%                         argument goes against it.
% edge:                   []
%
% ...
%
% decl ruling_with_unargued_driver(ruling:  symbol,
%                                  option:  symbol,
%                                  concern: symbol)
#show ruling_with_unargued_driver/3.

ruling_with_unargued_driver(Ruling, Option, Concern) :-
    has_type(Ruling, "type_ruling"),
    primary_edge(Ruling, "relation_upholds", Option),
    primary_edge(Option, "relation_is_option_for", Decision),
    driver(Decision, Concern),
    not argued(Option, Concern).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.advise.import_not_allowed
% guid_self:              lpp_64f6e4eca1dc4dc28a720cf4b9b1bb02
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Import not allowed
% brief:                  |
%                         A python module imports a module of another
%                         logical component, and no edge of
%                         relation_may_depend_on lets its component
%                         depend on that one. It is advice while the
%                         components and their edges are first laid
%                         down.
% did:                    |
%                         {module}, of {component}, imports {imported},
%                         of {other}, which {component} may not depend
%                         on.
% fix:                    |
%                         Move the code so that the import follows the
%                         order of the components, or, if the order
%                         should change, add the edge of
%                         relation_may_depend_on from the component of
%                         the module to the other.
% edge:                   []
%
% ...
%
% decl import_not_allowed(module:    symbol,
%                         component: symbol,
%                         imported:  symbol,
%                         other:     symbol,
%                         file:      symbol,
%                         line:      number)
#show import_not_allowed/6.

import_not_allowed(Module, Component, Imported, Other, File, Line) :-
    python_import(Module, Imported),
    python_component(Module, Component),
    python_component(Imported, Other),
    Component != Other,
    not primary_edge(Component, "relation_may_depend_on", Other),
    item(Module, _, _, File, Line).


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
