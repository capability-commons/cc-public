% ---
%
% id_self:                lpf_cc_public.check.check
% guid_self:              lpf_701afabb2c5248459d1eeb36bc8a6c18
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Checks
% brief:                  |
%                         Checks over the graph of data items.
% description:            |
%                         Each shown relation is one check, and each row
%                         of it is one failure. A check that reports a
%                         file reports the line of it too.
%
%                         The checks come in this order: identity,
%                         references and edges, prose and old ids, the
%                         shape of the graph, and the completeness of
%                         the kernel.
% usage:                  |
%                         Evaluated by pym_cc_public.check.check. The
%                         facts of the base relations and the rules of
%                         lpf_cc_public.graph.derive come before this
%                         file in the program.
% relation:               []
%
% ...

% -----------------------------------------------------------------------------
% Every id begins with the prefix of a known type.
%
% decl unknown_prefix(id:   symbol,
%                     file: symbol,
%                     line: number)
#show unknown_prefix/3.

unknown_prefix(Id, File, Line) :-
    item(Id, _, _, File, Line),
    not prefix_of(Id, _).


% -----------------------------------------------------------------------------
% Every id matches the regex_id of its type. sch_primitive checks only
% the form every id shares; the regex_id of each type is data, which a
% fixed schema cannot read.
%
% decl bad_id(id:    symbol,
%             regex: symbol,
%             file:  symbol,
%             line:  number)
#show bad_id/4.

bad_id(Id, Regex, File, Line) :-
    item(Id, _, _, File, Line),
    type_of(Id, Type),
    type_prefix(Type, _, Regex),
    @match(Regex, Id) = 0.


% -----------------------------------------------------------------------------
% Every guid is the prefix of its id and 32 hex digits. sch_primitive
% checks the form, but not that the two prefixes agree.
%
% decl bad_guid(id:   symbol,
%               guid: symbol,
%               file: symbol,
%               line: number)
#show bad_guid/4.

bad_guid(Id, Guid, File, Line) :-
    item(Id, Guid, _, File, Line),
    prefix_of(Id, Prefix),
    @match(@cat(Prefix, "_[0-9a-f]{32}"), Guid) = 0.


% -----------------------------------------------------------------------------
% No two types share a prefix.
%
% decl duplicate_prefix(prefix: symbol,
%                       type:   symbol,
%                       other:  symbol)
#show duplicate_prefix/3.

duplicate_prefix(Prefix, Type, Other) :-
    type_prefix(Type, Prefix, _),
    type_prefix(Other, Prefix, _),
    Type != Other.


% -----------------------------------------------------------------------------
% No id names two items.
%
% decl duplicate_id(id:    symbol,
%                   guid:  symbol,
%                   other: symbol)
#show duplicate_id/3.

duplicate_id(Id, Guid, Other) :-
    item(Id, Guid, _, _, _),
    item(Id, Other, _, _, _),
    Guid != Other.


% -----------------------------------------------------------------------------
% No guid identifies two items.
%
% decl duplicate_guid(guid:  symbol,
%                     id:    symbol,
%                     other: symbol)
#show duplicate_guid/3.

duplicate_guid(Guid, Id, Other) :-
    item(Id, Guid, _, _, _),
    item(Other, Guid, _, _, _),
    Id != Other.


% -----------------------------------------------------------------------------
% No item is written twice. A copy carries the id and the guid of the
% item it copies, so neither duplicate_id nor duplicate_guid finds it.
%
% decl repeated_item(id:   symbol,
%                    file: symbol,
%                    line: number)
#show repeated_item/3.

repeated_item(Id, File, Line) :-
    item(Id, Guid, _, File, Line),
    item(Id, Guid, _, Other, Where),
    (File, Line) != (Other, Where).


% -----------------------------------------------------------------------------
% A python module, python package or logic program file item is named
% for the module, package or file that holds it.
%
% decl misplaced_module(id:       symbol,
%                       expected: symbol)
#show misplaced_module/2.

misplaced_module(Id, Expected) :-
    module_name(Id, Expected),
    Id != Expected.


% -----------------------------------------------------------------------------
% The item belongs to the issue: it is the issue, a decision that
% answers it, an annotation about it, or a determination that settles
% a decision that answers it.
%
% decl issue_of(id:    symbol,
%               issue: symbol)

issue_of(Id, Id) :-
    type_of(Id, "t_issue").

issue_of(Id, Issue) :-
    type_of(Id, "t_decision"),
    primary_edge(Id, "r_answers", Issue).

issue_of(Id, Issue) :-
    type_of(Id, "t_annotation"),
    primary_edge(Id, "r_is_about", Issue),
    type_of(Issue, "t_issue").

issue_of(Id, Issue) :-
    settles(Id, Decision),
    issue_of(Decision, Issue).


% -----------------------------------------------------------------------------
% A document under a _data directory is in the folder named for its
% type, less the t_, in a file named for its id. A document that
% belongs to an issue is in the folder of the issue instead, so that
% everything argued about one issue is kept together.
%
% decl misplaced_document(id:       symbol,
%                         file:     symbol,
%                         expected: symbol)
#show misplaced_document/3.

misplaced_document(Id, File, Expected) :-
    item(Id, _, "", File, _),
    @match("(.*/)?_data/.*\\.yaml", File) = 1,
    not issue_of(Id, _),
    type_of(Id, Type),
    Stem     = @substr(Type, 2, @strlen(Type) - 2),
    Expected = @cat("_data/", Stem, "/", Id, ".yaml"),
    @match(@cat("(.*/)?", Expected), File) = 0.

misplaced_document(Id, File, Expected) :-
    item(Id, _, "", File, _),
    @match("(.*/)?_data/.*\\.yaml", File) = 1,
    issue_of(Id, Issue),
    Expected = @cat("_data/issue/", Issue, "/", Id, ".yaml"),
    @match(@cat("(.*/)?", Expected), File) = 0.


% -----------------------------------------------------------------------------
% A register holds only register entries of a type whose items it
% holds.
%
% decl misplaced_register_entry(register: symbol,
%                               id:       symbol,
%                               type:     symbol)
#show misplaced_register_entry/3.

misplaced_register_entry(Register, Id, Type) :-
    register_entry_key(Register, _, Id),
    type_of(Id, Type),
    not primary_edge(Type, "r_has_items_held_in_register", Register).


% -----------------------------------------------------------------------------
% Every python module and logic program file under src holds an item.
%
% decl unrecorded_module(file: symbol)
#show unrecorded_module/1.

unrecorded_module(File) :-
    tree_file(File),
    @match("src/.*\\.(py|lp)", File) = 1,
    not item(_, _, "", File, _).


% -----------------------------------------------------------------------------
% The key of a register entry is its id.
%
% decl key_mismatch(register: symbol,
%                   key:      symbol,
%                   id:       symbol)
#show key_mismatch/3.

key_mismatch(Register, Key, Id) :-
    register_entry_key(Register, Key, Id),
    Key != Id.


% -----------------------------------------------------------------------------
% Every reference names an item that exists, by its id or, where the
% id names nothing, by its guid. A protective mark that names nothing
% here is not a failure: it may be held in a partner's register, and
% advise.lp reports it.
%
% decl dangling_reference(holder: symbol,
%                         role:   symbol,
%                         id:     symbol,
%                         file:   symbol,
%                         line:   number)
#show dangling_reference/5.

dangling_reference(Holder, Role, Id, File, Line) :-
    reference(Holder, Role, Id, Guid, File, Line),
    not item(Id, _, _, _, _),
    not item(_, Guid, _, _, _),
    not alias(_, Id),
    Role != "mark".


% -----------------------------------------------------------------------------
% Every reference carries the guid of the item it names.
%
% decl stale_guid(holder: symbol,
%                 role:   symbol,
%                 id:     symbol,
%                 guid:   symbol,
%                 file:   symbol,
%                 line:   number)
#show stale_guid/6.

stale_guid(Holder, Role, Id, Guid, File, Line) :-
    reference(Holder, Role, Id, Guid, File, Line),
    item(Id, Other, _, _, _),
    Guid != Other.


% -----------------------------------------------------------------------------
% The source of an edge is of a type its relation's domain allows.
%
% decl domain_violation(source:   symbol,
%                       relation: symbol,
%                       type:     symbol)
#show domain_violation/3.

domain_violation(Source, Relation, Type) :-
    primary_edge(Source, Relation, _),
    relation_domain(Relation, _),
    type_of(Source, Type),
    not relation_domain(Relation, Type).


% -----------------------------------------------------------------------------
% The target of an edge is of a type its relation's range allows.
%
% decl range_violation(target:   symbol,
%                      relation: symbol,
%                      type:     symbol)
#show range_violation/3.

range_violation(Target, Relation, Type) :-
    primary_edge(_, Relation, Target),
    relation_range(Relation, _),
    type_of(Target, Type),
    not relation_range(Relation, Type).


% -----------------------------------------------------------------------------
% Every annotation and every issue is about something.
%
% decl missing_about(id: symbol)
#show missing_about/1.

missing_about(Id) :-
    type_of(Id, "t_annotation"),
    not primary_edge(Id, "r_is_about", _).

missing_about(Id) :-
    type_of(Id, "t_issue"),
    not primary_edge(Id, "r_is_about", _).


% -----------------------------------------------------------------------------
% Every decision answers exactly one issue. The decisions that answer
% an issue are its alternatives.
%
% decl answer_count(decision: symbol,
%                   issues:   number)
#show answer_count/2.

answer_count(Decision, Issues) :-
    type_of(Decision, "t_decision"),
    Issues = #count { Issue : primary_edge(Decision, "r_answers", Issue) },
    Issues != 1.


% -----------------------------------------------------------------------------
% Every determination upholds or rejects at least one decision.
%
% decl determination_without_decision(id: symbol)
#show determination_without_decision/1.

determination_without_decision(Id) :-
    type_of(Id, "t_determination"),
    not primary_edge(Id, "r_upholds", _),
    not primary_edge(Id, "r_rejects", _).


% -----------------------------------------------------------------------------
% The determination upholds or rejects the decision.
%
% decl settles(determination: symbol,
%              decision:      symbol)

settles(Determination, Decision) :-
    type_of(Determination, "t_determination"),
    primary_edge(Determination, "r_upholds", Decision).

settles(Determination, Decision) :-
    type_of(Determination, "t_determination"),
    primary_edge(Determination, "r_rejects", Decision).


% -----------------------------------------------------------------------------
% A determination settles the decisions of one issue.
%
% decl determination_across_issues(determination: symbol,
%                                  issue:         symbol,
%                                  other:         symbol)
#show determination_across_issues/3.

determination_across_issues(Determination, Issue, Other) :-
    type_of(Determination, "t_determination"),
    issue_of(Determination, Issue),
    issue_of(Determination, Other),
    Issue < Other.


% -----------------------------------------------------------------------------
% An issue is about logical components, since their drivers say which
% concerns must be argued before a decision of the issue is settled.
% An issue about anything else would escape that check.
%
% decl issue_about_non_component(issue:  symbol,
%                                target: symbol,
%                                type:   symbol)
#show issue_about_non_component/3.

issue_about_non_component(Issue, Target, Type) :-
    type_of(Issue, "t_issue"),
    primary_edge(Issue, "r_is_about", Target),
    type_of(Target, Type),
    Type != "t_logical_component".


% -----------------------------------------------------------------------------
% An annotation argues within its issue: what it supports or challenges
% belongs to the same issue as it does.
%
% decl argument_across_issues(annotation: symbol,
%                             issue:      symbol,
%                             target:     symbol,
%                             other:      symbol)
#show argument_across_issues/4.

argument_across_issues(Annotation, Issue, Target, Other) :-
    type_of(Annotation, "t_annotation"),
    primary_edge(Annotation, Relation, Target),
    argues(Relation),
    issue_of(Annotation, Issue),
    issue_of(Target, Other),
    Issue != Other.


% -----------------------------------------------------------------------------
% An annotation argues with what it supports or challenges.
%
% decl argues(relation: symbol)

argues("r_supports").
argues("r_challenges").


% -----------------------------------------------------------------------------
% An item supersedes only an item of its own type: a decision another
% decision, and a determination another determination.
%
% decl supersession_across_types(source: symbol,
%                                target: symbol)
#show supersession_across_types/2.

supersession_across_types(Source, Target) :-
    primary_edge(Source, "r_supersedes", Target),
    type_of(Source, Type),
    not type_of(Target, Type).


% -----------------------------------------------------------------------------
% A determination supersedes only a determination of its own issue.
%
% decl supersession_across_issues(determination: symbol,
%                                 other:         symbol)
#show supersession_across_issues/2.

supersession_across_issues(Determination, Other) :-
    type_of(Determination, "t_determination"),
    primary_edge(Determination, "r_supersedes", Other),
    issue_of(Determination, Issue),
    not issue_of(Other, Issue).


% -----------------------------------------------------------------------------
% The determination is the current one of its issue: nothing
% supersedes it.
%
% decl current_determination(determination: symbol,
%                            issue:         symbol)

current_determination(Determination, Issue) :-
    type_of(Determination, "t_determination"),
    issue_of(Determination, Issue),
    not primary_edge(_, "r_supersedes", Determination).


% -----------------------------------------------------------------------------
% An issue has at most one current determination. A later
% determination names the one it replaces.
%
% decl competing_determinations(issue:         symbol,
%                               determination: symbol,
%                               other:         symbol)
#show competing_determinations/3.

competing_determinations(Issue, Determination, Other) :-
    current_determination(Determination, Issue),
    current_determination(Other, Issue),
    Determination < Other.


% -----------------------------------------------------------------------------
% The decision, or an alternative to it that answers the same issue,
% has an annotation that supports or challenges it for the concern.
%
% decl argued(decision: symbol,
%             concern:  symbol)

argued(Decision, Concern) :-
    primary_edge(Decision, "r_answers", Issue),
    primary_edge(Other, "r_answers", Issue),
    practical(Id),
    primary_edge(Id, "r_supports", Other),
    primary_edge(Id, "r_argues_for_concern", Concern).

argued(Decision, Concern) :-
    primary_edge(Decision, "r_answers", Issue),
    primary_edge(Other, "r_answers", Issue),
    practical(Id),
    primary_edge(Id, "r_challenges", Other),
    primary_edge(Id, "r_argues_for_concern", Concern).


% -----------------------------------------------------------------------------
% A determination settles a decision only once every concern that
% drives the subject of its issue has been argued, for it or for an
% alternative to it.
%
% decl unargued_driver(determination: symbol,
%                      decision:      symbol,
%                      concern:       symbol)
#show unargued_driver/3.

unargued_driver(Determination, Decision, Concern) :-
    settles(Determination, Decision),
    primary_edge(Decision, "r_answers", Issue),
    primary_edge(Issue, "r_is_about", Subject),
    primary_edge(Subject, "r_is_driven_by", Concern),
    not argued(Decision, Concern).


% -----------------------------------------------------------------------------
% Every file that ought to hold a document can be read: a YAML file
% under _data, the module docstring of a python module, or a comment
% header. One that cannot hides its items from every other check.
%
% decl unreadable_file(file:    symbol,
%                      line:    number,
%                      message: symbol)
#show unreadable_file/3.

unreadable_file(File, Line, Message) :-
    unreadable(File, Line, Message).


% -----------------------------------------------------------------------------
% Every id that a text mentions, if it has the prefix of a known type,
% names an item, or an old id of one. A guid may be mentioned too.
%
% decl dangling_mention(holder: symbol,
%                       id:     symbol,
%                       file:   symbol,
%                       line:   number)
#show dangling_mention/4.

dangling_mention(Holder, Id, File, Line) :-
    mention(Holder, Id, File, Line),
    type_prefix(_, Prefix, _),
    @match(@cat(Prefix, "_.*"), Id) = 1,
    not item(Id, _, _, _, _),
    not item(_, Id, _, _, _),
    not alias(_, Id).


% -----------------------------------------------------------------------------
% An alias is an old id, so no item has it.
%
% decl alias_in_use(alias: symbol,
%                   id:    symbol)
#show alias_in_use/2.

alias_in_use(Alias, Id) :-
    alias(Id, Alias),
    item(Alias, _, _, _, _).


% -----------------------------------------------------------------------------
% A reference names an item by its current id, not an old one. An old
% id is found through an alias or, where the id names nothing, through
% the guid, which decides.
%
% decl outdated_reference(holder: symbol,
%                         role:   symbol,
%                         alias:  symbol,
%                         id:     symbol,
%                         file:   symbol,
%                         line:   number)
#show outdated_reference/6.

outdated_reference(Holder, Role, Alias, Id, File, Line) :-
    reference(Holder, Role, Alias, _, File, Line),
    alias(Id, Alias),
    not item(Alias, _, _, _, _).

outdated_reference(Holder, Role, Old, Id, File, Line) :-
    reference(Holder, Role, Old, Guid, File, Line),
    item(Id, Guid, _, _, _),
    not item(Old, _, _, _, _),
    not alias(Id, Old).


% -----------------------------------------------------------------------------
% A text names an item by its current id, except in the item itself,
% where it may record what the item was once called.
%
% decl outdated_mention(holder: symbol,
%                       alias:  symbol,
%                       id:     symbol,
%                       file:   symbol,
%                       line:   number)
#show outdated_mention/5.

outdated_mention(Holder, Alias, Id, File, Line) :-
    mention(Holder, Alias, File, Line),
    alias(Id, Alias),
    not item(Alias, _, _, _, _),
    Holder != Id.


% -----------------------------------------------------------------------------
% A chain of edges of an acyclic relation leads from source to target.
%
% decl reaches(relation: symbol,
%              source:   symbol,
%              target:   symbol)

reaches(Relation, Source, Target) :-
    relation_acyclic(Relation),
    primary_edge(Source, Relation, Target).

reaches(Relation, Source, Target) :-
    reaches(Relation, Source, Middle),
    primary_edge(Middle, Relation, Target).


% -----------------------------------------------------------------------------
% No chain of edges of an acyclic relation leads from an item back to
% itself.
%
% decl cycle(relation: symbol,
%            id:       symbol)
#show cycle/2.

cycle(Relation, Id) :-
    reaches(Relation, Id, Id).


% -----------------------------------------------------------------------------
% The annotation supports or challenges a decision.
%
% decl practical(id: symbol)

practical(Id) :-
    type_of(Id, "t_annotation"),
    primary_edge(Id, "r_supports", Target),
    type_of(Target, "t_decision").

practical(Id) :-
    type_of(Id, "t_annotation"),
    primary_edge(Id, "r_challenges", Target),
    type_of(Target, "t_decision").


% -----------------------------------------------------------------------------
% An annotation that supports or challenges a decision speaks for at
% least one concern. A premise that several concerns rest on is one
% annotation that speaks for each of them.
%
% decl argument_without_concern(id: symbol)
#show argument_without_concern/1.

argument_without_concern(Id) :-
    practical(Id),
    not primary_edge(Id, "r_argues_for_concern", _).


% -----------------------------------------------------------------------------
% An annotation that bears on no decision speaks for no concern, since
% it is answered with evidence and not outweighed.
%
% decl concern_without_decision(id:      symbol,
%                               concern: symbol)
#show concern_without_decision/2.

concern_without_decision(Id, Concern) :-
    type_of(Id, "t_annotation"),
    not practical(Id),
    primary_edge(Id, "r_argues_for_concern", Concern).


% -----------------------------------------------------------------------------
% Every type names exactly one schema for its items.
%
% decl schema_count(type:    symbol,
%                   schemas: number)
#show schema_count/2.

schema_count(Type, Schemas) :-
    type_prefix(Type, _, _),
    Schemas = #count { Schema :
                       primary_edge(Type, "r_has_items_specified_by_schema", Schema) },
    Schemas != 1.


% -----------------------------------------------------------------------------
% Every schema is used: named for the items of a type, named by a
% register for itself, or referred to by another schema.
%
% decl unused_schema(id: symbol)
#show unused_schema/1.

unused_schema(Id) :-
    type_of(Id, "t_schema"),
    not primary_edge(_, "r_has_items_specified_by_schema", Id),
    not primary_edge(_, "r_is_specified_by_schema", Id),
    not schema_ref(_, Id, _, _).


% -----------------------------------------------------------------------------
% The item is named by some item other than itself.
%
% decl named_by_other(id: symbol)

named_by_other(Id) :-
    reference(Holder, _, Id, _, _, _),
    Holder != Id.

named_by_other(Id) :-
    mention(Holder, Id, _, _),
    Holder != Id.


% -----------------------------------------------------------------------------
% Every concept is named by some item other than itself.
%
% decl unused_concept(id: symbol)
#show unused_concept/1.

unused_concept(Id) :-
    type_of(Id, "t_concept"),
    not named_by_other(Id).
