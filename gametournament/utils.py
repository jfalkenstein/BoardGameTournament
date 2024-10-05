
import statistics
from functools import lru_cache

@lru_cache()
def calculate_mean_and_std(all_game_scores):
    mean = statistics.mean(all_game_scores)
    std = statistics.stdev(all_game_scores, mean)
    return mean, std


def calculate_bonus(all_game_scores: list[float], this_game_score: float) -> float:
    mean, std = calculate_mean_and_std(tuple(all_game_scores))
    dist_from_mean = this_game_score - mean
    deviations_from_mean = dist_from_mean / std
    return deviations_from_mean


def calculate_score(current_inverse_rank: int, duration_multiplier: int, bonus: float):
    return max((2 * current_inverse_rank * duration_multiplier) + bonus, 1)