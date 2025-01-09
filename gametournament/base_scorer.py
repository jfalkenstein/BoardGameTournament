from __future__ import annotations
import statistics
from abc import ABC, abstractmethod
from typing import Self

from jedi.inference.gradual.typing import Callable
from pygments.token import Other

from gametournament.formula import Formula
from gametournament.models import TourneyScore, Player, Tournament


class BaseScorer(ABC):
    def __init__(self, tournament: Tournament, players: list[Player], game_hours: float, formula:  Formula):
        self.tournament = tournament
        self.players = players
        self.game_hours = game_hours
        self.formula = formula

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

    def make_metascore(self, inverse_rank: int, all_scores: list[float], this_score: float):
        return self.formula.compute(inverse_rank, all_scores, this_score)


    def get_formula(self) -> str:
        return self.formula.show()

