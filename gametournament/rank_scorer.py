from collections import defaultdict

import click

from gametournament.base_scorer import BaseScorer
from gametournament.formula import Formula, FormulaValue
from gametournament.models import TourneyScore, Tournament, Player


class RankScorer(BaseScorer):
    def __init__(self, tournament: Tournament, players: list[Player], game_hours: float):
        super().__init__(tournament, players, game_hours, RankFormula(tournament))

    def score(self) -> dict[int, TourneyScore]:
        """This function converts raw ranks (that might end up tied) to "scores" that can be added to the metascore."""
        ranks_available = list(map(str, range(1, len(self.players) + 1)))
        ranks = []
        for player in self.players:
            rank = click.prompt(
                f"What was the rank for player {player['name']} (lower is better)?",
                show_choices=True,
                type=click.Choice(ranks_available),
            )
            ranks.append((player['id'], int(rank)))
        inverse_ranks = self.invert_ranks(ranks)
        normalized_ranks = self.normalize_ranks(inverse_ranks)
        return self.calculate(normalized_ranks)

    def invert_ranks(self, ranks: list[tuple[int, int]]) -> list[tuple[int, int]]:
        inverted = []
        for player_id, rank in ranks:
            inverse = len(ranks) + 1 - rank
            inverted.append((player_id, inverse))

        return inverted

    def normalize_ranks(self, ranks) -> list[tuple[int, int]]:
        sorted_by_rank = sorted(ranks, key=lambda x: x[1])
        next_tier = len(ranks)
        last_seen_rank = None
        tiers = defaultdict(list)

        for player_index in range(len(ranks) - 1, -1, -1):
            player_id, rank = sorted_by_rank[player_index]
            if rank != last_seen_rank:
                next_tier -= 1
            tiers[next_tier].append(player_id)
            last_seen_rank = rank

        sorted_tiers = sorted(tiers.keys())
        normalized_ranks = []

        top_tier = sorted_tiers.pop()
        for player_id in tiers[top_tier]:
            normalized_ranks.append((player_id, len(ranks)))

        for i, tier in enumerate(sorted_tiers):
            for player_id in tiers[tier]:
                normalized_ranks.append((player_id, i+1))

        return normalized_ranks

    def calculate(self, scores: list[tuple[int, int]]) -> dict[int, TourneyScore]:
        player_scores = {}
        for player_id, rank in scores:
            metascore = self.make_metascore(rank, [], rank)
            player_scores[player_id] = TourneyScore(
                player_id=player_id,
                tournament_score=metascore,
                game_score=rank,
                game_score_type='rank',
            )

        return player_scores


class RankFormula(Formula):
    def __init__(self, tournament: Tournament):
        super().__init__(tournament)
        self._inverse_rank = FormulaValue("Inverse Adjusted Rank")

        self.expression.set(self._inverse_rank * self.rank_multiplier * self.duration_multiplier)

    def set_values(self, inverse_rank: int, all_scores: list[float], this_score: float):
        self._inverse_rank.set(inverse_rank)