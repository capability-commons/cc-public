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
% did  {id} has a prefix that no type in reg_data_item_type has.
% fix  Give the item the prefix of its type. Add a type only when a real
%      instance needs it.
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
% did  {id} does not match {regex}, the regex_id of its type.
% fix  Rename the item with cctool rename to an id that matches.
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
% did  {guid}, the guid of {id}, is not the prefix of the id and 32 hex
%      digits.
% fix  Give the guid the prefix of the id and keep its digits. Never
%      write a guid by hand: cctool new mints one.
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
% did  {type} and {other} share the prefix {prefix}.
% fix  Give one of the two types a prefix of its own.
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
% did  The id {id} names two items, with the guids {guid} and {other}.
% fix  Rename one of the two with cctool rename. If one is a copy of the
%      other, remove the copy.
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
% did  The guid {guid} identifies two items, {id} and {other}.
% fix  A copy keeps the guid of what it copies. Make the new item with
%      cctool new, which mints a guid, and remove the copy.
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
% did  {id} is written here and again elsewhere.
% fix  Keep one copy of the item and remove the others.
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
% did  {id} is not named for what holds it. Its id is {expected}.
% fix  Rename the item with cctool rename to the id the check expects.
#show misplaced_module/2.

misplaced_module(Id, Expected) :-
    module_name(Id, Expected),
    Id != Expected.


% -----------------------------------------------------------------------------
% A document under a _data directory is in the folder named for its
% type, less the t_, in a file named for its id. A document that
% belongs to an issue is in the folder of the issue instead, so that
% everything argued about one issue is kept together.
%
% decl misplaced_document(id:       symbol,
%                         file:     symbol,
%                         expected: symbol)
% did  {id} is in {file}, not in {expected}.
% fix  Move the file to where the check expects it. Everything argued
%      about an issue goes in the folder of the issue.
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
% did  {register} holds {id}, an entry of {type}, which is not a type
%      whose items it holds.
% fix  Move the entry to the register of its type, or correct its type.
#show misplaced_register_entry/3.

misplaced_register_entry(Register, Id, Type) :-
    register_entry_key(Register, _, Id),
    type_of(Id, Type),
    not primary_edge(Type, "r_has_items_held_in_register", Register).


% -----------------------------------------------------------------------------
% Every python module and logic program file under src holds an item.
%
% decl unrecorded_module(file: symbol)
% did  {file} holds no item.
% fix  Give the file its item with cctool header PATH.
#show unrecorded_module/1.

unrecorded_module(File) :-
    tree_file(File),
    @match("src/.*\\.(py|lp)", File) = 1,
    not item(_, _, "", File, _).


% -----------------------------------------------------------------------------
% An interface member sits in an interface control document, and its
% id is the id of what it sits in, then a full stop and a name of its
% own. The member prefix takes the place of the prefix of the document.
%
% decl member_stem(holder: symbol,
%                  stem:   symbol)

member_stem(Holder, Stem) :-
    type_of(Holder, "t_interface_control_document"),
    Stem = @cat("icm_", @substr(Holder, 4, @strlen(Holder) - 4)).

member_stem(Holder, Holder) :-
    type_of(Holder, "t_interface_member").

% decl misnamed_member(id:     symbol,
%                      holder: symbol)
% did  The id of {id} is not the stem of {holder}, a full stop and a
%      name.
% fix  Rename the member with cctool rename to the stem of what it sits
%      in, a full stop, and its own name.
#show misnamed_member/2.

misnamed_member(Id, Holder) :-
    type_of(Id, "t_interface_member"),
    item(Id, _, Holder, _, _),
    not member_stem(Holder, _).

misnamed_member(Id, Holder) :-
    type_of(Id, "t_interface_member"),
    item(Id, _, Holder, _, _),
    member_stem(Holder, Stem),
    Length = @strlen(Stem) + 1,
    @substr(Id, 0, Length) != @cat(Stem, ".").

misnamed_member(Id, Holder) :-
    type_of(Id, "t_interface_member"),
    item(Id, _, Holder, _, _),
    member_stem(Holder, Stem),
    Length = @strlen(Stem) + 1,
    @match("[a-z0-9_]+", @substr(Id, Length, @strlen(Id) - Length)) = 0.


% -----------------------------------------------------------------------------
% A python function that realizes an interface member takes the
% parameters the member states, by name and in order. A parameter of a
% member is an interface member in its parameter list, named for it.
% stated or actual is empty where the member or the function has no
% parameter at that position.
%
% decl parameter_member(member:    symbol,
%                       position:  number,
%                       parameter: symbol)

parameter_member(Member, Position, Parameter) :-
    type_of(Parameter, "t_interface_member"),
    item(Parameter, _, Member, _, _),
    type_of(Member, "t_interface_member"),
    position(Parameter, Position).

% decl stated_parameter(member:   symbol,
%                       position: number,
%                       name:     symbol)

stated_parameter(Member, Position, Name) :-
    parameter_member(Member, Position, Id),
    Length = @strlen(Member) + 1,
    Name = @substr(Id, Length, @strlen(Id) - Length).

% decl realized_function(function: symbol,
%                        member:   symbol)

realized_function(Function, Member) :-
    primary_edge(Function, "r_realizes", Member),
    type_of(Function, "t_python_function"),
    type_of(Member, "t_interface_member").

% decl parameter_mismatch(member:   symbol,
%                         function: symbol,
%                         position: number,
%                         stated:   symbol,
%                         actual:   symbol)
% did  At position {position}, {member} states the parameter {stated},
%      and {function} takes {actual}.
% fix  Make the member and the code agree: change the member if the
%      interface has changed, or the code if it has drifted. An empty
%      value means no parameter is there.
#show parameter_mismatch/5.

parameter_mismatch(Member, Function, Position, Stated, Actual) :-
    realized_function(Function, Member),
    stated_parameter(Member, Position, Stated),
    python_parameter(Function, Position, Actual),
    Stated != Actual.

parameter_mismatch(Member, Function, Position, Stated, "") :-
    realized_function(Function, Member),
    stated_parameter(Member, Position, Stated),
    not python_parameter(Function, Position, _).

parameter_mismatch(Member, Function, Position, "", Actual) :-
    realized_function(Function, Member),
    python_parameter(Function, Position, Actual),
    not stated_parameter(Member, Position, _).


% -----------------------------------------------------------------------------
% What a member states of the signature it restates is what the python
% function that realizes it says: the type and default of each
% parameter as the code writes them, whether it is optional or
% variadic, and the type the function returns. member is the parameter
% member, or the function member for returns. A part the member does
% not state is not compared, and actual is empty where the code does
% not say.
%
% decl signature_mismatch(member:   symbol,
%                         function: symbol,
%                         part:     symbol,
%                         stated:   symbol,
%                         actual:   symbol)
% did  {member} states {stated} for the {part}, and {function} says
%      {actual}.
% fix  Make the member and the code agree: change the member if the
%      interface has changed, or the code if it has drifted. An empty
%      value means that side does not say.
#show signature_mismatch/5.

signature_mismatch(Parameter, Function, Part, Stated, Actual) :-
    realized_function(Function, Member),
    parameter_member(Member, Position, Parameter),
    stated(Parameter, Part, Stated),
    python_signature(Function, Position, Part, Actual),
    Stated != Actual.

signature_mismatch(Member, Function, "returns", Stated, Actual) :-
    realized_function(Function, Member),
    stated(Member, "returns", Stated),
    python_returns(Function, Actual),
    Stated != Actual.


% -----------------------------------------------------------------------------
% The key of a register entry is its id.
%
% decl key_mismatch(register: symbol,
%                   key:      symbol,
%                   id:       symbol)
% did  In {register}, the key {key} holds the entry {id}.
% fix  Make the key the id of the entry. cctool rename changes both.
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
%                         field:  symbol,
%                         id:     symbol,
%                         file:   symbol,
%                         line:   number)
% did  {holder} names {id} in its {field} field, and no item has that id
%      or guid.
% fix  Correct the id, or add the item it names. Do not remove the
%      reference only to quiet the check.
#show dangling_reference/5.

dangling_reference(Holder, Field, Id, File, Line) :-
    reference(Holder, Field, Id, Guid, File, Line),
    not item(Id, _, _, _, _),
    not item(_, Guid, _, _, _),
    not alias(_, Id),
    Field != "mark".


% -----------------------------------------------------------------------------
% Every reference carries the guid of the item it names.
%
% decl stale_guid(holder: symbol,
%                 field:  symbol,
%                 id:     symbol,
%                 guid:   symbol,
%                 file:   symbol,
%                 line:   number)
% did  {holder} names {id} in its {field} field with the guid {guid},
%      which is not the guid of {id}.
% fix  Copy the guid of the item named, or write the edge with cctool
%      link, which copies it.
#show stale_guid/6.

stale_guid(Holder, Field, Id, Guid, File, Line) :-
    reference(Holder, Field, Id, Guid, File, Line),
    item(Id, Other, _, _, _),
    Guid != Other.


% -----------------------------------------------------------------------------
% A type satisfies a relation restriction if any one of its literals
% holds: its items play a role the restriction admits, or do not play
% a role it excludes.
%
% decl satisfies(type:        symbol,
%                restriction: symbol)

satisfies(Type, Restriction) :-
    primary_edge(Restriction, "r_admits", Role),
    primary_edge(Type, "r_has_items_that_play", Role).

satisfies(Type, Restriction) :-
    primary_edge(Restriction, "r_excludes", Role),
    type_prefix(Type, _, _),
    not primary_edge(Type, "r_has_items_that_play", Role).


% -----------------------------------------------------------------------------
% Each end of an edge satisfies every restriction its relation names
% for that end. An end that names none is open to any item.
%
% decl restriction_violation(source:      symbol,
%                            relation:    symbol,
%                            target:      symbol,
%                            end:         symbol,
%                            restriction: symbol)
% did  The edge {source} {relation} {target} breaks {restriction} at its
%      {end} end.
% fix  Point the edge at an item of a type the relation admits, or use
%      the relation that fits. Its entry in reg_relation.yaml names its
%      restrictions.
#show restriction_violation/5.

restriction_violation(Source, Relation, Target, "source", Restriction) :-
    primary_edge(Source, Relation, Target),
    primary_edge(Relation, "r_restricts_source", Restriction),
    type_of(Source, Type),
    not satisfies(Type, Restriction).

restriction_violation(Source, Relation, Target, "target", Restriction) :-
    primary_edge(Source, Relation, Target),
    primary_edge(Relation, "r_restricts_target", Restriction),
    type_of(Target, Type),
    not satisfies(Type, Restriction).


% -----------------------------------------------------------------------------
% Every annotation and every issue is about something.
%
% decl missing_about(id: symbol)
% did  {id} is about nothing: it has no edge of r_is_about.
% fix  Link it to its subject with cctool link ID r_is_about TARGET.
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
% did  The decision {decision} answers {issues} issues, not 1.
% fix  Give the decision one edge of r_answers, to the issue it answers.
#show answer_count/2.

answer_count(Decision, Issues) :-
    type_of(Decision, "t_decision"),
    Issues = #count { Issue : primary_edge(Decision, "r_answers", Issue) },
    Issues != 1.


% -----------------------------------------------------------------------------
% Every determination upholds or rejects at least one decision.
%
% decl determination_without_decision(id: symbol)
% did  The determination {id} neither upholds nor rejects a decision.
% fix  Link it with r_upholds or r_rejects to each decision it settles.
#show determination_without_decision/1.

determination_without_decision(Id) :-
    type_of(Id, "t_determination"),
    not primary_edge(Id, "r_upholds", _),
    not primary_edge(Id, "r_rejects", _).


% -----------------------------------------------------------------------------
% A determination settles the decisions of one issue.
%
% decl determination_across_issues(determination: symbol,
%                                  issue:         symbol,
%                                  other:         symbol)
% did  The determination {determination} settles decisions of both
%      {issue} and {other}.
% fix  Settle each issue with a determination of its own.
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
% did  The issue {issue} is about {target}, of {type}, which is not a
%      logical component.
% fix  Make the issue about the logical component whose design it
%      decides.
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
% did  The annotation {annotation} of {issue} argues with {target}, of
%      {other}.
% fix  Argue within one issue: point the edge at an item of the same
%      issue, or move the annotation to the issue it argues.
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
% decision, and an interface control document another.
%
% decl supersession_across_types(source: symbol,
%                                target: symbol)
% did  {source} supersedes {target}, an item of another type.
% fix  Supersede only an item of the same type.
#show supersession_across_types/2.

supersession_across_types(Source, Target) :-
    primary_edge(Source, "r_supersedes", Target),
    type_of(Source, Type),
    not type_of(Target, Type).


% -----------------------------------------------------------------------------
% An issue has at most one determination. A change of ruling edits it in
% place, and the history of the ruling is the history of its file.
%
% decl competing_determinations(issue:         symbol,
%                               determination: symbol,
%                               other:         symbol)
% did  The issue {issue} has two determinations, {determination} and
%      {other}.
% fix  Keep one determination and edit it in place when the ruling
%      changes. Git keeps the history of the ruling.
#show competing_determinations/3.

competing_determinations(Issue, Determination, Other) :-
    type_of(Determination, "t_determination"),
    type_of(Other, "t_determination"),
    issue_of(Determination, Issue),
    issue_of(Other, Issue),
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
% A determination upholds a decision only once every concern that
% drives the subject of its issue has been argued, for it or for an
% alternative to it. It may reject a decision at any time, since a
% rejection commits the subject to nothing.
%
% decl unargued_driver(determination: symbol,
%                      decision:      symbol,
%                      concern:       symbol)
% did  {determination} upholds {decision}, and no annotation argues
%      {concern}, a driver, for it or an alternative to it.
% fix  Add an annotation for that concern to the decision or an
%      alternative, or leave the decision open. Do not uphold a
%      decision while a driver of its issue is unargued.
#show unargued_driver/3.

unargued_driver(Determination, Decision, Concern) :-
    type_of(Determination, "t_determination"),
    primary_edge(Determination, "r_upholds", Decision),
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
% did  {file} cannot be read at line {line}: {message}
% fix  Correct the file so it parses. Until it does, no other check sees
%      its items.
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
% did  The text of {holder} mentions {id}, and no item has that id.
% fix  Correct the id, add the item, or say it in prose without the
%      prefix.
#show dangling_mention/4.

dangling_mention(Holder, Id, File, Line) :-
    mention(Holder, Id, File, Line),
    Prefix = @prefix(Id),
    type_prefix(_, Prefix, _),
    not item(Id, _, _, _, _),
    not item(_, Id, _, _, _),
    not alias(_, Id).


% -----------------------------------------------------------------------------
% An alias is an old id, so no item has it.
%
% decl alias_in_use(alias: symbol,
%                   id:    symbol)
% did  {alias}, an alias of {id}, is the id of an item.
% fix  An alias is an old id. Take it out of the alias list, or rename
%      the item that has it.
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
%                         field:  symbol,
%                         alias:  symbol,
%                         id:     symbol,
%                         file:   symbol,
%                         line:   number)
% did  {holder} names {alias} in its {field} field, an old id of {id}.
% fix  Name the item by its current id.
#show outdated_reference/6.

outdated_reference(Holder, Field, Alias, Id, File, Line) :-
    reference(Holder, Field, Alias, _, File, Line),
    alias(Id, Alias),
    not item(Alias, _, _, _, _).

outdated_reference(Holder, Field, Old, Id, File, Line) :-
    reference(Holder, Field, Old, Guid, File, Line),
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
% did  The text of {holder} mentions {alias}, an old id of {id}.
% fix  Mention the item by its current id.
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
% did  A chain of edges of {relation} leads from {id} back to itself.
% fix  The relation is acyclic. Find the edge of the chain that is
%      wrong, and remove or correct it.
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
% did  The annotation {id} supports or challenges a decision and argues
%      for no concern.
% fix  Link it with r_argues_for_concern to each concern it speaks for.
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
% did  The annotation {id} argues for {concern} and bears on no
%      decision.
% fix  A fact is answered with evidence, not weighed by concern. Remove
%      the edge to the concern, or link the annotation to the decision
%      it argues.
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
% did  The type {type} names {schemas} schemas for its items, not 1.
% fix  Give the type one edge of r_has_items_specified_by_schema.
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
% did  Nothing uses the schema {id}.
% fix  Name it from a type, a register or another schema, or remove it.
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
% did  No item but itself names the concept {id}.
% fix  Name the concept from the item that needs it, made with it in one
%      cctool batch, or remove the concept.
#show unused_concept/1.

unused_concept(Id) :-
    type_of(Id, "t_concept"),
    not named_by_other(Id).


% -----------------------------------------------------------------------------
% A node is named for the system configuration that holds it and the
% key it is filed under: the stem of the configuration, with nod in
% place of sys, a full stop and the key.
%
% decl misnamed_node(node:     symbol,
%                    expected: symbol)
% did  The node {node} is not named for the system configuration that
%      holds it and its key. Its id is {expected}.
% fix  Rename the node with cctool rename to the id the check expects.
#show misnamed_node/2.

misnamed_node(Node, Expected) :-
    system_node(System, Key, Node, _),
    Expected = @cat("nod_", @substr(System, 4, @strlen(System) - 4), ".", Key),
    Node != Expected.


% -----------------------------------------------------------------------------
% Every node presents exactly one interface: it realizes one interface
% control document, whose dataflow step surface it presents.
%
% decl interface_count(node:       symbol,
%                      interfaces: number)
% did  The node {node} realizes {interfaces} interface control
%      documents, not 1.
% fix  Give the node one edge of r_realizes to the interface control
%      document whose dataflow step surface it presents.
#show interface_count/2.

interface_count(Node, Interfaces) :-
    type_of(Node, "t_dataflow_node"),
    Interfaces = #count { Interface : node_interface(Node, Interface) },
    Interfaces != 1.


% -----------------------------------------------------------------------------
% Each end of an edge of a system configuration, with the kind of port
% it must name: an output at the source, and an input at the target.
%
% decl edge_end(system: symbol,
%               end:    symbol,
%               node:   symbol,
%               port:   symbol,
%               kind:   symbol,
%               file:   symbol,
%               line:   number)

edge_end(System, "source", Node, Port, "output", File, Line) :-
    system_edge(System, Node, Port, _, _, _, File, Line).

edge_end(System, "target", Node, Port, "input", File, Line) :-
    system_edge(System, _, _, Node, Port, _, File, Line).


% -----------------------------------------------------------------------------
% Each end of an edge names a node of the system configuration that
% holds the edge.
%
% decl foreign_node(system: symbol,
%                   end:    symbol,
%                   node:   symbol,
%                   file:   symbol,
%                   line:   number)
% did  The {end} of an edge of {system} names {node}, which is not one
%      of its nodes.
% fix  Name a node that the system configuration holds, or add the node
%      to it.
#show foreign_node/5.

foreign_node(System, End, Node, File, Line) :-
    edge_end(System, End, Node, _, _, File, Line),
    not system_node(System, _, Node, _).


% -----------------------------------------------------------------------------
% Each end of an edge names a port of the interface its node presents,
% of the kind the end needs: an output at the source and an input at
% the target.
%
% decl unknown_port(node: symbol,
%                   port: symbol,
%                   kind: symbol,
%                   file: symbol,
%                   line: number)
% did  An edge names {port} at {node}, which is not an {kind} of the
%      interface the node presents.
% fix  Name a port of that kind from the dataflow step surface of the
%      interface the node realizes, or add the port to the surface.
#show unknown_port/5.

unknown_port(Node, Port, Kind, File, Line) :-
    edge_end(_, _, Node, Port, Kind, File, Line),
    node_interface(Node, Interface),
    not interface_port(Interface, Kind, _, Port).


% -----------------------------------------------------------------------------
% The node takes a value at the port from an edge of its system
% configuration.
%
% decl fed(node: symbol,
%          port: symbol)

fed(Node, Port) :-
    system_edge(_, _, _, Node, Port, _, _, _).


% -----------------------------------------------------------------------------
% An input takes its value from at most one edge.
%
% decl input_fed_twice(node:  symbol,
%                      port:  symbol,
%                      edges: number)
% did  {edges} edges end at the input {port} of {node}, not 1.
% fix  Keep one edge into the input. To combine values, add a node that
%      reads each of them on an input of its own.
#show input_fed_twice/3.

input_fed_twice(Node, Port, Edges) :-
    fed(Node, Port),
    Edges = #count { Source, Output : system_edge(_, Source, Output, Node, Port, _, _, _) },
    Edges > 1.


% -----------------------------------------------------------------------------
% Every input that the interface of a node does not state to be
% optional takes its value from an edge.
%
% decl unfed_input(node: symbol,
%                  port: symbol)
% did  No edge ends at the input {port} of {node}, and the interface
%      does not state that it is optional.
% fix  Add an edge into the input, or state optional: true for it in the
%      interface if a step may run without it.
#show unfed_input/2.

unfed_input(Node, Port) :-
    system_node(_, _, Node, _),
    node_interface(Node, Interface),
    interface_port(Interface, "input", _, Port),
    not stated(Port, "optional", "true"),
    not fed(Node, Port).


% -----------------------------------------------------------------------------
% The ports at the two ends of an edge state the same type, where both
% state one.
%
% decl port_type_mismatch(source_port: symbol,
%                         source_type: symbol,
%                         target_port: symbol,
%                         target_type: symbol,
%                         file:        symbol,
%                         line:        number)
% did  An edge carries {source_type} from {source_port} into
%      {target_port}, which takes {target_type}.
% fix  Connect ports of the same type, or correct the type an interface
%      states. Add a node that converts the value if both are right.
#show port_type_mismatch/6.

port_type_mismatch(SourcePort, SourceType, TargetPort, TargetType, File, Line) :-
    system_edge(_, _, SourcePort, _, TargetPort, _, File, Line),
    stated(SourcePort, "type", SourceType),
    stated(TargetPort, "type", TargetType),
    SourceType != TargetType.


% -----------------------------------------------------------------------------
% Data from the node reaches the node other through feedforward edges
% only.
%
% decl feeds_forward(node:  symbol,
%                    other: symbol)

feeds_forward(Node, Other) :-
    feeds(Node, Other, "feedforward").

feeds_forward(Node, Other) :-
    feeds_forward(Node, Between),
    feeds(Between, Other, "feedforward").


% -----------------------------------------------------------------------------
% Every loop of data flow is closed by a feedback edge, whose value
% comes from the invocation before. A loop of feedforward edges only
% has a node wait on its own output, which never comes.
%
% decl feedforward_loop(node: symbol)
% did  Data from {node} comes back to it through feedforward edges only,
%      so it waits on its own output.
% fix  Give the edge that closes the loop direction: feedback.
#show feedforward_loop/1.

feedforward_loop(Node) :-
    feeds_forward(Node, Node).


% -----------------------------------------------------------------------------
% A node is configured only with settings its interface declares.
%
% decl unknown_setting(node:    symbol,
%                      setting: symbol)
% did  {node} gives a value for {setting}, which is not a setting of
%      the interface it presents.
% fix  Correct the name of the setting, or add the setting to the
%      dataflow step surface of the interface.
#show unknown_setting/2.

unknown_setting(Node, Setting) :-
    system_setting(Node, Setting),
    node_interface(Node, Interface),
    not interface_port(Interface, "config", Setting, _).


% -----------------------------------------------------------------------------
% A node gives a value for each setting that its interface neither
% states to be optional nor gives a default.
%
% decl missing_setting(node:    symbol,
%                      setting: symbol)
% did  {node} gives no value for {setting}, which its interface needs.
% fix  Give the setting a value in the config of the node.
#show missing_setting/2.

missing_setting(Node, Setting) :-
    system_node(_, _, Node, _),
    node_interface(Node, Interface),
    interface_port(Interface, "config", Setting, Member),
    not stated(Member, "optional", "true"),
    not stated(Member, "default", _),
    not system_setting(Node, Setting).


% -----------------------------------------------------------------------------
% A node runs on a process of its system configuration, and a process
% on a host of it.
%
% decl unplaced(system: symbol,
%               holder: symbol,
%               key:    symbol)
% did  {holder} in {system} runs on {key}, which the system
%      configuration does not list.
% fix  Name a process or host the system configuration lists, or add it
%      to the process or host section.
#show unplaced/3.

unplaced(System, Node, Process) :-
    system_node(System, _, Node, Process),
    Process != "",
    not system_process(System, Process, _).

unplaced(System, Process, Host) :-
    system_process(System, Process, Host),
    not system_host(System, Host).
