from typing import TypedDict, Literal, NotRequired


class TourneyScore(TypedDict):
    player_id: int
    game_score: int
    tournament_score: float
    game_score_type: Literal['points', 'rank']
    score_id: NotRequired[int]


