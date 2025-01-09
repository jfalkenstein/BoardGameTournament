import statistics

import click

from gametournament.base_scorer import BaseScorer
from gametournament.formula import Formula, FormulaValue
from gametournament.models import TourneyScore, Tournament, Player


class PointScorer(BaseScorer):
    def __init__(self, tournament: Tournament, players: list[Player], game_hours: float):
        super().__init__(tournament, players, game_hours, PointFormula(tournament))

    def score(self) -> dict[int, TourneyScore]:
        scores = [
            (player['id'], click.prompt(f"What was the score for player {player['name']}?", type=int))
            for player in self.players
        ]
        sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)
        return self.calculate(sorted_scores)

    def calculate(self, scores: list[tuple[int, float]]) -> dict[int, TourneyScore]:
        player_scores = {}
        current_inverse_rank = len(scores) + 1
        game_scores = [s[1] for s in scores]
        last_score = None
        last_points = None
        for player_id, points in scores:
            current_inverse_rank -= 1
            if points == last_points:
                player_scores[player_id] = TourneyScore(
                    player_id=player_id,
                    tournament_score=last_score,
                    game_score=int(points),
                    game_score_type='points'
                )
                continue

            last_points = points
            last_score = self.make_metascore(current_inverse_rank, game_scores, points)
            player_scores[player_id] = TourneyScore(player_id=player_id, tournament_score=last_score, game_score=points, game_score_type='points')
        return player_scores


class PointFormula(Formula):
    def __init__(self, tournament: Tournament):
        super().__init__(tournament)
        self._standard_deviations_from_mean = FormulaValue("Std. Deviations from Mean")
        self._inverse_rank = FormulaValue("Inverse Rank")

        self.expression.set(self._inverse_rank * self.rank_multiplier * self.duration_multiplier)
        if self.tournament['apply_bonus_or_penalty']:
            self._expression += self._standard_deviations_from_mean
        if self.tournament['participation_award'] > 0:
            self._expression += self.participation_award

    def set_values(self, inverse_rank: int, all_scores: list[float], this_score: float):
        self._inverse_rank.set(inverse_rank)
        std = statistics.stdev(all_scores)
        mean = statistics.mean(all_scores)
        dist_from_mean = this_score - mean
        self._standard_deviations_from_mean.set(dist_from_mean / std)
