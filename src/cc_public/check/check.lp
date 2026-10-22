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
%                         Each shown predicate is one check, and each
%                         row of it is one failure. A check that points
%                         at a place in a file reports the file, and the
%                         line where there is one.
% usage:                  |
%                         Evaluated by pym_cc_public.check.check. The
%                         facts of the base predicates and the rules of
%                         lpf_cc_public.graph.derive come before this
%                         file in the program.
% edge:                   []
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
    has_type(Id, Type),
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
% The regex_id of a type opens with its prefix, so that every id the
% regex admits has the prefix of its type. sch_regentry_type leaves
% this to a check, as JSON Schema cannot compare two fields.
%
% decl regex_without_prefix(type:   symbol,
%                           prefix: symbol,
%                           regex:  symbol)
% did  The regex_id {regex} of {type} does not open with ^{prefix}_.
% fix  Begin the regex_id with a caret, the prefix and an underscore.
#show regex_without_prefix/3.

regex_without_prefix(Type, Prefix, Regex) :-
    type_prefix(Type, Prefix, Regex),
    @match(@cat(@cat("\\^", Prefix), "_.*"), Regex) = 0.


% -----------------------------------------------------------------------------
% The $id of a schema ends with its id_self and .yaml, which is also the
% name of its file. sch_schema leaves this to a check, as JSON Schema
% cannot compare two fields.
%
% decl misnamed_schema(schema: symbol,
%                      uri:    symbol,
%                      file:   symbol,
%                      line:   number)
% did  The $id {uri} of {schema} does not end with /{schema}.yaml.
% fix  End the $id with the id_self of the schema and .yaml.
#show misnamed_schema/4.

misnamed_schema(Schema, Uri, File, Line) :-
    schema_uri(Schema, Uri, File, Line),
    @match(@cat(@cat(".*/", Schema), "\\.yaml"), Uri) = 0.


% -----------------------------------------------------------------------------
% A prefix is three lower-case letters, one whole word of the preferred
% term of the concept its type represents, or the first three letters of
% each of two or three words of that term in a row, as relcon for
% relation constraint. A type whose prefix is none of these states why
% in its prefix_exception field.
%
% decl prefix_form(type:   symbol,
%                  prefix: symbol)
% did  The prefix {prefix} of {type} is not three letters, a word of its
%      preferred term, or the first three letters of words of it in a row.
% fix  Choose three letters from the preferred term, one whole word of it,
%      or the first three letters of two or three of its words in a row, or
%      say in prefix_exception why the prefix must stay.
#show prefix_form/2.

prefix_form(Type, Prefix) :-
    type_prefix(Type, Prefix, _),
    @match("[a-z]{3}", Prefix) = 0,
    not prefix_is_word(Type),
    not prefix_is_contraction(Type),
    not prefix_exception(Type, _).

prefix_is_word(Type) :-
    type_prefix(Type, Prefix, _),
    reference(Type, "concept", Concept, _, _, _),
    designation(Concept, Term, "preferred"),
    @match(@cat("(.* )?", Prefix, "( .*)?"), Term) = 1.

prefix_is_contraction(Type) :-
    type_prefix(Type, Prefix, _),
    @strlen(Prefix) = 6,
    reference(Type, "concept", Concept, _, _, _),
    designation(Concept, Term, "preferred"),
    @match(@cat("(.* )?", @substr(Prefix, 0, 3), "[a-z]* ",
                @substr(Prefix, 3, 3), "[a-z]*( .*)?"), Term) = 1.

prefix_is_contraction(Type) :-
    type_prefix(Type, Prefix, _),
    @strlen(Prefix) = 9,
    reference(Type, "concept", Concept, _, _, _),
    designation(Concept, Term, "preferred"),
    @match(@cat("(.* )?", @substr(Prefix, 0, 3), "[a-z]* ",
                @substr(Prefix, 3, 3), "[a-z]* ",
                @substr(Prefix, 6, 3), "[a-z]*( .*)?"), Term) = 1.


% -----------------------------------------------------------------------------
% Two prefixes of the same length differ in more than one letter,
% unless their types declare one prefix family, as a container and its
% members do.
%
% decl prefix_near(type:   symbol,
%                  prefix: symbol,
%                  other:  symbol,
%                  near:   symbol)
% did  The prefix {prefix} of {type} differs by one letter from {near}, the
%      prefix of {other}.
% fix  Choose a prefix further from the other, or give both types the same
%      prefix_family if they belong together.
#show prefix_near/4.

prefix_near(Type, Prefix, Other, Near) :-
    type_prefix(Type, Prefix, _),
    type_prefix(Other, Near, _),
    Type != Other,
    @strlen(Prefix) = @strlen(Near),
    #count { Index : prefix_letter_differs(Type, Other, Index) } = 1,
    not prefix_family_shared(Type, Other).

prefix_letter_differs(Type, Other, Index) :-
    type_prefix(Type, Prefix, _),
    type_prefix(Other, Near, _),
    Type != Other,
    @strlen(Prefix) = @strlen(Near),
    Index = 0..@strlen(Prefix) - 1,
    @substr(Prefix, Index, 1) != @substr(Near, Index, 1).

prefix_family_shared(Type, Other) :-
    prefix_family(Type, Family),
    prefix_family(Other, Family).


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
% A YAML document under a _data directory is in the folder named for its
% type, less the type_, in a file named for its id. A document that
% belongs to a decision is in the folder of the decision instead, so that
% everything argued about one decision is kept together.
%
% decl misplaced_document(id:       symbol,
%                         file:     symbol,
%                         expected: symbol)
% did  {id} is in {file}, not in {expected}.
% fix  Move the file to where the check expects it. Everything argued
%      about a decision goes in the folder of the decision.
#show misplaced_document/3.

misplaced_document(Id, File, Expected) :-
    item(Id, _, "", File, _),
    @match("(.*/)?_data/.*\\.yaml", File) = 1,
    not decision_of(Id, _),
    has_type(Id, Type),
    Stem     = @substr(Type, 5, @strlen(Type) - 5),
    Expected = @cat("_data/", Stem, "/", Id, ".yaml"),
    @match(@cat("(.*/)?", Expected), File) = 0.

misplaced_document(Id, File, Expected) :-
    item(Id, _, "", File, _),
    @match("(.*/)?_data/.*\\.yaml", File) = 1,
    decision_of(Id, Decision),
    Expected = @cat("_data/decision/", Decision, "/", Id, ".yaml"),
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
    has_type(Id, Type),
    not primary_edge(Type, "relation_has_items_held_in_register", Register).


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
    has_type(Holder, "type_interface_control_document"),
    Stem = @cat("icm_", @substr(Holder, 4, @strlen(Holder) - 4)).

member_stem(Holder, Holder) :-
    has_type(Holder, "type_interface_member").

% decl misnamed_member(id:     symbol,
%                      holder: symbol)
% did  The id of {id} is not the stem of {holder}, a full stop and a
%      name.
% fix  Rename the member with cctool rename to the stem of what it sits
%      in, a full stop, and its own name. To rename the interface
%      control document, use cctool rename, which renames its members
%      with it.
#show misnamed_member/2.

misnamed_member(Id, Holder) :-
    has_type(Id, "type_interface_member"),
    item(Id, _, Holder, _, _),
    not member_stem(Holder, _).

misnamed_member(Id, Holder) :-
    has_type(Id, "type_interface_member"),
    item(Id, _, Holder, _, _),
    member_stem(Holder, Stem),
    Length = @strlen(Stem) + 1,
    @substr(Id, 0, Length) != @cat(Stem, ".").

misnamed_member(Id, Holder) :-
    has_type(Id, "type_interface_member"),
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
    has_type(Parameter, "type_interface_member"),
    item(Parameter, _, Member, _, _),
    has_type(Member, "type_interface_member"),
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
    primary_edge(Function, "relation_realizes", Member),
    has_type(Function, "type_python_function"),
    has_type(Member, "type_interface_member").

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
% decl guid_mismatch(holder: symbol,
%                    field:  symbol,
%                    id:     symbol,
%                    guid:   symbol,
%                    file:   symbol,
%                    line:   number)
% did  {holder} names {id} in its {field} field with the guid {guid},
%      which is not the guid of {id}.
% fix  Copy the guid of the item named, or write the edge with cctool
%      link, which copies it.
#show guid_mismatch/6.

guid_mismatch(Holder, Field, Id, Guid, File, Line) :-
    reference(Holder, Field, Id, Guid, File, Line),
    item(Id, Other, _, _, _),
    Guid != Other.


% -----------------------------------------------------------------------------
% A type satisfies a relation constraint if any one of its literals
% holds: its items play a role the constraint admits, or do not play
% a role it excludes.
%
% decl satisfies(type:        symbol,
%                constraint: symbol)

satisfies(Type, Constraint) :-
    primary_edge(Constraint, "relation_admits", Role),
    primary_edge(Type, "relation_has_items_that_play", Role).

satisfies(Type, Constraint) :-
    primary_edge(Constraint, "relation_excludes", Role),
    type_prefix(Type, _, _),
    not primary_edge(Type, "relation_has_items_that_play", Role).


% -----------------------------------------------------------------------------
% Each end of an edge satisfies every constraint its relation names
% for that end. An end that names none is open to any item.
%
% decl constraint_violation(source:      symbol,
%                            relation:    symbol,
%                            target:      symbol,
%                            end:         symbol,
%                            constraint: symbol)
% did  The edge {source} {relation} {target} breaks {constraint} at its
%      {end} end.
% fix  Point the edge at an item of a type the relation admits, or use
%      the relation that fits. Its entry in reg_relation.yaml names its
%      constraints.
#show constraint_violation/5.

constraint_violation(Source, Relation, Target, "source", Constraint) :-
    primary_edge(Source, Relation, Target),
    primary_edge(Relation, "relation_constrains_source", Constraint),
    has_type(Source, Type),
    not satisfies(Type, Constraint).

constraint_violation(Source, Relation, Target, "target", Constraint) :-
    primary_edge(Source, Relation, Target),
    primary_edge(Relation, "relation_constrains_target", Constraint),
    has_type(Target, Type),
    not satisfies(Type, Constraint).


% -----------------------------------------------------------------------------
% Every annotation and every decision is about something.
%
% decl missing_about(id: symbol)
% did  {id} is about nothing: it has no edge of relation_is_about.
% fix  Link it to its subject with cctool link ID relation_is_about TARGET.
#show missing_about/1.

missing_about(Id) :-
    has_type(Id, "type_annotation"),
    not primary_edge(Id, "relation_is_about", _).

missing_about(Id) :-
    has_type(Id, "type_decision"),
    not primary_edge(Id, "relation_is_about", _).


% -----------------------------------------------------------------------------
% Every option is an option for exactly one decision. The options for
% a decision are its alternatives.
%
% decl option_count(option:    symbol,
%                   decisions: number)
% did  The option {option} is an option for {decisions} decisions, not 1.
% fix  Give the option one edge of relation_is_option_for, to its decision.
#show option_count/2.

option_count(Option, Decisions) :-
    has_type(Option, "type_option"),
    Decisions = #count { Decision : primary_edge(Option, "relation_is_option_for", Decision) },
    Decisions != 1.


% -----------------------------------------------------------------------------
% Every ruling upholds or rejects at least one option.
%
% decl no_option_in_ruling(id: symbol)
% did  The ruling {id} neither upholds nor rejects an option.
% fix  Link it with relation_upholds or relation_rejects to each option it settles.
#show no_option_in_ruling/1.

no_option_in_ruling(Id) :-
    has_type(Id, "type_ruling"),
    not primary_edge(Id, "relation_upholds", _),
    not primary_edge(Id, "relation_rejects", _).


% -----------------------------------------------------------------------------
% A ruling settles the options of one decision.
%
% decl decisions_mixed_in_ruling(ruling:   symbol,
%                                decision: symbol,
%                                other:    symbol)
% did  The ruling {ruling} settles options of both
%      {decision} and {other}.
% fix  Settle each decision with a ruling of its own.
#show decisions_mixed_in_ruling/3.

decisions_mixed_in_ruling(Ruling, Decision, Other) :-
    has_type(Ruling, "type_ruling"),
    decision_of(Ruling, Decision),
    decision_of(Ruling, Other),
    Decision < Other.


% -----------------------------------------------------------------------------
% An annotation either supports or challenges a target, never both.
% One that qualifies another challenges it.
%
% decl supports_and_challenges(annotation: symbol,
%                              target:     symbol)
% did  The annotation {annotation} both supports and challenges {target}.
% fix  Keep the edge the annotation argues, or split it into two
%      annotations that each argue one way.
#show supports_and_challenges/2.

supports_and_challenges(Annotation, Target) :-
    primary_edge(Annotation, "relation_supports", Target),
    primary_edge(Annotation, "relation_challenges", Target).


% -----------------------------------------------------------------------------
% A ruling either upholds or rejects an option, never both.
%
% decl upholds_and_rejects(ruling: symbol,
%                          option: symbol)
% did  The ruling {ruling} both upholds and rejects {option}.
% fix  Keep the one edge the ruling means.
#show upholds_and_rejects/2.

upholds_and_rejects(Ruling, Option) :-
    primary_edge(Ruling, "relation_upholds", Option),
    primary_edge(Ruling, "relation_rejects", Option).


% -----------------------------------------------------------------------------
% A decision is about logical components, since their drivers say which
% concerns must be argued before an option of the decision is settled.
% A decision about anything else would escape that check.
%
% decl decision_about_non_component(decision: symbol,
%                                   target:   symbol,
%                                   type:     symbol)
% did  The decision {decision} is about {target}, of {type}, which is not a
%      logical component.
% fix  Make the decision about the logical component whose design it
%      decides.
#show decision_about_non_component/3.

decision_about_non_component(Decision, Target, Type) :-
    has_type(Decision, "type_decision"),
    primary_edge(Decision, "relation_is_about", Target),
    has_type(Target, Type),
    Type != "type_logical_component".


% -----------------------------------------------------------------------------
% An annotation argues within its decision: what it supports or challenges
% belongs to the same decision as it does.
%
% decl argument_across_decisions(annotation: symbol,
%                                decision:   symbol,
%                                target:     symbol,
%                                other:      symbol)
% did  The annotation {annotation} of {decision} argues with {target}, of
%      {other}.
% fix  Argue within one decision: point the edge at an item of the same
%      decision, or move the annotation to the decision it argues.
#show argument_across_decisions/4.

argument_across_decisions(Annotation, Decision, Target, Other) :-
    has_type(Annotation, "type_annotation"),
    primary_edge(Annotation, Relation, Target),
    argues(Relation),
    decision_of(Annotation, Decision),
    decision_of(Target, Other),
    Decision != Other.


% -----------------------------------------------------------------------------
% An annotation argues with what it supports or challenges.
%
% decl argues(relation: symbol)

argues("relation_supports").
argues("relation_challenges").


% -----------------------------------------------------------------------------
% An item supersedes only an item of its own type: an option another
% option, and an interface control document another.
%
% decl supersession_across_types(source: symbol,
%                                target: symbol)
% did  {source} supersedes {target}, an item of another type.
% fix  Supersede only an item of the same type.
#show supersession_across_types/2.

supersession_across_types(Source, Target) :-
    primary_edge(Source, "relation_supersedes", Target),
    has_type(Source, Type),
    not has_type(Target, Type).


% -----------------------------------------------------------------------------
% A decision has at most one ruling. A change of ruling edits it in
% place, and the history of the ruling is the history of its file.
%
% decl competing_rulings(decision: symbol,
%                        ruling:   symbol,
%                        other:    symbol)
% did  The decision {decision} has two rulings, {ruling} and
%      {other}.
% fix  Keep one ruling and edit it in place when the ruling
%      changes. Git keeps the history of the ruling.
#show competing_rulings/3.

competing_rulings(Decision, Ruling, Other) :-
    has_type(Ruling, "type_ruling"),
    has_type(Other, "type_ruling"),
    decision_of(Ruling, Decision),
    decision_of(Other, Decision),
    Ruling < Other.


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
% A ruling upholds an option only once every concern that
% drives the subject of its decision has been argued, for it or for an
% alternative to it. It may reject an option at any time, since a
% rejection commits the subject to nothing.
%
% decl unargued_driver(ruling:  symbol,
%                      option:  symbol,
%                      concern: symbol)
% did  {ruling} upholds {option}, and no annotation argues
%      {concern}, a driver, for it or an alternative to it.
% fix  Add an annotation for that concern to the option or an
%      alternative, or leave the option open. Do not uphold an
%      option while a driver of its decision is unargued.
#show unargued_driver/3.

unargued_driver(Ruling, Option, Concern) :-
    has_type(Ruling, "type_ruling"),
    primary_edge(Ruling, "relation_upholds", Option),
    primary_edge(Option, "relation_is_option_for", Decision),
    primary_edge(Decision, "relation_is_about", Subject),
    primary_edge(Subject, "relation_is_driven_by", Concern),
    not argued(Option, Concern).


% -----------------------------------------------------------------------------
% Every file that ought to hold a YAML document can be read: a YAML file
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
% A text uses none of the words that a writing style rule asks to
% replace, outside double quotes and the breaks example of a rule.
%
% decl word_to_replace(holder:    symbol,
%                      word:      symbol,
%                      preferred: symbol,
%                      rule:      symbol,
%                      file:      symbol,
%                      line:      number)
% did  The text of {holder} uses {word}, which {rule} asks to write as
%      {preferred}.
% fix  Write the preferred word. A quotation keeps its own spelling
%      inside double quotes.
#show word_to_replace/6.

word_to_replace(Holder, Word, Preferred, Rule, File, Line) :-
    avoided_word(Holder, Word, File, Line),
    word_replacement(Rule, Word, Preferred).


% -----------------------------------------------------------------------------
% A link [[term]] finds its concept among the concepts that the item
% holding it uses, or that an item holding that item uses: the one with
% a preferred or admitted term of the same form.
%
% decl unresolved_term(holder: symbol,
%                      term:   symbol,
%                      file:   symbol,
%                      line:   number)
% did  {holder} links [[{term}]], and no concept it uses has that term.
% fix  Add an edge of relation_uses_concept from the item to the
%      concept meant, or write a term that concept gives.
#show unresolved_term/4.

unresolved_term(Holder, Term, File, Line) :-
    term_link(Holder, Term, "", File, Line),
    not term_has_sense(Holder, Term).


% -----------------------------------------------------------------------------
% A link [[term]] finds one concept. Where the item uses two concepts
% with that term, each link to either is written [[concept|term]].
%
% decl ambiguous_term(holder:   symbol,
%                     term:     symbol,
%                     concepts: number,
%                     file:     symbol,
%                     line:     number)
% did  {holder} links [[{term}]], and {concepts} concepts it uses have
%      that term.
% fix  Name the concept meant in each such link, as [[concept|term]].
#show ambiguous_term/5.

ambiguous_term(Holder, Term, Concepts, File, Line) :-
    term_link(Holder, Term, "", File, Line),
    Concepts = #count { Concept : term_sense(Holder, Term, Concept) },
    Concepts > 1.


% -----------------------------------------------------------------------------
% A link [[concept|term]] names a concept that the item uses.
%
% decl unused_linked_concept(holder:  symbol,
%                            concept: symbol,
%                            file:    symbol,
%                            line:    number)
% did  {holder} links to {concept}, which it does not use.
% fix  Add an edge of relation_uses_concept from the item to the
%      concept, or link to a concept the item uses.
#show unused_linked_concept/4.

unused_linked_concept(Holder, Concept, File, Line) :-
    term_link(Holder, _, Concept, File, Line),
    Concept != "",
    not uses_concept(Holder, Concept).


% -----------------------------------------------------------------------------
% The item uses the concept: it declares the use, or it is a concept
% itself, since a concept is defined in the terms of the others.
%
% decl uses_concept(holder:  symbol,
%                   concept: symbol)

uses_concept(Holder, Concept) :-
    declares_concept(Holder, Concept).

uses_concept(Holder, Concept) :-
    has_type(Holder, "type_concept"),
    has_type(Concept, "type_concept").


% -----------------------------------------------------------------------------
% The item declares that it uses the concept: it, or an item that holds
% it, has an edge of relation_uses_concept to the concept.
%
% decl declares_concept(holder:  symbol,
%                       concept: symbol)

declares_concept(Holder, Concept) :-
    primary_edge(Holder, "relation_uses_concept", Concept).

declares_concept(Holder, Concept) :-
    item(Holder, _, Container, _, _),
    Container != "",
    declares_concept(Container, Concept).


% -----------------------------------------------------------------------------
% A link [[term]] in the item could mean the concept: the item uses it,
% and one of its preferred or admitted terms has a form of the term.
%
% decl term_sense(holder:  symbol,
%                 term:    symbol,
%                 concept: symbol)

term_sense(Holder, Term, Concept) :-
    term_link(Holder, Term, "", _, _),
    uses_concept(Holder, Concept),
    designation(Concept, Designation, Rating),
    Rating != "deprecated",
    term_form(Term, Form),
    term_form(Designation, Form).


% -----------------------------------------------------------------------------
% The link [[term]] in the item finds at least one concept.
%
% decl term_has_sense(holder: symbol,
%                     term:   symbol)

term_has_sense(Holder, Term) :-
    term_sense(Holder, Term, _).


% -----------------------------------------------------------------------------
% A concept rates each of its terms once: a term is preferred, admitted
% or deprecated, never two of these, as ISO 1087 rates a designation.
%
% decl term_rated_twice(concept: symbol,
%                       term:    symbol,
%                       rating:  symbol,
%                       other:   symbol)
% did  {concept} rates the term "{term}" both {rating} and {other}.
% fix  Keep the one rating the concept means, and take the term out of
%      the other list.
#show term_rated_twice/4.

term_rated_twice(Concept, Term, Rating, Other) :-
    designation(Concept, Term, Rating),
    designation(Concept, Twin, Other),
    Rating < Other,
    term_form(Term, Form),
    term_form(Twin, Form).


% -----------------------------------------------------------------------------
% A strict field links every term it uses. The definition of a concept
% and the slots of a requirement statement are short, and they are
% where a term is most often meant in its registered sense, so a term
% in them is written as a link, which the link checks then hold to its
% concept. A concept's own terms are exempt from its definition.
%
% decl unlinked_term(holder: symbol,
%                    field:  symbol,
%                    term:   symbol,
%                    file:   symbol,
%                    line:   number)
% did  The {field} of {holder} uses the term "{term}" without a link.
% fix  Write the term as a link [[term]], or [[concept|term]] where two
%      concepts have the term, with an edge of relation_uses_concept to
%      the concept if the item has none. If the word is not meant as the
%      term, reword it.
#show unlinked_term/5.

unlinked_term(Holder, Field, Term, File, Line) :-
    term_word(Holder, Field, Term, File, Line),
    strict_field(Holder, Field),
    not designation(Holder, Term, _).


% -----------------------------------------------------------------------------
% The field of the item is strict: the brief of a concept, which is its
% definition, or a slot of a requirement that holds text.
%
% decl strict_field(holder: symbol,
%                   field:  symbol)

strict_field(Holder, "brief") :-
    has_type(Holder, "type_concept").

strict_field(Holder, Field) :-
    has_type(Holder, "type_requirement"),
    Field = ("condition"; "object"; "qualifier").


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
    acyclic_relation(Relation),
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
% A relation that reads through the proxy at an end constrains that end
% to proxies.
%
% decl unconstrained_proxy_end(relation: symbol,
%                              end:      symbol)
% did  {relation} reads through the proxy at its {end}, but does not
%      constrain that end to proxies.
% fix  Give the relation the constraint relcon_is_proxy at that end, or
%      take the end out of its reads_through list.
#show unconstrained_proxy_end/2.

unconstrained_proxy_end(Relation, "source") :-
    reads_through(Relation, "source"),
    not primary_edge(Relation, "relation_constrains_source", "relcon_is_proxy").

unconstrained_proxy_end(Relation, "target") :-
    reads_through(Relation, "target"),
    not primary_edge(Relation, "relation_constrains_target", "relcon_is_proxy").


% -----------------------------------------------------------------------------
% The concept has a match of grade in the external class.
%
% decl match(concept: symbol,
%            grade:   symbol,
%            class:   symbol)

match(Concept, "exact", Class) :-
    primary_edge(Concept, "relation_has_exact_match", Class).

match(Concept, "close", Class) :-
    primary_edge(Concept, "relation_has_close_match", Class).

match(Concept, "broad", Class) :-
    primary_edge(Concept, "relation_has_broad_match", Class).

match(Concept, "narrow", Class) :-
    primary_edge(Concept, "relation_has_narrow_match", Class).

match(Concept, "related", Class) :-
    primary_edge(Concept, "relation_has_related_match", Class).


% -----------------------------------------------------------------------------
% Two grades of match that cannot both hold between one concept and one
% class. SKOS makes an exact match disjoint from a broad, narrow or
% related match, and a related match disjoint from a broad or narrow one.
%
% decl conflicting_grades(grade: symbol,
%                         other: symbol)

conflicting_grades("exact", "broad").
conflicting_grades("exact", "narrow").
conflicting_grades("exact", "related").
conflicting_grades("related", "broad").
conflicting_grades("related", "narrow").


% -----------------------------------------------------------------------------
% No two concepts have an exact match in the same external class, since
% an exact match is transitive and would make them one concept.
%
% decl shared_exact_match(class:   symbol,
%                         concept: symbol,
%                         other:   symbol)
% did  {concept} and {other} both have an exact match in {class}, which
%      makes them one concept recorded twice.
% fix  Merge the two concepts, or grade the match of the one that
%      differs from the class as close, broad or narrow.
#show shared_exact_match/3.

shared_exact_match(Class, Concept, Other) :-
    match(Concept, "exact", Class),
    match(Other, "exact", Class),
    Concept < Other.


% -----------------------------------------------------------------------------
% A concept has no two grades of match in one external class that
% contradict each other.
%
% decl conflicting_match(concept: symbol,
%                        class:   symbol,
%                        grade:   symbol,
%                        other:   symbol)
% did  {concept} has both {grade} and {other} matches in {class}, which
%      contradict each other.
% fix  Keep the one grade that says how the concept and the class
%      differ, and unlink the other edge.
#show conflicting_match/4.

conflicting_match(Concept, Class, Grade, Other) :-
    match(Concept, Grade, Class),
    match(Concept, Other, Class),
    conflicting_grades(Grade, Other).


% -----------------------------------------------------------------------------
% The concept picks out the same things as the external class, or nearly
% so.
%
% decl equivalent_match(concept: symbol,
%                       class:   symbol)

equivalent_match(Concept, Class) :-
    match(Concept, "exact", Class).

equivalent_match(Concept, Class) :-
    match(Concept, "close", Class).


% -----------------------------------------------------------------------------
% A concept narrower than another does not match a class that the release
% places above the class the broader concept matches. Only exact and
% close matches are compared, since they say the concept and the class
% pick out the same things.
%
% decl mapping_against_hierarchy(concept:       symbol,
%                                broader:       symbol,
%                                class:         symbol,
%                                broader_class: symbol)
% did  {concept} is narrower than {broader}, but it matches {class},
%      which the release places above {broader_class}, the match of
%      {broader}.
% fix  Correct the match of one of the two concepts, or the edge of
%      relation_is_narrower_than between them. Do not change the edges
%      between external classes by hand; cctool import keeps them as
%      the release has them.
#show mapping_against_hierarchy/4.

mapping_against_hierarchy(Concept, Broader, Class, BroaderClass) :-
    reaches("relation_is_narrower_than", Concept, Broader),
    equivalent_match(Concept, Class),
    equivalent_match(Broader, BroaderClass),
    reaches("relation_is_subclass_of", BroaderClass, Class).


% -----------------------------------------------------------------------------
% The concept picks out things that all belong to the external class:
% its match there is exact, close or broad. A broad match names a class
% broader than the concept.
%
% decl within_class(concept: symbol,
%                   class:   symbol)

within_class(Concept, Class) :-
    equivalent_match(Concept, Class).

within_class(Concept, Class) :-
    match(Concept, "broad", Class).


% -----------------------------------------------------------------------------
% The release implies that the concept is narrower than the other: the
% concept is within a class that the release places below the match of
% the other, or within the very class that the other matches, more
% broadly. Only exact and close matches of the other are compared, since
% they say the other and its class pick out the same things.
%
% decl implied_narrower(concept:     symbol,
%                       other:       symbol,
%                       class:       symbol,
%                       other_class: symbol)

implied_narrower(Concept, Other, Class, OtherClass) :-
    within_class(Concept, Class),
    equivalent_match(Other, OtherClass),
    reaches("relation_is_subclass_of", Class, OtherClass),
    Concept != Other.

implied_narrower(Concept, Other, Class, Class) :-
    match(Concept, "broad", Class),
    equivalent_match(Other, Class),
    Concept != Other.


% -----------------------------------------------------------------------------
% A concept that the release implies is narrower than another is
% narrower than it here too, so that the concept register keeps the
% hierarchy that the mappings claim.
%
% decl missing_narrower(concept:       symbol,
%                       broader:       symbol,
%                       class:         symbol,
%                       broader_class: symbol)
% did  {concept} is within {class}, which the release places at or below
%      {broader_class}, the match of {broader}, but {concept} is not
%      narrower than {broader}.
% fix  Add an edge of relation_is_narrower_than from {concept} to
%      {broader}, or to a concept narrower than {broader}, or correct
%      the match of one of the two concepts.
#show missing_narrower/4.

missing_narrower(Concept, Broader, Class, BroaderClass) :-
    implied_narrower(Concept, Broader, Class, BroaderClass),
    not reaches("relation_is_narrower_than", Concept, Broader).


% -----------------------------------------------------------------------------
% An annotation is about both the concept and the external class, which
% explains how the two are related.
%
% decl explained_pair(concept: symbol,
%                     class:   symbol)

explained_pair(Concept, Class) :-
    has_type(Annotation, "type_annotation"),
    primary_edge(Annotation, "relation_is_about", Concept),
    primary_edge(Annotation, "relation_is_about", Class),
    has_type(Class, "type_external_class").


% -----------------------------------------------------------------------------
% A concept whose term is the label of an external class either matches
% that class exactly or closely, or has an annotation about both that
% says why not. The same word with another sense is a false friend, and
% a reader who knows the release will take the wrong sense.
%
% decl false_friend(concept: symbol,
%                   term:    symbol,
%                   class:   symbol)
% did  {concept} has the term "{term}", which is the label of {class},
%      but {concept} has no exact or close match in {class}.
% fix  Match {concept} in {class} if they pick out the same things.
%      Otherwise add an annotation about both that says how they
%      differ, with edges of relation_is_about to each.
#show false_friend/3.

false_friend(Concept, Term, Class) :-
    designation(Concept, Term, Rating),
    Rating != "deprecated",
    term_form(Term, Form),
    label(Class, Label),
    term_form(Label, Form),
    not equivalent_match(Concept, Class),
    not explained_pair(Concept, Class).


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
% An annotation that supports or challenges an option speaks for at
% least one concern. A premise that several concerns rest on is one
% annotation that speaks for each of them.
%
% decl argument_without_concern(id: symbol)
% did  The annotation {id} supports or challenges an option and argues
%      for no concern.
% fix  Link it with relation_speaks_for_concern to each concern it speaks for.
#show argument_without_concern/1.

argument_without_concern(Id) :-
    practical(Id),
    not primary_edge(Id, "relation_speaks_for_concern", _).


% -----------------------------------------------------------------------------
% An annotation that bears on no option speaks for no concern, since
% it is answered with evidence and not outweighed.
%
% decl concern_without_option(id:      symbol,
%                             concern: symbol)
% did  The annotation {id} speaks for {concern} and bears on no
%      option.
% fix  A fact is answered with evidence, not weighed by concern. Remove
%      the edge to the concern, or link the annotation to the option
%      it argues.
#show concern_without_option/2.

concern_without_option(Id, Concern) :-
    has_type(Id, "type_annotation"),
    not practical(Id),
    primary_edge(Id, "relation_speaks_for_concern", Concern).


% -----------------------------------------------------------------------------
% Every type names exactly one schema for its items.
%
% decl schema_count(type:    symbol,
%                   schemas: number)
% did  The type {type} names {schemas} schemas for its items, not 1.
% fix  Give the type one edge of relation_has_items_specified_by_schema.
#show schema_count/2.

schema_count(Type, Schemas) :-
    type_prefix(Type, _, _),
    Schemas = #count { Schema :
                       primary_edge(Type, "relation_has_items_specified_by_schema", Schema) },
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
    has_type(Id, "type_schema"),
    not primary_edge(_, "relation_has_items_specified_by_schema", Id),
    not primary_edge(_, "relation_is_specified_by_schema", Id),
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
    has_type(Id, "type_concept"),
    not named_by_other(Id).


% -----------------------------------------------------------------------------
% A node is named for the dataflow graph that holds it and the
% key it is filed under: the stem of the dataflow graph, with dfn in
% place of dfg, a full stop and the key.
%
% decl misnamed_node(node:     symbol,
%                    expected: symbol)
% did  The node {node} is not named for the dataflow graph that
%      holds it and its key. Its id is {expected}.
% fix  Rename the node with cctool rename to the id the check expects.
%      To rename the dataflow graph, use cctool rename, which renames
%      its nodes with it.
#show misnamed_node/2.

misnamed_node(Node, Expected) :-
    dataflow_node(Graph, Key, Node, _),
    Expected = @cat("dfn_", @substr(Graph, 4, @strlen(Graph) - 4), ".", Key),
    Node != Expected.


% -----------------------------------------------------------------------------
% Every node presents exactly one interface: it realizes one interface
% control document, whose dataflow step surface it presents.
%
% decl interface_count(node:       symbol,
%                      interfaces: number)
% did  The node {node} realizes {interfaces} interface control
%      documents, not 1.
% fix  Give the node one edge of relation_realizes to the interface control
%      document whose dataflow step surface it presents.
#show interface_count/2.

interface_count(Node, Interfaces) :-
    has_type(Node, "type_dataflow_node"),
    Interfaces = #count { Interface : node_interface(Node, Interface) },
    Interfaces != 1.


% -----------------------------------------------------------------------------
% Each end of an edge of a dataflow graph, with the kind of port
% it must name: an output at the source, and an input at the target.
%
% decl edge_end(graph: symbol,
%               end:   symbol,
%               node:  symbol,
%               port:  symbol,
%               kind:  symbol,
%               file:  symbol,
%               line:  number)

edge_end(Graph, "source", Node, Port, "output", File, Line) :-
    dataflow_edge(Graph, Node, Port, _, _, _, File, Line).

edge_end(Graph, "target", Node, Port, "input", File, Line) :-
    dataflow_edge(Graph, _, _, Node, Port, _, File, Line).


% -----------------------------------------------------------------------------
% Each end of an edge names a node of the dataflow graph that
% holds the edge.
%
% decl foreign_node(graph: symbol,
%                   end:   symbol,
%                   node:  symbol,
%                   file:  symbol,
%                   line:  number)
% did  The {end} of an edge of {graph} names {node}, which is not one
%      of its nodes.
% fix  Name a node that the dataflow graph holds, or add the node
%      to it.
#show foreign_node/5.

foreign_node(Graph, End, Node, File, Line) :-
    edge_end(Graph, End, Node, _, _, File, Line),
    not dataflow_node(Graph, _, Node, _).


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
% The node takes a value at the port from an edge of its dataflow graph
% configuration.
%
% decl fed(node: symbol,
%          port: symbol)

fed(Node, Port) :-
    dataflow_edge(_, _, _, Node, Port, _, _, _).


% -----------------------------------------------------------------------------
% An input takes its value from at most one edge. Edges are counted
% where they are written, so a second copy of one edge counts too.
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
    Edges = #count { File, Line : dataflow_edge(_, _, _, Node, Port, _, File, Line) },
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
%      interface if an invocation may run without it.
#show unfed_input/2.

unfed_input(Node, Port) :-
    dataflow_node(_, _, Node, _),
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
    dataflow_edge(_, _, SourcePort, _, TargetPort, _, File, Line),
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
    dataflow_setting(Node, Setting),
    node_interface(Node, Interface),
    not interface_port(Interface, "settings", Setting, _).


% -----------------------------------------------------------------------------
% A node gives a value for each setting that its interface neither
% states to be optional nor gives a default.
%
% decl missing_setting(node:    symbol,
%                      setting: symbol)
% did  {node} gives no value for {setting}, which its interface needs.
% fix  Give the setting a value in the settings of the node.
#show missing_setting/2.

missing_setting(Node, Setting) :-
    dataflow_node(_, _, Node, _),
    node_interface(Node, Interface),
    interface_port(Interface, "settings", Setting, Member),
    not stated(Member, "optional", "true"),
    not stated(Member, "default", _),
    not dataflow_setting(Node, Setting).


% -----------------------------------------------------------------------------
% A node runs on a process of its dataflow graph, and a process
% on a host of it.
%
% decl unplaced(graph:  symbol,
%               holder: symbol,
%               key:    symbol)
% did  {holder} in {graph} runs on {key}, which the dataflow graph
%      does not list.
% fix  Name a process or host the dataflow graph lists, or add it
%      to the process or host section.
#show unplaced/3.

unplaced(Graph, Node, Process) :-
    dataflow_node(Graph, _, Node, Process),
    Process != "",
    not os_process(Graph, Process, _).

unplaced(Graph, Process, Host) :-
    os_process(Graph, Process, Host),
    not host(Graph, Host).
