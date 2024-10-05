from datetime import datetime
from typing import TypedDict, Literal, NotRequired


class TourneyScore(TypedDict):
    player_id: int
    game_score: int | float
    tournament_score: float
    game_score_type: Literal['points', 'rank']
    score_id: NotRequired[int]


class Tournament(TypedDict):
    name: str
    start_date: datetime
    id: int
    rank_multiplier: int | float
    duration_multiplier: int | float
    apply_bonus_or_penalty: bool

class Player(TypedDict):
    id: int
    name: str
