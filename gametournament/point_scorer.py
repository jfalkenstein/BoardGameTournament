import statistics

import click

from gametournament import utils
from gametournament.constants import HOURS_PER_INCREMENT
from gametournament.models import TourneyScore, Player
from gametournament.base_scorer import BaseScorer

class PointScorer(BaseScorer):

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
        mean, std = utils.calculate_mean_and_std(tuple(game_scores))
        click.echo(f"Standard deviation: {std}; Mean: {mean}")
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
            bonus = utils.calculate_bonus(game_scores, points)
            last_score = utils.calculate_score(current_inverse_rank, self.duration_multiplier, bonus)
            player_scores[player_id] = TourneyScore(player_id=player_id, tournament_score=last_score, game_score=points, game_score_type='points')
        click.echo(
            f"Formula: (2 * inverse rank * {self.duration_multiplier} {{duration_multiplier}}) + {{std deviations from avg}}"
        )
        return player_scores




