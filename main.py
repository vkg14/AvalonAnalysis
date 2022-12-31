from dataclasses import dataclass
from datetime import datetime
from enum import auto
from functools import cached_property
from typing import Dict, Optional, List

import pandas as pd
from dateutil.parser import parse
from strenum import StrEnum


class Team(StrEnum):
    GOOD = auto()
    EVIL = auto()


class Role(StrEnum):
    MERLIN = auto()
    PERCIVAL = auto()
    LOYAL_SERVANT = auto()
    MORDRED = auto()
    MORGANA = auto()
    ASSASSIN = auto()
    MINION = auto()
    OBERON = auto()


AFFILIATIONS = {
    Role.MERLIN: Team.GOOD,
    Role.PERCIVAL: Team.GOOD,
    Role.LOYAL_SERVANT: Team.GOOD,
    Role.OBERON: Team.EVIL,
    Role.MINION: Team.EVIL,
    Role.ASSASSIN: Team.EVIL,
    Role.MORGANA: Team.EVIL,
    Role.MORDRED: Team.EVIL
}


class SummaryParser:
    @staticmethod
    def _parse_assignments(text) -> Dict[str, Role]:
        team_str, assignments_str = text.split(': ')
        team = Team(team_str.upper())
        assignments = [a.split() for a in assignments_str.split(', ')]
        default_character = Role.LOYAL_SERVANT if team == Team.GOOD else Role.MINION
        parse_role = lambda s: s[s.find("(") + 1:s.find(")")]
        return {
            assignment[0]: Role(parse_role(assignment[1].upper())) if len(assignment) > 1 else default_character
            for assignment in assignments
        }

    @staticmethod
    def parse_summary(game_id: int, text: str):
        """
        Sample text based on expected format:
        12/15/2022
        Good wins in 4 missions!
        Good: Bruno (Merlin), Vkg (Percival), Max, Cale, Julie, Dean
        Evil: Austin (Mordred), Kate (Morgana), Evan (Assassin)
        Assassinated: Cale
        """
        sp = text.split('\n')
        dt = parse(sp[0])
        # Parse winner and number missions from: "Good wins in 4 missions!"
        winner = Team(sp[1].split()[0].upper())
        n_missions = int(sp[1].split()[3])
        # Parse player and team affiliations
        players = SummaryParser._parse_assignments(sp[2]) | SummaryParser._parse_assignments(sp[3])
        assassinated = sp[4].split(': ')[1] if len(sp) > 4 else None
        return GameSummary(game_id, dt, players, n_missions, winner, assassinated, text)


@dataclass
class GameSummary:
    game_id: int
    dt: datetime
    players: Dict[str, Role]
    n_missions: int
    winner: Team
    assassinated: Optional[str]
    raw_text: str

    def __post_init__(self):
        if sum(1 if AFFILIATIONS[c] == Team.GOOD else -1 for c in self.players.values()) <= 0:
            raise Exception(f"Game {self.game_id} should have more good than bad players:\n{self.raw_text}")
        if self.winner == Team.GOOD and not self.assassinated:
            raise Exception(f"An assassination was expected in game {self.game_id}:\n{self.raw_text}")

    def get_game_level_data(self):
        win_by_assassination = True if self.players.get(self.assassinated, None) == Role.MERLIN else False
        good_won = self.winner == Team.GOOD
        return [self.dt, len(self.players), self.n_missions, good_won, win_by_assassination]

    def get_player_level_data(self):
        # TODO: understand the contributions of a particular player over the course of many games
        pass


@dataclass
class AvalonAnalysis:
    games: List[GameSummary]

    @cached_property
    def game_level_data(self):
        columns = ['date', 'nPlayers', 'nMissions', 'goodWon', 'wonByAssassination']
        data = [g.get_game_level_data() for g in sorted(self.games, key=lambda t: t.game_id)]
        return pd.DataFrame(data, columns=columns)

    def game_level_stats(self):
        # TODO: Add stats about the most lopsided variant (by number of players)
        total_games = len(self.game_level_data)
        total_good_wins = self.game_level_data.goodWon.sum()
        good_win_pct = total_good_wins * 100.0 / total_games
        print(f"Good wins {good_win_pct}% of the time.")
        win_by_ass = self.game_level_data.wonByAssassination.sum() * 100.0 / (total_games - total_good_wins)
        print(f"When evil wins, {win_by_ass}% is via Merlin assassination.")


if __name__ == '__main__':
    with open('games.txt') as f:
        games_raw = f.read().split('\n\n')
        analysis = AvalonAnalysis([SummaryParser.parse_summary(idx, game) for idx, game in enumerate(games_raw)])
        for game in analysis.games:
            print(f"Game: {game.game_id}, {game.players}, missions: {game.n_missions}, winner: {game.winner}")
        print(analysis.game_level_data)
        analysis.game_level_stats()
