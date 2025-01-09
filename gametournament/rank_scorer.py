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
        sorted_by_rank = sorted(ranks, key=lambda x: x[1])

        next_rank = len(sorted_by_rank) + 1
        last_seen_rank = None
        for i in range(len(ranks) - 1, 0, -1):
            player_id, rank = sorted_by_rank[i]
            if rank == last_seen_rank:
                sorted_by_rank[i] = (player_id, next_rank)
            else:
                next_rank -= 1
                sorted_by_rank[i] = (player_id, next_rank)
                last_seen_rank = rank
        return self.calculate(sorted_by_rank)

    def calculate(self, scores: list[tuple[int, float]]) -> dict[int, TourneyScore]:
        player_scores = {}
        ranks_as_scores = [r[1] * 10 for r in scores]
        last_score = None
        last_rank = None
        for player_id, rank in scores:
            if rank == last_rank:
                player_scores[player_id] = TourneyScore(
                    player_id=player_id,
                    tournament_score=last_score,
                    game_score=last_rank,
                    game_score_type='rank',
                )
                continue

            last_rank = rank
            inverse_rank = len(self.players) - int(rank) + 1
            last_score = self.make_metascore(inverse_rank, ranks_as_scores, inverse_rank)
            player_scores[player_id] = TourneyScore(
                player_id=player_id,
                tournament_score=last_score,
                game_score=last_rank,
                game_score_type='rank',
            )
        return player_scores


class RankFormula(Formula):
    def __init__(self, tournament: Tournament):
        super().__init__(tournament)
        self._inverse_rank = FormulaValue("Inverse Normalized Rank")

        self.expression.set(self._inverse_rank * self.rank_multiplier * self.duration_multiplier)

    def set_values(self, inverse_rank: int, all_scores: list[float], this_score: float):
        self._inverse_rank.set(inverse_rank)