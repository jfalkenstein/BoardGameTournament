import statistics

import click

from gametournament import utils
from gametournament.base_scorer import BaseScorer
from gametournament.constants import HOURS_PER_INCREMENT
from gametournament.models import TourneyScore, Player


class RankScorer(BaseScorer):

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
        mean, std = utils.calculate_mean_and_std(tuple(ranks_as_scores))
        click.echo(f"Standard deviation of (ranks * 10): {std}; Mean: {mean}")
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
            bonus = utils.calculate_bonus(ranks_as_scores, inverse_rank)
            last_score = utils.calculate_score(inverse_rank, self.duration_multiplier, bonus)
            player_scores[player_id] = TourneyScore(
                player_id=player_id,
                tournament_score=last_score,
                game_score=last_rank,
                game_score_type='rank',
            )

        click.echo(
            f"Formula: (2 * {{inverse rank}} * {self.duration_multiplier} {{duration_multiplier}}) + {{std deviations from avg}}"
        )
        return player_scores
