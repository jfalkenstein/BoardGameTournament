from __future__ import annotations
import statistics
from abc import ABC, abstractmethod
from typing import Self

from jedi.inference.gradual.typing import Callable
from pygments.token import Other

from gametournament.models import TourneyScore, Player, Tournament


class BaseScorer(ABC):
    def __init__(self, tournament: Tournament, players: list[Player], game_hours: float):
        self.tournament = tournament
        self.players = players
        self.game_hours = game_hours
        self._formula = Formula(tournament)

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
        return self._formula.calculate(inverse_rank, all_scores, this_score)
        # score = self.tournament['rank_multiplier'] * inverse_rank
        # duration_multiplier = self.tournament['duration_multiplier'] * self.game_hours
        # if duration_multiplier != 0:
        #     score *= duration_multiplier
        # if self.tournament['apply_bonus_or_penalty']:
        #     mean = statistics.mean(all_scores)
        #     std = statistics.stdev(all_scores, mean)
        #     distance_from_mean = this_score - mean
        #     deviations_from_mean = distance_from_mean / std
        #     score += deviations_from_mean
        # return score

    def get_formula(self):
        return self._formula.show()
        # formula = f"({{Rank multiplier: {self.tournament['rank_multiplier']}}} x {{inverse rank}}"
        # if self.tournament['duration_multiplier'] != 0:
        #     formula += f" x {{Duration multiplier: {self.tournament['duration_multiplier']}}} * {{Game Hours:{self.game_hours}}}"
        # formula += ")"
        # if self.tournament['apply_bonus_or_penalty']:
        #     formula += f" +/- {{# Standard deviations from avg score/rank}}"
        #
        # return formula

class FormulaNode:
    __match_args__ = ("text",)
    def __init__(self, text: str):
        self.text = text

    def __eq__(self, other) -> bool:
        return self.text == other.text

class FormulaOp(FormulaNode):
    def __init__(self, text: str, op_func: Callable[[float, float], float]):
        super().__init__(text)
        self.op_func = op_func

class FormulaValue(FormulaNode):
    __match_args__ = ("text", "value")
    def __init__(self, text: str, value: float | int = None):
        super().__init__(text)
        self.value = value

    def __add__(self, other: FormulaNode) -> Expression:
        return Expression(self, Add, other)
    def __sub__(self, other: FormulaNode) -> Expression:
        return Expression(self, Subtract, other)

    def __mul__(self, other) -> Expression:
        return Expression(self, Multiply, other)

    def __truediv__(self, other) -> Expression:
        return Expression(self, Divide, other)

class Expression(FormulaNode):
    __match_args__ = ("text",)

    def __init__(self, *nodes: FormulaNode):
        self.nodes = list(nodes)
        self._text = None

    @property
    def operator(self) -> FormulaOp | None:
        if len(self.nodes) > 1 and isinstance(self.nodes[1], FormulaOp):
            return self.nodes[1]

        return None

    def __add__(self, other: FormulaValue | Expression) -> Expression:
        return self._operate(Add, other)

    def __sub__(self, other: FormulaValue | Expression) -> Expression:
        return self._operate(Subtract, other)

    def __mul__(self, other: FormulaValue | Expression) -> Expression:
        return self._operate(Multiply, other)

    def __truediv__(self, other: FormulaValue | Expression) -> Expression:
        return self._operate(Divide, other)

    def _operate(self, op: FormulaOp, other: FormulaValue | Expression) -> Expression:
        if isinstance(other, FormulaValue) and self.operator == op:
            self.nodes.extend([Add, other])
            return self
        elif isinstance(other, (Expression, FormulaValue)):
            return Expression(self, op, other)


    @property
    def text(self) -> str:
        if self._text is not None:
            return self._text

        string = ""
        for node in self.nodes:
            match node:
                case FormulaValue(text, None):
                    string += f'{{{text}}} '
                case FormulaValue(text, value):
                    string += f"{{{text}:{value}}} "
                case FormulaOp(text):
                    string += f"{text} "
                case Expression(text):
                    string += f'({text}) '
                case _:
                    raise TypeError("Unexpected node type!")
        return string.strip()

    @text.setter
    def text(self, value: str):
        self._text = value

    @property
    def value(self) -> float:
        current_value: float = 0
        current_op: Callable[[float, float], float] | None = None
        for node in self.nodes:
            match node:
                case FormulaValue(text, None):
                    raise ValueError(f"Cannot calculate value for None value '{text}'")
                case FormulaValue(_, value) if current_op is None:
                    current_value = value
                case FormulaValue(_, value) if current_op is not None:
                    current_value = current_op(current_value, value)
                    current_op = None
                case Expression() if current_op is None:
                    current_value = node.value
                case Expression() if current_op is not None:
                    current_value = current_op(current_value, node.value)
                    current_op = node.value
                case FormulaOp():
                    current_op = node.op_func
                case _:
                    raise TypeError("Unexpected node type!")
        return current_value

Add = FormulaOp("+", lambda x, y: x + y)
Subtract = FormulaOp("-", lambda x, y: x - y)
Multiply = FormulaOp("x", lambda x, y: x * y)
Divide = FormulaOp("÷", lambda x, y: x / y)

class Formula:
    def __init__(self, tournament: Tournament):
        self._tournament = tournament
        self._rank_multiplier = FormulaValue("Rank Multiplier", tournament['rank_multiplier'])
        self._participation_award = FormulaValue("Participation Award", tournament['participation_award'])
        self._duration_multiplier = FormulaValue("Duration Multiplier", tournament['duration_multiplier'])

        # These need values set
        self._inverse_rank = FormulaValue("Inverse Rank")
        self._standard_deviations_from_mean = FormulaValue("Std. Deviations from Mean")

        self._expression = self._rank_multiplier * self._inverse_rank * self._duration_multiplier
        if self._tournament['apply_bonus_or_penalty']:
            self._expression += self._standard_deviations_from_mean
        if self._tournament['participation_award'] > 0:
            self._expression += self._participation_award

    def reset(self):
        self._inverse_rank.value = None
        self._standard_deviations_from_mean.value = None

    def calculate(self, inverse_rank: int, all_scores: list[float], this_score: float):
        self.reset()
        self._inverse_rank.value = inverse_rank
        mean = statistics.mean(all_scores)
        std = statistics.stdev(all_scores)
        distance_from_mean = this_score - mean
        self._standard_deviations_from_mean.value = distance_from_mean / std
        return self._expression.value

    def show(self) -> str:
        self.reset()
        return self._expression.text