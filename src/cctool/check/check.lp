% ---
%
% id_self:                lpf_cctool.check.check
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
%                         Evaluated by pym_cctool.check.check. The facts
%                         of the base predicates and the rules of
%                         lpf_cctool.graph.derive come before this file
%                         in the program.
% edge:                   []
%
% ...

% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.unknown_prefix
% guid_self:              lpp_f086851f36d9483db655ec6c027621aa
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unknown prefix
% brief:                  |
%                         Every id begins with the prefix of a known
%                         type.
% did:                    |
%                         {id} has a prefix that no type in
%                         reg_data_item_type has.
% fix:                    |
%                         Give the item the prefix of its type. Add a
%                         type only when a real instance needs it.
% edge:                   []
%
% ...
%
% decl unknown_prefix(id:   symbol,
%                     file: symbol,
%                     line: number)
#show unknown_prefix/3.

unknown_prefix(Id, File, Line) :-
    item(Id, _, _, File, Line),
    not prefix_of(Id, _).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.bad_id
% guid_self:              lpp_28059ac53d6644d0b5187f1ae8357b6d
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Bad id
% brief:                  |
%                         Every id matches the regex_id of its type.
%                         sch_primitive checks only the form every id
%                         shares; the regex_id of each type is data,
%                         which a fixed schema cannot read.
% did:                    |
%                         {id} does not match {regex}, the regex_id of
%                         its type.
% fix:                    |
%                         Rename the item with cctool rename to an id
%                         that matches.
% edge:                   []
%
% ...
%
% decl bad_id(id:    symbol,
%             regex: symbol,
%             file:  symbol,
%             line:  number)
#show bad_id/4.

bad_id(Id, Regex, File, Line) :-
    item(Id, _, _, File, Line),
    has_type(Id, Type),
    type_prefix(Type, _, Regex),
    @match(Regex, Id) = 0.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.bad_guid
% guid_self:              lpp_6446d85a018c4f99be5f4413a24199ee
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Bad guid
% brief:                  |
%                         Every guid is the prefix of its id and 32 hex
%                         digits. sch_primitive checks the form, but not
%                         that the two prefixes agree.
% did:                    |
%                         {guid}, the guid of {id}, is not the prefix of
%                         the id and 32 hex digits.
% fix:                    |
%                         Give the guid the prefix of the id and keep
%                         its digits. Never write a guid by hand: cctool
%                         new mints one.
% edge:                   []
%
% ...
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
% ---
%
% id_self:                lpp_cctool.check.check.duplicate_prefix
% guid_self:              lpp_08deff22443a466394397f016ff481de
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Duplicate prefix
% brief:                  |
%                         No two types share a prefix.
% did:                    |
%                         {type} and {other} share the prefix {prefix}.
% fix:                    |
%                         Give one of the two types a prefix of its own.
% edge:                   []
%
% ...
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
% ---
%
% id_self:                lpp_cctool.check.check.regex_without_prefix
% guid_self:              lpp_000243e8afc44681a759445d714eed49
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Regex without prefix
% brief:                  |
%                         The regex_id of a type opens with its prefix,
%                         so that every id the regex admits has the
%                         prefix of its type. sch_regentry_type leaves
%                         this to a check, as JSON Schema cannot compare
%                         two fields.
% did:                    |
%                         The regex_id {regex} of {type} does not open
%                         with ^{prefix}_.
% fix:                    |
%                         Begin the regex_id with a caret, the prefix
%                         and an underscore.
% edge:                   []
%
% ...
%
% decl regex_without_prefix(type:   symbol,
%                           prefix: symbol,
%                           regex:  symbol)
#show regex_without_prefix/3.

regex_without_prefix(Type, Prefix, Regex) :-
    type_prefix(Type, Prefix, Regex),
    @match(@cat(@cat("\\^", Prefix), "_.*"), Regex) = 0.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.misnamed_schema
% guid_self:              lpp_c065b831a14a40d982d678392b1337fc
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Misnamed schema
% brief:                  |
%                         The $id of a schema ends with its id_self and
%                         .yaml, which is also the name of its file.
%                         sch_schema leaves this to a check, as JSON
%                         Schema cannot compare two fields.
% did:                    |
%                         The $id {uri} of {schema} does not end with
%                         /{schema}.yaml.
% fix:                    |
%                         End the $id with the id_self of the schema and
%                         .yaml.
% edge:                   []
%
% ...
%
% decl misnamed_schema(schema: symbol,
%                      uri:    symbol,
%                      file:   symbol,
%                      line:   number)
#show misnamed_schema/4.

misnamed_schema(Schema, Uri, File, Line) :-
    schema_uri(Schema, Uri, File, Line),
    @match(@cat(@cat(".*/", Schema), "\\.yaml"), Uri) = 0.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.prefix_form
% guid_self:              lpp_4ff184bafcdf411587fe9db39534cab0
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Prefix form
% brief:                  |
%                         A prefix is three lower-case letters, one
%                         whole word of the preferred term of the
%                         concept its type represents, or the first
%                         three letters of each of two or three words of
%                         that term in a row, as relcon for relation
%                         constraint. A type whose prefix is none of
%                         these states why in its prefix_exception
%                         field.
% did:                    |
%                         The prefix {prefix} of {type} is not three
%                         letters, a word of its preferred term, or the
%                         first three letters of words of it in a row.
% fix:                    |
%                         Choose three letters from the preferred term,
%                         one whole word of it, or the first three
%                         letters of two or three of its words in a row,
%                         or say in prefix_exception why the prefix must
%                         stay.
% edge:                   []
%
% ...
%
% decl prefix_form(type:   symbol,
%                  prefix: symbol)
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
% ---
%
% id_self:                lpp_cctool.check.check.prefix_near
% guid_self:              lpp_73fe14c5106d48dfa1c62b484348c6cb
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Prefix near
% brief:                  |
%                         Two prefixes of the same length differ in more
%                         than one letter, unless their types declare
%                         one prefix family, as a container and its
%                         members do.
% did:                    |
%                         The prefix {prefix} of {type} differs by one
%                         letter from {near}, the prefix of {other}.
% fix:                    |
%                         Choose a prefix further from the other, or
%                         give both types the same prefix_family if they
%                         belong together.
% edge:                   []
%
% ...
%
% decl prefix_near(type:   symbol,
%                  prefix: symbol,
%                  other:  symbol,
%                  near:   symbol)
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
% ---
%
% id_self:                lpp_cctool.check.check.duplicate_id
% guid_self:              lpp_7b3020e92a7445b7859d1bbe458302a0
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Duplicate id
% brief:                  |
%                         No id names two items.
% did:                    |
%                         The id {id} names two items, with the guids
%                         {guid} and {other}.
% fix:                    |
%                         Rename one of the two with cctool rename. If
%                         one is a copy of the other, remove the copy.
% edge:                   []
%
% ...
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
% ---
%
% id_self:                lpp_cctool.check.check.duplicate_guid
% guid_self:              lpp_be8622d1eae54913b35003af48ac1876
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Duplicate guid
% brief:                  |
%                         No guid identifies two items.
% did:                    |
%                         The guid {guid} identifies two items, {id} and
%                         {other}.
% fix:                    |
%                         A copy keeps the guid of what it copies. Make
%                         the new item with cctool new, which mints a
%                         guid, and remove the copy.
% edge:                   []
%
% ...
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
% ---
%
% id_self:                lpp_cctool.check.check.repeated_item
% guid_self:              lpp_00e896da95f94ae8a68438b26b825c18
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Repeated item
% brief:                  |
%                         No item is written twice. A copy carries the
%                         id and the guid of the item it copies, so
%                         neither duplicate_id nor duplicate_guid finds
%                         it. A shadow carries them too, so it is no
%                         copy of the item it stands for.
% did:                    |
%                         {id} is written here and again elsewhere.
% fix:                    |
%                         Keep one copy of the item and remove the
%                         others.
% edge:                   []
%
% ...
%
% decl repeated_item(id:   symbol,
%                    file: symbol,
%                    line: number)
#show repeated_item/3.

repeated_item(Id, File, Line) :-
    item(Id, Guid, _, File, Line),
    item(Id, Guid, _, Other, Where),
    (File, Line) != (Other, Where),
    not shadow(Id, File),
    not shadow(Id, Other).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.misplaced_module
% guid_self:              lpp_9566474dc0f94d46b1ad639f6a48b186
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Misplaced module
% brief:                  |
%                         A python module, python package or logic
%                         program file item is named for the module,
%                         package or file that holds it.
% did:                    |
%                         {id} is not named for what holds it. Its id is
%                         {expected}.
% fix:                    |
%                         Rename the item with cctool rename to the id
%                         the check expects.
% edge:                   []
%
% ...
%
% decl misplaced_module(id:       symbol,
%                       expected: symbol)
#show misplaced_module/2.

misplaced_module(Id, Expected) :-
    module_name(Id, Expected),
    Id != Expected.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.misplaced_document
% guid_self:              lpp_444ba3b8e3e84d9cb3dbbbbc0abac285
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Misplaced document
% brief:                  |
%                         A YAML document under a _data directory is in
%                         the folder named for its type, less the type_,
%                         in a file named for its id. A document that
%                         belongs to a decision is in the folder of the
%                         decision instead, so that everything argued
%                         about one decision is kept together. A shadow
%                         is in the file of shadows of its release.
% did:                    |
%                         {id} is in {file}, not in {expected}.
% fix:                    |
%                         Move the file to where the check expects it.
%                         Everything argued about a decision goes in the
%                         folder of the decision.
% edge:                   []
%
% ...
%
% decl misplaced_document(id:       symbol,
%                         file:     symbol,
%                         expected: symbol)
#show misplaced_document/3.

misplaced_document(Id, File, Expected) :-
    item(Id, _, "", File, _),
    @match("(.*/)?_data/.*\\.yaml", File) = 1,
    not shadow(Id, File),
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
% ---
%
% id_self:                lpp_cctool.check.check.misplaced_register_entry
% guid_self:              lpp_c9ea9f2273a04bdf99c6b288824f5f45
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Misplaced register entry
% brief:                  |
%                         A register holds only register entries of a
%                         type whose items it holds.
% did:                    |
%                         {register} holds {id}, an entry of {type},
%                         which is not a type whose items it holds.
% fix:                    |
%                         Move the entry to the register of its type, or
%                         correct its type.
% edge:                   []
%
% ...
%
% decl misplaced_register_entry(register: symbol,
%                               id:       symbol,
%                               type:     symbol)
#show misplaced_register_entry/3.

misplaced_register_entry(Register, Id, Type) :-
    register_entry_key(Register, _, Id),
    has_type(Id, Type),
    not primary_edge(Type, "relation_has_items_held_in_register", Register).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.unrecorded_module
% guid_self:              lpp_1f20ba7d65fe41a483d60dd2775d4e4d
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unrecorded module
% brief:                  |
%                         Every python module and logic program file
%                         under src holds an item.
% did:                    |
%                         {file} holds no item.
% fix:                    |
%                         Give the file its item with cctool header
%                         PATH.
% edge:                   []
%
% ...
%
% decl unrecorded_module(file: symbol)
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
    type_prefix("type_interface_control_document", Prefix, _),
    type_prefix("type_interface_member", Member, _),
    Start = @strlen(Prefix) + 1,
    Stem = @cat(Member, "_", @substr(Holder, Start, @strlen(Holder) - Start)).

member_stem(Holder, Holder) :-
    has_type(Holder, "type_interface_member").

% ---
%
% id_self:                lpp_cctool.check.check.misnamed_member
% guid_self:              lpp_b297213f22444811990f6c4d3beb1ea4
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Misnamed member
% brief:                  |
%                         The id of an interface member is the stem of
%                         what it sits in, a full stop and a name of its
%                         own.
% did:                    |
%                         The id of {id} is not the stem of {holder}, a
%                         full stop and a name.
% fix:                    |
%                         Rename the member with cctool rename to the
%                         stem of what it sits in, a full stop, and its
%                         own name. To rename the interface control
%                         document, use cctool rename, which renames its
%                         members with it.
% edge:                   []
%
% ...
%
% decl misnamed_member(id:     symbol,
%                      holder: symbol)
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

% ---
%
% id_self:                lpp_cctool.check.check.parameter_mismatch
% guid_self:              lpp_15ca3aada1294e719d84ce3629be934f
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Parameter mismatch
% brief:                  |
%                         A python function that realizes an interface
%                         member takes the parameters the member states,
%                         by name and in order.
% did:                    |
%                         At position {position}, {member} states the
%                         parameter {stated}, and {function} takes
%                         {actual}.
% fix:                    |
%                         Make the member and the code agree: change the
%                         member if the interface has changed, or the
%                         code if it has drifted. An empty value means
%                         no parameter is there.
% edge:                   []
%
% ...
%
% decl parameter_mismatch(member:   symbol,
%                         function: symbol,
%                         position: number,
%                         stated:   symbol,
%                         actual:   symbol)
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
% ---
%
% id_self:                lpp_cctool.check.check.signature_mismatch
% guid_self:              lpp_abe1c817540a4d989d2607d7bb880298
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Signature mismatch
% brief:                  |
%                         What a member states of the signature it
%                         restates is what the python function that
%                         realizes it says: the type and default of each
%                         parameter as the code writes them, whether it
%                         is optional or variadic, and the type the
%                         function returns. member is the parameter
%                         member, or the function member for returns. A
%                         part the member does not state is not
%                         compared, and actual is empty where the code
%                         does not say.
% did:                    |
%                         {member} states {stated} for the {part}, and
%                         {function} says {actual}.
% fix:                    |
%                         Make the member and the code agree: change the
%                         member if the interface has changed, or the
%                         code if it has drifted. An empty value means
%                         that side does not say.
% edge:                   []
%
% ...
%
% decl signature_mismatch(member:   symbol,
%                         function: symbol,
%                         part:     symbol,
%                         stated:   symbol,
%                         actual:   symbol)
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
% A command line surface states the commands of a program and their
% parameters, and click describes the commands and parameters of cctool
% as it runs. A program is held to click wherever a surface states it.
% The program itself is stated by its surface, so its own parameters
% sit under the empty command.
%
% decl command_line_program(program: symbol)

command_line_program(Program) :-
    command_member(_, Program, _, _).

% decl command_holder(member:  symbol,
%                     program: symbol,
%                     command: symbol)

command_holder(Member, Program, Command) :-
    command_member(Member, Program, Command, "").

command_holder("", Program, "") :-
    command_line_program(Program).

% ---
%
% id_self:                lpp_cctool.check.check.command_mismatch
% guid_self:              lpp_0ffa1dc6656541d89fe03a913717f3f0
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Command mismatch
% brief:                  |
%                         What a command line surface states of a
%                         program is what click describes of it: each
%                         command, each parameter of each command, and
%                         the kind, type, default and position of each
%                         parameter, and whether it is optional,
%                         variadic or a flag. member is the member that
%                         states the part, or the command that holds a
%                         parameter no member states, and is empty for a
%                         command no member states. A part the member
%                         does not state is not compared.
% did:                    |
%                         {member} states {stated} for the {part} of
%                         {command} of {program}, and click describes
%                         {actual}.
% fix:                    |
%                         Make the member and the code agree: change the
%                         member if the command line has changed, or the
%                         code if it has drifted. An empty value means
%                         that side does not say, so a command or a
%                         parameter that no member states needs one, in
%                         a command line surface of the program.
% edge:                   []
%
% ...
%
% decl command_mismatch(member:  symbol,
%                       program: symbol,
%                       command: symbol,
%                       part:    symbol,
%                       stated:  symbol,
%                       actual:  symbol)
#show command_mismatch/6.

command_mismatch(Member, Program, Command, "command", Command, "") :-
    command_member(Member, Program, Command, ""),
    not click_command(Program, Command).

command_mismatch("", Program, Command, "command", "", Command) :-
    click_command(Program, Command),
    Command != "",
    command_line_program(Program),
    not command_member(_, Program, Command, "").

command_mismatch(Member, Program, Command, "parameter", Name, "") :-
    command_member(Member, Program, Command, Name),
    Name != "",
    click_command(Program, Command),
    not click_parameter(Program, Command, Name, "kind", _).

command_mismatch(Member, Program, Command, "parameter", "", Name) :-
    click_parameter(Program, Command, Name, "kind", _),
    command_holder(Member, Program, Command),
    not command_member(_, Program, Command, Name).

command_mismatch(Member, Program, Command, Part, Stated, Actual) :-
    command_member(Member, Program, Command, Name),
    Name != "",
    stated(Member, Part, Stated),
    click_parameter(Program, Command, Name, Part, Actual),
    Stated != Actual.


% -----------------------------------------------------------------------------
% An interface control document that states any check declares the
% checks of cctool, and is held to all of them.
%
% decl check_interface(interface: symbol)

check_interface(Interface) :-
    check_member(_, Interface, _, _).

% ---
%
% id_self:                lpp_cctool.check.check.severity_mismatch
% guid_self:              lpp_fd3185c58deb4ff6a50f0a92ea4185c0
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Severity mismatch
% brief:                  |
%                         Each check that cctool runs is stated in each
%                         interface control document that states any
%                         check, with the severity its rows have:
%                         failure for a check of check.lp, schema
%                         validation and layout, and advice for a check
%                         of advise.lp. member is the member that states
%                         the check, or the document where no member
%                         does.
% did:                    |
%                         {member} states {stated} as the severity of
%                         {check} in {interface}, and cctool reports
%                         {actual}.
% fix:                    |
%                         Make the member and the code agree: if the
%                         check has moved between check.lp and
%                         advise.lp, change the severity of its member,
%                         since a move from advice to failure is a
%                         change to the interface. An empty value means
%                         that side does not say, so a new check needs a
%                         member, and the member of a check that is gone
%                         goes with it.
% edge:                   []
%
% ...
%
% decl severity_mismatch(member:    symbol,
%                        interface: symbol,
%                        check:     symbol,
%                        stated:    symbol,
%                        actual:    symbol)
#show severity_mismatch/5.

severity_mismatch(Member, Interface, Check, Stated, Actual) :-
    check_member(Member, Interface, Check, Stated),
    check_severity(Check, Actual),
    Stated != Actual.

severity_mismatch(Member, Interface, Check, Stated, "") :-
    check_member(Member, Interface, Check, Stated),
    not check_severity(Check, _).

severity_mismatch(Interface, Interface, Check, "", Actual) :-
    check_severity(Check, Actual),
    check_interface(Interface),
    not check_member(_, Interface, Check, _).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.key_mismatch
% guid_self:              lpp_256af75b8dd243e2922d6ff74e622e50
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Key mismatch
% brief:                  |
%                         The key of a register entry is its id.
% did:                    |
%                         In {register}, the key {key} holds the entry
%                         {id}.
% fix:                    |
%                         Make the key the id of the entry. cctool
%                         rename changes both.
% edge:                   []
%
% ...
%
% decl key_mismatch(register: symbol,
%                   key:      symbol,
%                   id:       symbol)
#show key_mismatch/3.

key_mismatch(Register, Key, Id) :-
    register_entry_key(Register, Key, Id),
    Key != Id.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.dangling_reference
% guid_self:              lpp_e68311b68aca490da396041d5142ed6c
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Dangling reference
% brief:                  |
%                         Every reference names an item that exists, by
%                         its id or, where the id names nothing, by its
%                         guid. A protective mark that names nothing
%                         here is not a failure: it may be held in a
%                         partner's register, and advise.lp reports it.
% did:                    |
%                         {holder} names {id} in its {field} field, and
%                         no item has that id or guid.
% fix:                    |
%                         Correct the id, or add the item it names. Do
%                         not remove the reference only to quiet the
%                         check.
% edge:                   []
%
% ...
%
% decl dangling_reference(holder: symbol,
%                         field:  symbol,
%                         id:     symbol,
%                         file:   symbol,
%                         line:   number)
#show dangling_reference/5.

dangling_reference(Holder, Field, Id, File, Line) :-
    reference(Holder, Field, Id, Guid, File, Line),
    not item(Id, _, _, _, _),
    not item(_, Guid, _, _, _),
    not alias(_, Id),
    Field != "mark".


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.guid_mismatch
% guid_self:              lpp_d260e58bd2f6440fa12b696d10263498
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Guid mismatch
% brief:                  |
%                         Every reference carries the guid of the item
%                         it names.
% did:                    |
%                         {holder} names {id} in its {field} field with
%                         the guid {guid}, which is not the guid of
%                         {id}.
% fix:                    |
%                         Copy the guid of the item named, or write the
%                         edge with cctool link, which copies it.
% edge:                   []
%
% ...
%
% decl guid_mismatch(holder: symbol,
%                    field:  symbol,
%                    id:     symbol,
%                    guid:   symbol,
%                    file:   symbol,
%                    line:   number)
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
% ---
%
% id_self:                lpp_cctool.check.check.constraint_violation
% guid_self:              lpp_451eef8476dd49e6b4cea9fcf91fc42e
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Constraint violation
% brief:                  |
%                         Each end of an edge satisfies every constraint
%                         its relation names for that end. An end that
%                         names none is open to any item.
% did:                    |
%                         The edge {source} {relation} {target} breaks
%                         {constraint} at its {end} end.
% fix:                    |
%                         Point the edge at an item of a type the
%                         relation admits, or use the relation that
%                         fits. Its entry in reg_relation.yaml names its
%                         constraints.
% edge:                   []
%
% ...
%
% decl constraint_violation(source:      symbol,
%                            relation:    symbol,
%                            target:      symbol,
%                            end:         symbol,
%                            constraint: symbol)
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
% ---
%
% id_self:                lpp_cctool.check.check.missing_about
% guid_self:              lpp_d51671bbf60c436080c82ff17055cc80
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Missing about
% brief:                  |
%                         Every annotation and every decision is about
%                         something.
% did:                    |
%                         {id} is about nothing: it has no edge of
%                         relation_is_about.
% fix:                    |
%                         Link it to its subject with cctool link ID
%                         relation_is_about TARGET.
% edge:                   []
%
% ...
%
% decl missing_about(id: symbol)
#show missing_about/1.

missing_about(Id) :-
    has_type(Id, "type_annotation"),
    not primary_edge(Id, "relation_is_about", _).

missing_about(Id) :-
    has_type(Id, "type_decision"),
    not primary_edge(Id, "relation_is_about", _).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.option_count
% guid_self:              lpp_da24bf2321cc4c4a8eb42f3879bd9662
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Option count
% brief:                  |
%                         Every option is an option for exactly one
%                         decision. The options for a decision are its
%                         alternatives.
% did:                    |
%                         The option {option} is an option for
%                         {decisions} decisions, not 1.
% fix:                    |
%                         Give the option one edge of
%                         relation_is_option_for, to its decision.
% edge:                   []
%
% ...
%
% decl option_count(option:    symbol,
%                   decisions: number)
#show option_count/2.

option_count(Option, Decisions) :-
    has_type(Option, "type_option"),
    Decisions = #count { Decision : primary_edge(Option, "relation_is_option_for", Decision) },
    Decisions != 1.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.no_option_in_ruling
% guid_self:              lpp_f8d942840c1b420abd10780f2ff263b9
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  No option in ruling
% brief:                  |
%                         Every ruling upholds or rejects at least one
%                         option.
% did:                    |
%                         The ruling {id} neither upholds nor rejects an
%                         option.
% fix:                    |
%                         Link it with relation_upholds or
%                         relation_rejects to each option it settles.
% edge:                   []
%
% ...
%
% decl no_option_in_ruling(id: symbol)
#show no_option_in_ruling/1.

no_option_in_ruling(Id) :-
    has_type(Id, "type_ruling"),
    not primary_edge(Id, "relation_upholds", _),
    not primary_edge(Id, "relation_rejects", _).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.decisions_mixed_in_ruling
% guid_self:              lpp_df9560e47ce34a9d83f014130d1ea14f
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Decisions mixed in ruling
% brief:                  |
%                         A ruling settles the options of one decision.
% did:                    |
%                         The ruling {ruling} settles options of both
%                         {decision} and {other}.
% fix:                    |
%                         Settle each decision with a ruling of its own.
% edge:                   []
%
% ...
%
% decl decisions_mixed_in_ruling(ruling:   symbol,
%                                decision: symbol,
%                                other:    symbol)
#show decisions_mixed_in_ruling/3.

decisions_mixed_in_ruling(Ruling, Decision, Other) :-
    has_type(Ruling, "type_ruling"),
    decision_of(Ruling, Decision),
    decision_of(Ruling, Other),
    Decision < Other.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.supports_and_challenges
% guid_self:              lpp_62c8acfc745744ca9e18fb30599a215b
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Supports and challenges
% brief:                  |
%                         An annotation either supports or challenges a
%                         target, never both. One that qualifies another
%                         challenges it.
% did:                    |
%                         The annotation {annotation} both supports and
%                         challenges {target}.
% fix:                    |
%                         Keep the edge the annotation argues, or split
%                         it into two annotations that each argue one
%                         way.
% edge:                   []
%
% ...
%
% decl supports_and_challenges(annotation: symbol,
%                              target:     symbol)
#show supports_and_challenges/2.

supports_and_challenges(Annotation, Target) :-
    primary_edge(Annotation, "relation_supports", Target),
    primary_edge(Annotation, "relation_challenges", Target).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.upholds_and_rejects
% guid_self:              lpp_2d3411771cad4baebc7f205bdcea81df
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Upholds and rejects
% brief:                  |
%                         A ruling either upholds or rejects an option,
%                         never both.
% did:                    |
%                         The ruling {ruling} both upholds and rejects
%                         {option}.
% fix:                    |
%                         Keep the one edge the ruling means.
% edge:                   []
%
% ...
%
% decl upholds_and_rejects(ruling: symbol,
%                          option: symbol)
#show upholds_and_rejects/2.

upholds_and_rejects(Ruling, Option) :-
    primary_edge(Ruling, "relation_upholds", Option),
    primary_edge(Ruling, "relation_rejects", Option).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.decision_about_non_component
% guid_self:              lpp_67847fa727b24813be608d3a06c11b67
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Decision about non component
% brief:                  |
%                         A decision is about logical components, since
%                         their drivers say which concerns must be
%                         argued before an option of the decision is
%                         settled. A decision about anything else would
%                         escape that check.
% did:                    |
%                         The decision {decision} is about {target}, of
%                         {type}, which is not a logical component.
% fix:                    |
%                         Make the decision about the logical component
%                         whose design it decides.
% edge:                   []
%
% ...
%
% decl decision_about_non_component(decision: symbol,
%                                   target:   symbol,
%                                   type:     symbol)
#show decision_about_non_component/3.

decision_about_non_component(Decision, Target, Type) :-
    has_type(Decision, "type_decision"),
    primary_edge(Decision, "relation_is_about", Target),
    has_type(Target, Type),
    Type != "type_logical_component".


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.argument_across_decisions
% guid_self:              lpp_9b72fa0d24eb46239d1a6df2404a0288
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Argument across decisions
% brief:                  |
%                         An annotation argues within its decision: what
%                         it supports or challenges belongs to the same
%                         decision as it does.
% did:                    |
%                         The annotation {annotation} of {decision}
%                         argues with {target}, of {other}.
% fix:                    |
%                         Argue within one decision: point the edge at
%                         an item of the same decision, or move the
%                         annotation to the decision it argues.
% edge:                   []
%
% ...
%
% decl argument_across_decisions(annotation: symbol,
%                                decision:   symbol,
%                                target:     symbol,
%                                other:      symbol)
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
% ---
%
% id_self:                lpp_cctool.check.check.supersession_across_types
% guid_self:              lpp_69c0418379a343358139268d214e8bd2
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Supersession across types
% brief:                  |
%                         An item supersedes only an item of its own
%                         type: an option another option, and an
%                         interface control document another.
% did:                    |
%                         {source} supersedes {target}, an item of
%                         another type.
% fix:                    |
%                         Supersede only an item of the same type.
% edge:                   []
%
% ...
%
% decl supersession_across_types(source: symbol,
%                                target: symbol)
#show supersession_across_types/2.

supersession_across_types(Source, Target) :-
    primary_edge(Source, "relation_supersedes", Target),
    has_type(Source, Type),
    not has_type(Target, Type).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.competing_rulings
% guid_self:              lpp_77038072a00c4038b3b661291a8694aa
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Competing rulings
% brief:                  |
%                         A decision has at most one ruling. A change of
%                         ruling edits it in place, and the history of
%                         the ruling is the history of its file.
% did:                    |
%                         The decision {decision} has two rulings,
%                         {ruling} and {other}.
% fix:                    |
%                         Keep one ruling and edit it in place when the
%                         ruling changes. Git keeps the history of the
%                         ruling.
% edge:                   []
%
% ...
%
% decl competing_rulings(decision: symbol,
%                        ruling:   symbol,
%                        other:    symbol)
#show competing_rulings/3.

competing_rulings(Decision, Ruling, Other) :-
    has_type(Ruling, "type_ruling"),
    has_type(Other, "type_ruling"),
    decision_of(Ruling, Decision),
    decision_of(Other, Decision),
    Ruling < Other.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.option_taken_but_not_upheld
% guid_self:              lpp_aaa9b2cbb49744a2afcc04eba3538ddb
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Option taken but not upheld
% brief:                  |
%                         A dataflow variant takes only an option that a
%                         ruling upholds.
% did:                    |
%                         {variant} takes {option}, which no ruling
%                         upholds.
% fix:                    |
%                         Take an upheld option of the decision, or
%                         remove the edge until the decision is ruled.
% edge:                   []
%
% ...
%
% decl option_taken_but_not_upheld(variant: symbol,
%                                  option:  symbol)
#show option_taken_but_not_upheld/2.

option_taken_but_not_upheld(Variant, Option) :-
    primary_edge(Variant, "relation_takes_option", Option),
    not primary_edge(_, "relation_upholds", Option).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.two_options_taken
% guid_self:              lpp_58b2ab16b31b46be86ce6d809e217e96
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Two options taken
% brief:                  |
%                         A dataflow variant takes at most one option of
%                         each decision.
% did:                    |
%                         {variant} takes both {option} and {other} of
%                         {decision}.
% fix:                    |
%                         Keep the edge to the option the dataflow
%                         variant takes.
% edge:                   []
%
% ...
%
% decl two_options_taken(variant:  symbol,
%                        decision: symbol,
%                        option:   symbol,
%                        other:    symbol)
#show two_options_taken/4.

two_options_taken(Variant, Decision, Option, Other) :-
    primary_edge(Variant, "relation_takes_option", Option),
    primary_edge(Variant, "relation_takes_option", Other),
    decision_of(Option, Decision),
    decision_of(Other, Decision),
    Option < Other.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.unreadable_file
% guid_self:              lpp_4ea0e7c691ca44c2aa6835f18e809982
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unreadable file
% brief:                  |
%                         Every file that ought to hold a YAML document
%                         can be read: a YAML file under _data, the
%                         module docstring of a python module, or a
%                         comment header. One that cannot hides its
%                         items from every other check.
% did:                    |
%                         {file} cannot be read at line {line}:
%                         {message}
% fix:                    |
%                         Correct the file so it parses. Until it does,
%                         no other check sees its items.
% edge:                   []
%
% ...
%
% decl unreadable_file(file:    symbol,
%                      line:    number,
%                      message: symbol)
#show unreadable_file/3.

unreadable_file(File, Line, Message) :-
    unreadable(File, Line, Message).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.dangling_mention
% guid_self:              lpp_80527bdf1fa54880b66abbf5c6e23e4c
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Dangling mention
% brief:                  |
%                         Every id that a text mentions, if it has the
%                         prefix of a known type, names an item, or an
%                         old id of one. A guid may be mentioned too.
% did:                    |
%                         The text of {holder} mentions {id}, and no
%                         item has that id.
% fix:                    |
%                         Correct the id, add the item, or say it in
%                         prose without the prefix.
% edge:                   []
%
% ...
%
% decl dangling_mention(holder: symbol,
%                       id:     symbol,
%                       file:   symbol,
%                       line:   number)
#show dangling_mention/4.

dangling_mention(Holder, Id, File, Line) :-
    mention(Holder, Id, File, Line),
    id_prefix(Id, Prefix),
    type_prefix(_, Prefix, _),
    not item(Id, _, _, _, _),
    not item(_, Id, _, _, _),
    not alias(_, Id).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.word_to_replace
% guid_self:              lpp_ceb4a72ac0574e65a25f32c2e66bc749
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Word to replace
% brief:                  |
%                         A text uses none of the words that a writing
%                         style rule asks to replace, outside double
%                         quotes and the breaks example of a rule.
% did:                    |
%                         The text of {holder} uses {word}, which {rule}
%                         asks to write as {preferred}.
% fix:                    |
%                         Write the preferred word. A quotation keeps
%                         its own spelling inside double quotes.
% edge:                   []
%
% ...
%
% decl word_to_replace(holder:    symbol,
%                      word:      symbol,
%                      preferred: symbol,
%                      rule:      symbol,
%                      file:      symbol,
%                      line:      number)
#show word_to_replace/6.

word_to_replace(Holder, Word, Preferred, Rule, File, Line) :-
    avoided_word(Holder, Word, File, Line),
    word_replacement(Rule, Word, Preferred).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.unresolved_term
% guid_self:              lpp_ff2545b97815451bb143615dcc113cab
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unresolved term
% brief:                  |
%                         A wiki link "[[term]]" finds its concept among
%                         the concepts that the item holding it uses, or
%                         that an item holding that item uses: the one
%                         with a preferred or admitted term of the same
%                         form.
% did:                    |
%                         {holder} links "[[{term}]]", and no concept it
%                         uses has that term.
% fix:                    |
%                         Add an edge of relation_uses_concept from the
%                         item to the concept meant, or write a term
%                         that concept gives.
% edge:                   []
%
% ...
%
% decl unresolved_term(holder: symbol,
%                      term:   symbol,
%                      file:   symbol,
%                      line:   number)
#show unresolved_term/4.

unresolved_term(Holder, Term, File, Line) :-
    term_link(Holder, Term, "", File, Line),
    not term_has_sense(Holder, Term).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.ambiguous_term
% guid_self:              lpp_59460c8c8bfa47039fe4c33e747f0935
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Ambiguous term
% brief:                  |
%                         A wiki link "[[term]]" finds one concept.
%                         Where the item uses two concepts with that
%                         term, each link to either is written
%                         "[[concept|term]]".
% did:                    |
%                         {holder} links "[[{term}]]", and {concepts}
%                         concepts it uses have that term.
% fix:                    |
%                         Name the concept meant in each such link, as
%                         "[[concept|term]]".
% edge:                   []
%
% ...
%
% decl ambiguous_term(holder:   symbol,
%                     term:     symbol,
%                     concepts: number,
%                     file:     symbol,
%                     line:     number)
#show ambiguous_term/5.

ambiguous_term(Holder, Term, Concepts, File, Line) :-
    term_link(Holder, Term, "", File, Line),
    Concepts = #count { Concept : term_sense(Holder, Term, Concept) },
    Concepts > 1.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.unused_linked_concept
% guid_self:              lpp_e35554efb5fc4671b6f9c219380abb1c
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unused linked concept
% brief:                  |
%                         A wiki link "[[concept|term]]" names a concept
%                         that the item uses.
% did:                    |
%                         {holder} links to {concept}, which it does not
%                         use.
% fix:                    |
%                         Add an edge of relation_uses_concept from the
%                         item to the concept, or link to a concept the
%                         item uses.
% edge:                   []
%
% ...
%
% decl unused_linked_concept(holder:  symbol,
%                            concept: symbol,
%                            file:    symbol,
%                            line:    number)
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
% A wiki link "[[term]]" in the item could mean the concept: the item uses it,
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
% The wiki link "[[term]]" in the item finds at least one concept.
%
% decl term_has_sense(holder: symbol,
%                     term:   symbol)

term_has_sense(Holder, Term) :-
    term_sense(Holder, Term, _).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.term_rated_twice
% guid_self:              lpp_3a5635df406148fbbba2dca49efb010c
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Term rated twice
% brief:                  |
%                         A concept rates each of its terms once: a term
%                         is preferred, admitted or deprecated, never
%                         two of these, as ISO 1087 rates a designation.
% did:                    |
%                         {concept} rates the term "{term}" both
%                         {rating} and {other}.
% fix:                    |
%                         Keep the one rating the concept means, and
%                         take the term out of the other list.
%
% edge:
%
%   - id_relation:        relation_cites
%     guid_relation:      relation_51554b1012884a358e38a299ba3632e0
%     id_target:          extdoc_iso_1087_2019
%     guid_target:        extdoc_7963394b2f8f461183b91a27f8ca526c
%
% ...
%
% decl term_rated_twice(concept: symbol,
%                       term:    symbol,
%                       rating:  symbol,
%                       other:   symbol)
#show term_rated_twice/4.

term_rated_twice(Concept, Term, Rating, Other) :-
    designation(Concept, Term, Rating),
    designation(Concept, Twin, Other),
    Rating < Other,
    term_form(Term, Form),
    term_form(Twin, Form).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.unlinked_term
% guid_self:              lpp_1235d4920b5445d998c478be3ce13c48
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unlinked term
% brief:                  |
%                         A strict field links every term it uses. The
%                         definition of a concept and the slots of a
%                         requirement statement are short, and they are
%                         where a term is most often meant in its
%                         registered sense, so a term in them is written
%                         as a link, which the link checks then hold to
%                         its concept. A concept's own terms are exempt
%                         from its definition.
% did:                    |
%                         The {field} of {holder} uses the term "{term}"
%                         without a link.
% fix:                    |
%                         Write the term as a wiki link "[[term]]", or
%                         "[[concept|term]]" where two concepts have the
%                         term, with an edge of relation_uses_concept to
%                         the concept if the item has none. If the word
%                         is not meant as the term, reword it.
% edge:                   []
%
% ...
%
% decl unlinked_term(holder: symbol,
%                    field:  symbol,
%                    term:   symbol,
%                    file:   symbol,
%                    line:   number)
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
% ---
%
% id_self:                lpp_cctool.check.check.alias_in_use
% guid_self:              lpp_293e4c88df7c4fbdae455631eaa304d6
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Alias in use
% brief:                  |
%                         An alias is an old id, so no item has it.
% did:                    |
%                         {alias}, an alias of {id}, is the id of an
%                         item.
% fix:                    |
%                         An alias is an old id. Take it out of the
%                         alias list, or rename the item that has it.
% edge:                   []
%
% ...
%
% decl alias_in_use(alias: symbol,
%                   id:    symbol)
#show alias_in_use/2.

alias_in_use(Alias, Id) :-
    alias(Id, Alias),
    item(Alias, _, _, _, _).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.outdated_reference
% guid_self:              lpp_f10ea6d2cad6457db523d453bf699a3d
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Outdated reference
% brief:                  |
%                         A reference names an item by its current id,
%                         not an old one. An old id is found through an
%                         alias or, where the id names nothing, through
%                         the guid, which decides.
% did:                    |
%                         {holder} names {alias} in its {field} field,
%                         an old id of {id}.
% fix:                    |
%                         Name the item by its current id.
% edge:                   []
%
% ...
%
% decl outdated_reference(holder: symbol,
%                         field:  symbol,
%                         alias:  symbol,
%                         id:     symbol,
%                         file:   symbol,
%                         line:   number)
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
% ---
%
% id_self:                lpp_cctool.check.check.outdated_mention
% guid_self:              lpp_3a342787b9dc447ab39cf73159e8d79b
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Outdated mention
% brief:                  |
%                         A text names an item by its current id, except
%                         in the item itself, where it may record what
%                         the item was once called.
% did:                    |
%                         The text of {holder} mentions {alias}, an old
%                         id of {id}.
% fix:                    |
%                         Mention the item by its current id.
% edge:                   []
%
% ...
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
    acyclic_relation(Relation),
    primary_edge(Source, Relation, Target).

reaches(Relation, Source, Target) :-
    reaches(Relation, Source, Middle),
    primary_edge(Middle, Relation, Target).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.cycle
% guid_self:              lpp_6905aebec55c45e3946fb0da51e2cd35
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Cycle
% brief:                  |
%                         No chain of edges of an acyclic relation leads
%                         from an item back to itself.
% did:                    |
%                         A chain of edges of {relation} leads from {id}
%                         back to itself.
% fix:                    |
%                         The relation is acyclic. Find the edge of the
%                         chain that is wrong, and remove or correct it.
% edge:                   []
%
% ...
%
% decl cycle(relation: symbol,
%            id:       symbol)
#show cycle/2.

cycle(Relation, Id) :-
    reaches(Relation, Id, Id).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.unconstrained_proxy_end
% guid_self:              lpp_0bf47cef93ff47ecae227f4c6bcf8f1d
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unconstrained proxy end
% brief:                  |
%                         A relation that reads through the proxy at an
%                         end constrains that end to proxies.
% did:                    |
%                         {relation} reads through the proxy at its
%                         {end}, but does not constrain that end to
%                         proxies.
% fix:                    |
%                         Give the relation the constraint
%                         relcon_is_proxy at that end, or take the end
%                         out of its reads_through list.
% edge:                   []
%
% ...
%
% decl unconstrained_proxy_end(relation: symbol,
%                              end:      symbol)
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
% ---
%
% id_self:                lpp_cctool.check.check.shared_exact_match
% guid_self:              lpp_e05162e112d846eba046ac251374a012
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Shared exact match
% brief:                  |
%                         No two concepts have an exact match in the
%                         same external class, since an exact match is
%                         transitive and would make them one concept.
% did:                    |
%                         {concept} and {other} both have an exact match
%                         in {class}, which makes them one concept
%                         recorded twice.
% fix:                    |
%                         Merge the two concepts, or grade the match of
%                         the one that differs from the class as close,
%                         broad or narrow.
% edge:                   []
%
% ...
%
% decl shared_exact_match(class:   symbol,
%                         concept: symbol,
%                         other:   symbol)
#show shared_exact_match/3.

shared_exact_match(Class, Concept, Other) :-
    match(Concept, "exact", Class),
    match(Other, "exact", Class),
    Concept < Other.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.conflicting_match
% guid_self:              lpp_42d81c622b114dcda50349f92d2d2dbd
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Conflicting match
% brief:                  |
%                         A concept has no two grades of match in one
%                         external class that contradict each other.
% did:                    |
%                         {concept} has both {grade} and {other} matches
%                         in {class}, which contradict each other.
% fix:                    |
%                         Keep the one grade that says how the concept
%                         and the class differ, and unlink the other
%                         edge.
% edge:                   []
%
% ...
%
% decl conflicting_match(concept: symbol,
%                        class:   symbol,
%                        grade:   symbol,
%                        other:   symbol)
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
% ---
%
% id_self:                lpp_cctool.check.check.mapping_against_hierarchy
% guid_self:              lpp_ded023551b1e4181b4689cf55b388f79
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Mapping against hierarchy
% brief:                  |
%                         A concept narrower than another does not match
%                         a class that the release places above the
%                         class the broader concept matches. Only exact
%                         and close matches are compared, since they say
%                         the concept and the class pick out the same
%                         things.
% did:                    |
%                         {concept} is narrower than {broader}, but it
%                         matches {class}, which the release places
%                         above {broader_class}, the match of {broader}.
% fix:                    |
%                         Correct the match of one of the two concepts,
%                         or the edge of relation_is_narrower_than
%                         between them. Do not change the edges between
%                         external classes by hand; cctool import keeps
%                         them as the release has them.
% edge:                   []
%
% ...
%
% decl mapping_against_hierarchy(concept:       symbol,
%                                broader:       symbol,
%                                class:         symbol,
%                                broader_class: symbol)
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
    has_type(Class, "type_external_class"),
    Concept != Other.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.missing_narrower
% guid_self:              lpp_4dfc87db16fb434b92088a6e975ebbd9
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Missing narrower
% brief:                  |
%                         A concept that the release implies is narrower
%                         than another is narrower than it here too, so
%                         that the concept register keeps the hierarchy
%                         that the mappings claim.
% did:                    |
%                         {concept} is within {class}, which the release
%                         places at or below {broader_class}, the match
%                         of {broader}, but {concept} is not narrower
%                         than {broader}.
% fix:                    |
%                         Add an edge of relation_is_narrower_than from
%                         the concept to the broader one, or to a
%                         concept narrower than it, or correct the match
%                         of one of the two concepts.
% edge:                   []
%
% ...
%
% decl missing_narrower(concept:       symbol,
%                       broader:       symbol,
%                       class:         symbol,
%                       broader_class: symbol)
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
% ---
%
% id_self:                lpp_cctool.check.check.false_friend
% guid_self:              lpp_1a92a7a68349447989f5e722dc6f4754
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  False friend
% brief:                  |
%                         A concept whose term is the label of an
%                         external class either matches that class
%                         exactly or closely, or has an annotation about
%                         both that says why not. The same word with
%                         another sense is a false friend, and a reader
%                         who knows the release will take the wrong
%                         sense.
% did:                    |
%                         {concept} has the term "{term}", which is the
%                         label of {class}, but {concept} has no exact
%                         or close match in {class}.
% fix:                    |
%                         Match the concept in the class if they pick
%                         out the same things. Otherwise add an
%                         annotation about both that says how they
%                         differ, with edges of relation_is_about to
%                         each.
% edge:                   []
%
% ...
%
% decl false_friend(concept: symbol,
%                   term:    symbol,
%                   class:   symbol)
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
% The relation entry relates only pairs that the external relation
% relates too: its match there is exact, close or broad.
%
% decl within_relation(relation: symbol,
%                      external: symbol)

within_relation(Relation, External) :-
    equivalent_match(Relation, External),
    has_type(External, "type_external_relation").

within_relation(Relation, External) :-
    match(Relation, "broad", External),
    has_type(External, "type_external_relation").


% -----------------------------------------------------------------------------
% The release says that whatever the external relation relates at its
% end, source or target, is an instance of the external class: the
% class is its domain or its range, or one of a union of them.
%
% decl end_class(external: symbol,
%                end:      symbol,
%                class:    symbol)

end_class(External, "source", Class) :-
    primary_edge(External, "relation_has_domain", Class).

end_class(External, "target", Class) :-
    primary_edge(External, "relation_has_range", Class).


% -----------------------------------------------------------------------------
% The relation entry constrains its end, source or target, by the
% relation constraint.
%
% decl end_constraint(relation:   symbol,
%                     end:        symbol,
%                     constraint: symbol)

end_constraint(Relation, "source", Constraint) :-
    primary_edge(Relation, "relation_constrains_source", Constraint).

end_constraint(Relation, "target", Constraint) :-
    primary_edge(Relation, "relation_constrains_target", Constraint).


% -----------------------------------------------------------------------------
% An item of the type fails one of the constraints of the relation entry
% at its end.
%
% decl refused_at_end(relation: symbol,
%                     end:      symbol,
%                     type:     symbol)

refused_at_end(Relation, End, Type) :-
    end_constraint(Relation, End, Constraint),
    type_prefix(Type, _, _),
    not satisfies(Type, Constraint).


% -----------------------------------------------------------------------------
% The relation entry constrains its end, and an item of the type meets
% every constraint there. An end that reads through a proxy is left out,
% since what it relates is the thing the proxy points at, not an item of
% the type.
%
% decl admitted_at_end(relation: symbol,
%                      end:      symbol,
%                      type:     symbol)

admitted_at_end(Relation, End, Type) :-
    end_constraint(Relation, End, _),
    type_prefix(Type, _, _),
    not refused_at_end(Relation, End, Type),
    not reads_through(Relation, End).


% -----------------------------------------------------------------------------
% The items of the type all belong to the external class: the concept of
% the type, or a concept it is narrower than, is within the class.
%
% decl type_within(type:  symbol,
%                  class: symbol)

type_within(Type, Class) :-
    reference(Type, "concept", Concept, _, _, _),
    within_class(Concept, Class),
    has_type(Class, "type_external_class").

type_within(Type, Class) :-
    reference(Type, "concept", Concept, _, _, _),
    reaches("relation_is_narrower_than", Concept, Broader),
    within_class(Broader, Class),
    has_type(Class, "type_external_class").


% -----------------------------------------------------------------------------
% The external class is the other, or the release places it below the
% other.
%
% decl at_or_below(class: symbol,
%                  other: symbol)

at_or_below(Class, Class) :-
    has_type(Class, "type_external_class").

at_or_below(Class, Other) :-
    reaches("relation_is_subclass_of", Class, Other).


% -----------------------------------------------------------------------------
% The external class is at or below, or at or above, a class that the
% release gives for the end of the external relation, so the two may
% share instances.
%
% decl fits_end(external: symbol,
%               end:      symbol,
%               class:    symbol)

fits_end(External, End, Class) :-
    end_class(External, End, Bound),
    at_or_below(Class, Bound).

fits_end(External, End, Class) :-
    end_class(External, End, Bound),
    at_or_below(Bound, Class).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.end_outside_release
% guid_self:              lpp_d5cdddadf51a4583b0a219ca6dfd74b3
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  End outside release
% brief:                  |
%                         A relation entry that matches an external
%                         relation admits at each of its ends only types
%                         whose items the release lets that relation
%                         relate there. A type is outside when its
%                         concept is within a class that is neither at
%                         or below nor at or above any class that the
%                         release gives for the end. A type whose
%                         concept has no match, or a class above the
%                         bound, cannot be judged and is left alone.
% did:                    |
%                         {relation} admits {type} at its {end}, and the
%                         concept of {type} is within {class}, but
%                         {external}, which {relation} matches, relates
%                         there only instances of classes that {class}
%                         is neither at or below nor at or above.
% fix:                    |
%                         Correct the match of the relation entry, its
%                         constraint at that end, or the match of the
%                         concept of the type. Do not change the domain
%                         or range of the external relation by hand;
%                         cctool import keeps them as the release has
%                         them.
% edge:                   []
%
% ...
%
% decl end_outside_release(relation: symbol,
%                          end:      symbol,
%                          type:     symbol,
%                          class:    symbol,
%                          external: symbol)
#show end_outside_release/5.

end_outside_release(Relation, End, Type, Class, External) :-
    within_relation(Relation, External),
    end_class(External, End, _),
    admitted_at_end(Relation, End, Type),
    type_within(Type, Class),
    not fits_end(External, End, Class).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.argument_without_concern
% guid_self:              lpp_2f46ab25306d448e80e3335a8f2b0208
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Argument without concern
% brief:                  |
%                         An annotation that supports or challenges an
%                         option speaks for at least one concern. A
%                         premise that several concerns rest on is one
%                         annotation that speaks for each of them.
% did:                    |
%                         The annotation {id} supports or challenges an
%                         option and argues for no concern.
% fix:                    |
%                         Link it with relation_speaks_for_concern to
%                         each concern it speaks for.
% edge:                   []
%
% ...
%
% decl argument_without_concern(id: symbol)
#show argument_without_concern/1.

argument_without_concern(Id) :-
    practical(Id),
    not primary_edge(Id, "relation_speaks_for_concern", _).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.concern_without_option
% guid_self:              lpp_cc1f8166789c4f12a4ed253472103ed7
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Concern without option
% brief:                  |
%                         An annotation that bears on no option speaks
%                         for no concern, since it is answered with
%                         evidence and not outweighed.
% did:                    |
%                         The annotation {id} speaks for {concern} and
%                         bears on no option.
% fix:                    |
%                         A fact is answered with evidence, not weighed
%                         by concern. Remove the edge to the concern, or
%                         link the annotation to the option it argues.
% edge:                   []
%
% ...
%
% decl concern_without_option(id:      symbol,
%                             concern: symbol)
#show concern_without_option/2.

concern_without_option(Id, Concern) :-
    has_type(Id, "type_annotation"),
    not practical(Id),
    primary_edge(Id, "relation_speaks_for_concern", Concern).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.schema_count
% guid_self:              lpp_593eea3ec4e247bbbc94c62f59977950
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Schema count
% brief:                  |
%                         Every type names exactly one schema for its
%                         items.
% did:                    |
%                         The type {type} names {schemas} schemas for
%                         its items, not 1.
% fix:                    |
%                         Give the type one edge of
%                         relation_has_items_specified_by_schema.
% edge:                   []
%
% ...
%
% decl schema_count(type:    symbol,
%                   schemas: number)
#show schema_count/2.

schema_count(Type, Schemas) :-
    type_prefix(Type, _, _),
    Schemas = #count { Schema :
                       primary_edge(Type, "relation_has_items_specified_by_schema", Schema) },
    Schemas != 1.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.segment_count
% guid_self:              lpp_2c85487f26b845f5ba777dd4af81a0d3
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Segment count
% brief:                  |
%                         Every tree holds exactly one segment item,
%                         which declares it a segment of the federation
%                         and names the releases it consumes.
% did:                    The tree holds {segments} segment items, not 1.
% fix:                    Give the tree one segment item in _data/federated_segment/, naming with relation_consumes the release item of each segment it consumes.
% edge:                   []
%
% ...
%
% decl segment_count(segments: number)
#show segment_count/1.

segment_count(Segments) :-
    Segments = #count { Segment : has_type(Segment, "type_federated_segment"),
                                  item(Segment, _, _, File, _),
                                  not consumed_file(File) },
    Segments != 1.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.unused_schema
% guid_self:              lpp_c09ca296e370441ab621d46dd6a02c1d
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unused schema
% brief:                  |
%                         Every schema is used: named for the items of a
%                         type, named by a register for itself, or
%                         referred to by another schema.
% did:                    |
%                         Nothing uses the schema {id}.
% fix:                    |
%                         Name it from a type, a register or another
%                         schema, or remove it.
% edge:                   []
%
% ...
%
% decl unused_schema(id: symbol)
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
% ---
%
% id_self:                lpp_cctool.check.check.unused_concept
% guid_self:              lpp_f753ffcada224c99995d2141a5a31600
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unused concept
% brief:                  |
%                         Every concept is named by some item other than
%                         itself.
% did:                    |
%                         No item but itself names the concept {id}.
% fix:                    |
%                         Name the concept from the item that needs it,
%                         made with it in one cctool batch, or remove
%                         the concept.
% edge:                   []
%
% ...
%
% decl unused_concept(id: symbol)
#show unused_concept/1.

unused_concept(Id) :-
    has_type(Id, "type_concept"),
    not named_by_other(Id).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.misnamed_node
% guid_self:              lpp_cbbdd8b9e9fc416bb75ef076697ca1ed
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Misnamed node
% brief:                  |
%                         A node is named for the dataflow graph that
%                         holds it and the key it is filed under: the
%                         stem of the dataflow graph, with dfn in place
%                         of dfg, a full stop and the key.
% did:                    |
%                         The node {node} is not named for the dataflow
%                         graph that holds it and its key. Its id is
%                         {expected}.
% fix:                    |
%                         Rename the node with cctool rename to the id
%                         the check expects. To rename the dataflow
%                         graph, use cctool rename, which renames its
%                         nodes with it.
% edge:                   []
%
% ...
%
% decl misnamed_node(node:     symbol,
%                    expected: symbol)
#show misnamed_node/2.

misnamed_node(Node, Expected) :-
    dataflow_node(Graph, Key, Node, _),
    type_prefix("type_dataflow_graph", Prefix, _),
    type_prefix("type_dataflow_node", Member, _),
    Start = @strlen(Prefix) + 1,
    Expected = @cat(Member, "_", @substr(Graph, Start, @strlen(Graph) - Start), ".", Key),
    Node != Expected.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.interface_count
% guid_self:              lpp_39896de6019a42dd89d7ed2ea3a63503
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Interface count
% brief:                  |
%                         Every node presents exactly one interface: it
%                         realizes one interface control document, whose
%                         dataflow step surface it presents.
% did:                    |
%                         The node {node} realizes {interfaces}
%                         interface control documents, not 1.
% fix:                    |
%                         Give the node one edge of relation_realizes to
%                         the interface control document whose dataflow
%                         step surface it presents.
% edge:                   []
%
% ...
%
% decl interface_count(node:       symbol,
%                      interfaces: number)
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
% ---
%
% id_self:                lpp_cctool.check.check.foreign_node
% guid_self:              lpp_43a9cb5c1a324232817cdc20bb962913
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Foreign node
% brief:                  |
%                         Each end of an edge names a node of the
%                         dataflow graph that holds the edge.
% did:                    |
%                         The {end} of an edge of {graph} names {node},
%                         which is not one of its nodes.
% fix:                    |
%                         Name a node that the dataflow graph holds, or
%                         add the node to it.
% edge:                   []
%
% ...
%
% decl foreign_node(graph: symbol,
%                   end:   symbol,
%                   node:  symbol,
%                   file:  symbol,
%                   line:  number)
#show foreign_node/5.

foreign_node(Graph, End, Node, File, Line) :-
    edge_end(Graph, End, Node, _, _, File, Line),
    not dataflow_node(Graph, _, Node, _).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.unknown_port
% guid_self:              lpp_9baf600d81914ed49f1ef83f3eb4ef1e
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unknown port
% brief:                  |
%                         Each end of an edge names a port of the
%                         interface its node presents, of the kind the
%                         end needs: an output at the source and an
%                         input at the target.
% did:                    |
%                         An edge names {port} at {node}, which is not
%                         an {kind} of the interface the node presents.
% fix:                    |
%                         Name a port of that kind from the dataflow
%                         step surface of the interface the node
%                         realizes, or add the port to the surface.
% edge:                   []
%
% ...
%
% decl unknown_port(node: symbol,
%                   port: symbol,
%                   kind: symbol,
%                   file: symbol,
%                   line: number)
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
% ---
%
% id_self:                lpp_cctool.check.check.input_fed_twice
% guid_self:              lpp_5bb6da618b0f4622a6350c5dbf5276e1
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Input fed twice
% brief:                  |
%                         An input takes its value from at most one
%                         edge. Edges are counted where they are
%                         written, so a second copy of one edge counts
%                         too.
% did:                    |
%                         {edges} edges end at the input {port} of
%                         {node}, not 1.
% fix:                    |
%                         Keep one edge into the input. To combine
%                         values, add a node that reads each of them on
%                         an input of its own.
% edge:                   []
%
% ...
%
% decl input_fed_twice(node:  symbol,
%                      port:  symbol,
%                      edges: number)
#show input_fed_twice/3.

input_fed_twice(Node, Port, Edges) :-
    fed(Node, Port),
    Edges = #count { File, Line : dataflow_edge(_, _, _, Node, Port, _, File, Line) },
    Edges > 1.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.unfed_input
% guid_self:              lpp_b4e36af1903c4668a0977b40d005fbc3
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unfed input
% brief:                  |
%                         Every input that the interface of a node does
%                         not state to be optional takes its value from
%                         an edge.
% did:                    |
%                         No edge ends at the input {port} of {node},
%                         and the interface does not state that it is
%                         optional.
% fix:                    |
%                         Add an edge into the input, or state optional:
%                         true for it in the interface if an invocation
%                         may run without it.
% edge:                   []
%
% ...
%
% decl unfed_input(node: symbol,
%                  port: symbol)
#show unfed_input/2.

unfed_input(Node, Port) :-
    dataflow_node(_, _, Node, _),
    node_interface(Node, Interface),
    interface_port(Interface, "input", _, Port),
    not stated(Port, "optional", "true"),
    not fed(Node, Port).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.port_type_mismatch
% guid_self:              lpp_a24c1944765f444581630f40470a44cf
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Port type mismatch
% brief:                  |
%                         The ports at the two ends of an edge state the
%                         same type, where both state one.
% did:                    |
%                         An edge carries {source_type} from
%                         {source_port} into {target_port}, which takes
%                         {target_type}.
% fix:                    |
%                         Connect ports of the same type, or correct the
%                         type an interface states. Add a node that
%                         converts the value if both are right.
% edge:                   []
%
% ...
%
% decl port_type_mismatch(source_port: symbol,
%                         source_type: symbol,
%                         target_port: symbol,
%                         target_type: symbol,
%                         file:        symbol,
%                         line:        number)
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
% ---
%
% id_self:                lpp_cctool.check.check.feedforward_loop
% guid_self:              lpp_7538f8e11b154062b832587f0bccf200
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Feedforward loop
% brief:                  |
%                         Every loop of data flow is closed by a
%                         feedback edge, whose value comes from the
%                         invocation before. A loop of feedforward edges
%                         only has a node wait on its own output, which
%                         never comes.
% did:                    |
%                         Data from {node} comes back to it through
%                         feedforward edges only, so it waits on its own
%                         output.
% fix:                    |
%                         Give the edge that closes the loop direction:
%                         feedback.
% edge:                   []
%
% ...
%
% decl feedforward_loop(node: symbol)
#show feedforward_loop/1.

feedforward_loop(Node) :-
    feeds_forward(Node, Node).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.unknown_setting
% guid_self:              lpp_299bc6baf08d406baa9fa600d4934211
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unknown setting
% brief:                  |
%                         A node is configured only with settings its
%                         interface declares.
% did:                    |
%                         {node} gives a value for {setting}, which is
%                         not a setting of the interface it presents.
% fix:                    |
%                         Correct the name of the setting, or add the
%                         setting to the dataflow step surface of the
%                         interface.
% edge:                   []
%
% ...
%
% decl unknown_setting(node:    symbol,
%                      setting: symbol)
#show unknown_setting/2.

unknown_setting(Node, Setting) :-
    dataflow_setting(Node, Setting),
    node_interface(Node, Interface),
    not interface_port(Interface, "settings", Setting, _).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.missing_setting
% guid_self:              lpp_7c53a32f56aa481cab6ee244fa62a29c
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Missing setting
% brief:                  |
%                         A node gives a value for each setting that its
%                         interface neither states to be optional nor
%                         gives a default.
% did:                    |
%                         {node} gives no value for {setting}, which its
%                         interface needs.
% fix:                    |
%                         Give the setting a value in the settings of
%                         the node.
% edge:                   []
%
% ...
%
% decl missing_setting(node:    symbol,
%                      setting: symbol)
#show missing_setting/2.

missing_setting(Node, Setting) :-
    dataflow_node(_, _, Node, _),
    node_interface(Node, Interface),
    interface_port(Interface, "settings", Setting, Member),
    not stated(Member, "optional", "true"),
    not stated(Member, "default", _),
    not dataflow_setting(Node, Setting).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.unplaced
% guid_self:              lpp_78baa72364664cb1b05698fa6e3d95a1
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unplaced
% brief:                  |
%                         A node runs on an OS process of its dataflow
%                         graph, and an OS process on a host of it.
% did:                    |
%                         {holder} in {graph} runs on {key}, which the
%                         dataflow graph does not list.
% fix:                    |
%                         Name an OS process or host the dataflow graph
%                         lists, or add it to the os_process or host
%                         section.
% edge:                   []
%
% ...
%
% decl unplaced(graph:  symbol,
%               holder: symbol,
%               key:    symbol)
#show unplaced/3.

unplaced(Graph, Node, Process) :-
    dataflow_node(Graph, _, Node, Process),
    Process != "",
    not os_process(Graph, Process, _).

unplaced(Graph, Process, Host) :-
    os_process(Graph, Process, Host),
    not host(Graph, Host).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.unheld_design_rule
% guid_self:              lpp_acc545a491734217811a99d7aa317e3b
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unheld design rule
% brief:                  |
%                         A design rule names an implementation that
%                         holds it, in whole or in part, with an edge of
%                         relation_is_held_by. A rule that names none is
%                         held by the scheduled reviews alone, and that
%                         is accepted only by a ruling on a decision
%                         about the rule.
% did:                    |
%                         {rule} names nothing that holds it, and no
%                         ruling settles a decision about it.
% fix:                    |
%                         Add an edge of relation_is_held_by to the
%                         check, advice or code that finds where the
%                         rule is broken. If only the scheduled reviews
%                         can judge it, raise a decision about the rule
%                         and leave it to a ruling. Do not narrow the
%                         rule to a sentence that nothing breaks.
% edge:                   []
%
% ...
%
% decl unheld_design_rule(rule: symbol,
%                         file: symbol,
%                         line: number)
#show unheld_design_rule/3.

% decl rule_held(rule: symbol)

rule_held(Rule) :-
    primary_edge(Rule, "relation_is_held_by", _).

% decl rule_left_to_review(rule: symbol)

rule_left_to_review(Rule) :-
    primary_edge(Decision, "relation_is_about", Rule),
    has_type(Decision, "type_decision"),
    settles(_, Option),
    decision_of(Option, Decision).

unheld_design_rule(Rule, File, Line) :-
    has_type(Rule, "type_design_rule"),
    item(Rule, _, _, File, Line),
    not rule_held(Rule),
    not rule_left_to_review(Rule).


% -----------------------------------------------------------------------------
% No more design rules are left to the scheduled reviews alone than the
% cap, however each was accepted, so that accepting one stays rare. The
% cap is raised only by a ruling.
%
% decl unheld_rule_cap(cap: number)

unheld_rule_cap(3).

% ---
%
% id_self:                lpp_cctool.check.check.too_many_unheld_rules
% guid_self:              lpp_d66677765831409eafe44046b264490f
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Too many unheld rules
% brief:                  |
%                         No more design rules are held by the scheduled
%                         reviews alone than the cap, however each was
%                         accepted, so that accepting one stays rare.
% did:                    |
%                         {count} design rules are held by the scheduled
%                         reviews alone, more than the cap of {cap}.
% fix:                    |
%                         Hold one of them with a check, or cut the part
%                         of a rule that nothing holds. Raise the cap
%                         only by a ruling.
% edge:                   []
%
% ...
%
% decl too_many_unheld_rules(count: number,
%                            cap:   number)
#show too_many_unheld_rules/2.

too_many_unheld_rules(Count, Cap) :-
    unheld_rule_cap(Cap),
    Count = #count { Rule : has_type(Rule, "type_design_rule"), not rule_held(Rule) },
    Count > Cap.


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.unheld_claim
% guid_self:              lpp_336c7dd1f29d41e9a18ba876b602c17c
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unheld claim
% brief:                  |
%                         A writing style rule that says a check or the
%                         formatter holds it names what holds it, with
%                         an edge of relation_is_held_by.
% did:                    |
%                         {rule} says that {mechanism} holds it, and
%                         names nothing that does.
% fix:                    |
%                         Add an edge of relation_is_held_by to what
%                         holds the rule, or set its enforcement to what
%                         does.
% edge:                   []
%
% ...
%
% decl unheld_claim(rule:      symbol,
%                   mechanism: symbol,
%                   file:      symbol,
%                   line:      number)
#show unheld_claim/4.

unheld_claim(Rule, Mechanism, File, Line) :-
    enforcement(Rule, Mechanism),
    Mechanism != "none",
    Mechanism != "judge",
    item(Rule, _, _, File, Line),
    not rule_held(Rule).


% -----------------------------------------------------------------------------
% The segment consumes the segment consumed: it has an edge of
% relation_consumes to a release item that consumed holds.
%
% decl segment_consumes(segment:  symbol,
%                       consumed: symbol)

segment_consumes(Segment, Consumed) :-
    edge(Segment, "relation_consumes", Release),
    item(Release, _, _, File, _),
    segment_of(File, Consumed).


% -----------------------------------------------------------------------------
% The segment has an edge of relation_consumes to a release item that no
% tree holds. Its references into the trees it reads are then left to
% the dangling reference of that edge.
%
% decl unresolved_consumes(segment: symbol)

unresolved_consumes(Segment) :-
    edge(Segment, "relation_consumes", Release),
    not item(Release, _, _, _, _).


% -----------------------------------------------------------------------------
% The item holder, in file at line, names the item id by a reference or a
% mention.
%
% decl names_item(holder: symbol,
%                 id:     symbol,
%                 file:   symbol,
%                 line:   number)

names_item(Holder, Id, File, Line) :-
    reference(Holder, _, Id, _, File, Line).

names_item(Holder, Id, File, Line) :-
    mention(Holder, Id, File, Line).


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.check.check.unconsumed_reference
% guid_self:              lpp_0279eecdc70041bb914ca6a39f653b33
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Unconsumed reference
% brief:                  |
%                         A reference or mention runs only within a
%                         segment, or into a segment that its own
%                         segment consumes.
% did:                    |
%                         {holder}, in the segment {segment}, names
%                         {id}, which the segment {other} holds, but
%                         {segment} does not consume {other}.
% fix:                    |
%                         Remove the reference. If the segment is to
%                         rely on the other, give its segment item an
%                         edge of relation_consumes to the release of
%                         the other that it relies on. A consumed
%                         segment never names a segment that consumes
%                         it.
% edge:                   []
%
% ...
%
% decl unconsumed_reference(holder:   symbol,
%                           id:       symbol,
%                           segment:  symbol,
%                           other:    symbol,
%                           file:     symbol,
%                           line:     number)
#show unconsumed_reference/6.

unconsumed_reference(Holder, Id, Segment, Other, File, Line) :-
    names_item(Holder, Id, File, Line),
    segment_of(File, Segment),
    item(Id, _, _, Target, _),
    segment_of(Target, Other),
    Segment != Other,
    not segment_consumes(Segment, Other),
    not unresolved_consumes(Segment).
