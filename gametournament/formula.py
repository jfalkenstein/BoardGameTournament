from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable, Self

from gametournament.models import Tournament


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
        self._value = value
        # If we instantiate this with a value, it means it's not resettable.
        self.is_immutable = value is not None

    @property
    def value(self) -> float | None:
        return self._value

    def set(self, value: float):
        if self.is_immutable:
            raise ValueError(f"You cannot set a value on {self.text}; It's immutable")
        self._value = value

    def reset(self):
        if not self.is_immutable:
            self._value = None

    def __add__(self, other: FormulaNode) -> Expression:
        return Expression(self, Add, other)

    def __sub__(self, other: FormulaNode) -> Expression:
        return Expression(self, Subtract, other)

    def __mul__(self, other) -> Expression:
        return Expression(self, Multiply, other)

    def __truediv__(self, other) -> Expression:
        return Expression(self, Divide, other)


class Expression:
    __match_args__ = ("text",)

    def __init__(self, *nodes: FormulaNode | Self):
        self.nodes = list(nodes)
        self._text = None

    @property
    def operator(self) -> FormulaOp | None:
        if len(self.nodes) > 1 and isinstance(self.nodes[1], FormulaOp):
            return self.nodes[1]

        return None

    def set(self, *nodes: FormulaNode | Self):
        if len(nodes) == 1 and isinstance(nodes[0], Expression):
            nodes = nodes[0].nodes

        self.nodes = list(nodes)

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
            self.nodes.extend([op, other])
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

    def compute(self) -> float:
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
                    current_value = node.compute()
                case Expression() if current_op is not None:
                    current_value = current_op(current_value, node.value)
                    current_op = None
                case FormulaOp():
                    current_op = node.op_func
                case _:
                    raise TypeError("Unexpected node type!")
        return current_value

    def reset(self):
        for node in self.nodes:
            if isinstance(node, (Expression, FormulaValue)):
                node.reset()


Add = FormulaOp("+", lambda x, y: x + y)
Subtract = FormulaOp("-", lambda x, y: x - y)
Multiply = FormulaOp("x", lambda x, y: x * y)
Divide = FormulaOp("÷", lambda x, y: x / y)


class Formula(ABC):

    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        self.rank_multiplier = FormulaValue("Rank Multiplier", tournament['rank_multiplier'])
        self.duration_multiplier = FormulaValue("Duration Multiplier", tournament['duration_multiplier'])

        self._expression = Expression()

    @property
    def expression(self) -> Expression:
        return self._expression

    @abstractmethod
    def set_values(self, inverse_rank: int, all_scores: list[float], this_score: float):
        """Implement this to set up the various expression node values"""

    def compute(self, inverse_rank: int, all_scores: list[float], this_score: float) -> float:
        self.reset()
        self.set_values(inverse_rank, all_scores, this_score)
        return self.expression.compute()

    def reset(self):
        self.expression.reset()

    def show(self) -> str:
        self.reset()
        return self.expression.text