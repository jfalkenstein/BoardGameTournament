from abc import ABC, abstractmethod

from gametournament.constants import HOURS_PER_INCREMENT
from gametournament.db import Player
from gametournament.models import TourneyScore


class BaseScorer(ABC):
    def __init__(self, players: list[Player], game_hours: float):
        self.players = players
        self.duration_multiplier = max((game_hours // HOURS_PER_INCREMENT), 1)

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
