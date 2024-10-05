import statistics
from abc import ABC, abstractmethod

from gametournament.constants import HOURS_PER_INCREMENT
from gametournament.models import TourneyScore, Player, Tournament


class BaseScorer(ABC):
    def __init__(self, tournament: Tournament, players: list[Player], game_hours: float):
        self.tournament = tournament
        self.players = players
        self.game_hours = game_hours

    @abstractmethod
    def score(self) -> dict[int, TourneyScore]: ...

    @abstractmethod
    def calculate(self, scores: list[tuple[int, float]]) -> dict[int, TourneyScore]: ...

    def recalculate(self, scores: list[TourneyScore]):
        scores_to_calc_with = [(t['player_id'], t['game_score']) for t in scores]
        result = self.calculate(scores_to_calc_with)
        for score in scores:
            result_score = result[score['player_id']]['tournament_score']
            score['tournament_score'] = result_score

        return scores

    def make_score(self, inverse_rank: int, all_scores: list[float], this_score: float):
        score = self.tournament['rank_multiplier'] * inverse_rank
        duration_multiplier = self.tournament['duration_multiplier'] * self.game_hours
        if duration_multiplier != 0:
            score *= duration_multiplier
        if self.tournament['apply_bonus_or_penalty']:
            mean = statistics.mean(all_scores)
            std = statistics.stdev(all_scores, mean)
            distance_from_mean = this_score - mean
            deviations_from_mean = distance_from_mean / std
            score += deviations_from_mean
        return score

    def get_formula(self):
        formula = f"( {{Rank multiplier: {self.tournament['rank_multiplier']}}} x {{inverse rank}}"
        if self.tournament['duration_multiplier'] != 0:
            formula += f" x {{Duration multiplier: {self.tournament['duration_multiplier']}}} * {{Game Hours:{self.game_hours}}}"
        formula += " )"
        if self.tournament['apply_bonus_or_penalty']:
            formula += f" +/- {{# Standard deviations from avg score/rank}}"

        return formula