% ---
%
% id_self:                lpf_cc_public.commit.change
% guid_self:              lpf_b63f515e0e9f4eefb74c4ca1aa673a8b
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Commit checks
% brief:                  |
%                         Checks of a commit against the graph before
%                         and after it.
% description:            |
%                         The base predicates hold the graph after the
%                         commit: the staged content. before_item holds
%                         the items of the graph before it: the content
%                         of HEAD. commit_verb, commit_mention and
%                         content_change describe the commit itself.
%
%                         Each shown predicate is one check, and each
%                         row of it is one failure. The checks come in
%                         order: identity, then the verb of the title.
% usage:                  |
%                         Evaluated by pym_cc_public.commit.change. The
%                         facts of the base predicates and the rules of
%                         lpf_cc_public.graph.derive come before this
%                         file in the program.
% edge:                   []
%
% ...

% -----------------------------------------------------------------------------
% Each item of the graph before the commit, with its guid.
%
% decl before_item(id:   symbol,
%                  guid: symbol)


% -----------------------------------------------------------------------------
% The verb that the title of the commit begins with.
%
% decl commit_verb(verb: symbol)


% -----------------------------------------------------------------------------
% Each id that the title, brief or description of the commit names.
%
% decl commit_mention(id: symbol)


% -----------------------------------------------------------------------------
% Each file whose content differs before and after the commit, beyond
% what the layout printer changes. A file added or removed counts.
%
% decl content_change(file: symbol)


% -----------------------------------------------------------------------------
% The guids of the graph before the commit, and after it.
%
% decl before_guid(guid: symbol)

before_guid(Guid) :-
    before_item(_, Guid).

% decl after_guid(guid: symbol)

after_guid(Guid) :-
    item(_, Guid, _, _, _).

% The 32 hex digits that end a guid, found once for each guid, so
% that guids are matched by their digits rather than pair by pair.
%
% decl digits(guid:   symbol,
%             digits: symbol)

digits(Guid, @substr(Guid, @strlen(Guid) - 32, 32)) :-
    before_guid(Guid),
    @strlen(Guid) >= 32.

digits(Guid, @substr(Guid, @strlen(Guid) - 32, 32)) :-
    after_guid(Guid),
    @strlen(Guid) >= 32.


% -----------------------------------------------------------------------------
% An item the commit adds, removes, or gives a new id.
%
% decl added(id:   symbol,
%            guid: symbol)

added(Id, Guid) :-
    item(Id, Guid, _, _, _),
    not before_guid(Guid).

% decl removed(id:   symbol,
%              guid: symbol)

removed(Id, Guid) :-
    before_item(Id, Guid),
    not after_guid(Guid).

% decl renamed(guid:  symbol,
%              id:    symbol,
%              other: symbol)

renamed(Guid, Id, Other) :-
    before_item(Id, Guid),
    item(Other, Guid, _, _, _),
    Id != Other.


% -----------------------------------------------------------------------------
% A guid keeps its type. The 32 hex digits of a guid that existed
% before the commit are not given another prefix after it.
%
% decl retyped_guid(guid:  symbol,
%                   other: symbol)
% did  The guid {guid} becomes {other}: its digits carry another prefix.
% fix  Keep the type of an item. To change it, remove the item, make a
%      new one, and say so in the commit.
#show retyped_guid/2.

retyped_guid(Guid, Other) :-
    before_guid(Guid),
    digits(Guid, Digits),
    digits(Other, Digits),
    after_guid(Other),
    Guid != Other.


% -----------------------------------------------------------------------------
% Nothing disappears without the commit saying so. The commit item
% names each item that the commit removes.
%
% decl unannounced_removal(id:   symbol,
%                          guid: symbol)
% did  The commit removes {id} and does not name it.
% fix  Name the id of each item removed in the title, brief or
%      description of the commit item.
#show unannounced_removal/2.

unannounced_removal(Id, Guid) :-
    removed(Id, Guid),
    not commit_mention(Id).


% -----------------------------------------------------------------------------
% The commit item names each item that the commit gives a new id, by
% its old id or its new one.
%
% decl unannounced_rename(id:    symbol,
%                         other: symbol)
% did  The commit renames {id} to {other} and names neither.
% fix  Name the old id or the new one in the title, brief or description
%      of the commit item.
#show unannounced_rename/2.

unannounced_rename(Id, Other) :-
    renamed(_, Id, Other),
    not commit_mention(Id),
    not commit_mention(Other).


% -----------------------------------------------------------------------------
% A register entry given a new id keeps its old id in its alias list,
% so that references by the old id can be found and resolved. An item
% embedded in another, such as an interface member or a dataflow node,
% is not a register entry: its schema allows no alias, and what refers
% to it carries its guid. A revert is the exception: it restores an
% entry as it was, with the id and the aliases it had then, and that
% content passed when it was first committed.
%
% decl rename_without_alias(id:    symbol,
%                           other: symbol)
% did  The register entry {other}, renamed from {id}, does not keep {id}
%      in its alias list.
% fix  Add the old id to the alias list of the entry. cctool rename does
%      this.
#show rename_without_alias/2.

rename_without_alias(Id, Other) :-
    renamed(_, Id, Other),
    register_entry_key(_, _, Other),
    not alias(Other, Id),
    not commit_verb("Revert"),
    not commit_verb("Reapply").


% -----------------------------------------------------------------------------
% The kinds of change to the items of the graph that a verb rules out.
% Add adds, Remove removes, and Rename and Move change ids or places
% but neither add nor remove.
%
% decl forbidden_change(verb: symbol,
%                       kind: symbol)

forbidden_change("Add", "remove").
forbidden_change("Add", "rename").
forbidden_change("Remove", "add").
forbidden_change("Remove", "rename").
forbidden_change("Rename", "add").
forbidden_change("Rename", "remove").
forbidden_change("Move", "add").
forbidden_change("Move", "remove").

% decl item_change(kind: symbol,
%                  id:   symbol)

item_change("add", Id) :-
    added(Id, _).

item_change("remove", Id) :-
    removed(Id, _).

item_change("rename", Other) :-
    renamed(_, _, Other).


% -----------------------------------------------------------------------------
% The verb of the title is true of the change. A change of a kind that
% the verb rules out contradicts it.
%
% decl verb_contradicted(verb: symbol,
%                        kind: symbol,
%                        id:   symbol)
% did  The title says {verb}, and the commit makes a change of kind
%      {kind} to {id}.
% fix  Use the verb that is true of the change, or split the commit so
%      that each does one thing.
#show verb_contradicted/3.

verb_contradicted(Verb, Kind, Id) :-
    commit_verb(Verb),
    forbidden_change(Verb, Kind),
    item_change(Kind, Id).


% -----------------------------------------------------------------------------
% A commit titled Reformat changes nothing beyond layout.
%
% decl reformat_changes_content(file: symbol)
% did  The commit is titled Reformat and changes the content of {file}.
% fix  Commit the change of content on its own, with a verb of its own.
#show reformat_changes_content/1.

reformat_changes_content(File) :-
    commit_verb("Reformat"),
    content_change(File).
