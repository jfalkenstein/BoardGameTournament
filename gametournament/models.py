from datetime import datetime
from typing import TypedDict, Literal, NotRequired


class TourneyScore(TypedDict):
    player_id: int
    game_score: int
    tournament_score: float
    game_score_type: Literal['points', 'rank']
    score_id: NotRequired[int]


class Tournament(TypedDict):
    name: str
    start_date: datetime
    id: int

class Player(TypedDict):
    id: int
    name: str
