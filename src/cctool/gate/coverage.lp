% ---
%
% id_self:                lpf_cctool.gate.coverage
% guid_self:              lpf_30d53ee6bf124378a631d039855b96f9
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Coverage against maturity
% brief:                  |
%                         The rule that compares the coverage measured
%                         of each source file with the floor its
%                         maturity level sets.
% description:            |
%                         The coverage measured is not a fact of the
%                         tree: pym_cctool.gate.coverage reads it from
%                         the data a run of the tests under coverage
%                         wrote, and adds it to the facts of the tree as
%                         measured_coverage, in a thousand, for this
%                         program alone. Nothing measured is kept.
% usage:                  |
%                         Evaluated by pym_cctool.gate.coverage after
%                         lpf_cctool.graph.derive.
% edge:                   []
%
% ...


% -----------------------------------------------------------------------------
% ---
%
% id_self:                lpp_cctool.gate.coverage.coverage_below_floor
% guid_self:              lpp_7fc7c2f2f690489d8cd1b58f71b38241
% copyright:              Copyright 2026 William Payne
% license:                Apache-2.0
%
% protective_mark:
%
%   - id_mark:            mark_public
%     guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f
%
% title:                  Coverage below the floor
% brief:                  |
%                         The tests cover each source file at least as
%                         much as the floor of lines and branches that
%                         its maturity level, or a lower one, sets. A
%                         file the run did not measure is covered by
%                         none.
% did:                    |
%                         {file} has {kind} coverage of {measured} in a
%                         thousand, below the floor of {floor} in a
%                         thousand that its maturity sets.
% fix:                    |
%                         Write the tests that reach what is not
%                         covered, or lower the maturity of the file
%                         until they exist.
% edge:                   []
%
% ...
%
% decl coverage_below_floor(file:     symbol,
%                           kind:     symbol,
%                           measured: number,
%                           floor:    number)
#show coverage_below_floor/4.

coverage_below_floor(File, Kind, Measured, Floor) :-
    file_floor(Id, Kind, Floor),
    item(Id, _, "", File, _),
    covered(File, Kind, Measured),
    Measured < Floor.


% -----------------------------------------------------------------------------
% The coverage of the kind measured of the file, in a thousand, or none
% if the run did not measure the file.
%
% decl covered(file:     symbol,
%              kind:     symbol,
%              measured: number)

covered(File, Kind, Measured) :-
    measured_coverage(File, Kind, Measured).

covered(File, Kind, 0) :-
    file_floor(Id, Kind, _),
    item(Id, _, "", File, _),
    not measured_coverage(File, _, _).


% -----------------------------------------------------------------------------
% The floor of the kind of coverage, in a thousand, that the maturity
% of the file that holds the item id sets: the highest that its level,
% or a lower level, sets.
%
% decl file_floor(id:    symbol,
%                 kind:  symbol,
%                 floor: number)

file_floor(Id, Kind, Floor) :-
    has_floor(Id, Kind),
    Floor = #max { Percent * 10 : coverage_floor(Entry, Kind, Percent),
                                  maturity_level(Entry, Below),
                                  file_maturity(Id, Level),
                                  Below <= Level }.


% -----------------------------------------------------------------------------
% The maturity of the file that holds the item id, or a lower level,
% sets a floor of the kind of coverage.
%
% decl has_floor(id:   symbol,
%                kind: symbol)

has_floor(Id, Kind) :-
    file_maturity(Id, Level),
    coverage_floor(Entry, Kind, _),
    maturity_level(Entry, Below),
    Below <= Level.
