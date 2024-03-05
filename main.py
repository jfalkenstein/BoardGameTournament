from collections import defaultdict
from typing import Iterable

import click
import sqlite3
from gametournament import db
from gametournament.db import Player
from gametournament.models import TourneyScore
from gametournament.point_scorer import PointScorer
from gametournament.rank_scorer import RankScorer


@click.group()
def cli():
    pass


@cli.command()
def init():
    click.echo("Setting up tournament...")
    players = []
    while True:
        player = click.prompt("Enter player name or hit enter if finished", default="", show_default=False)
        if player.strip() == "":
            break
        players.append(player)

    with db.get_connection() as connection:
        db.create_tables(connection, players)


@cli.command()
def add_scores():
    if not db.DB_FILE.exists():
        raise RuntimeError("You need to run the init command!")

    with db.get_connection() as connection:
        all_players = db.get_players(connection)

    game = click.prompt("What game was it?")
    hours = click.prompt("How many hours did you play it?", type=float)
    if click.confirm("Did all players play?", default=True):
        players = all_players
    else:
        players = []
        for player in all_players:
            if click.confirm(f"Did {player['name']} play?"):
                players.append(player)

    if click.confirm("Did the game have points?", default=True):
        scorer = PointScorer(players, hours)
    else:
        scorer = RankScorer(players, hours)

    scores = scorer.score()
    player_lookup = {player['id']: player['name'] for player in players}
    click.echo(f"\n{'-' * 20}\nHere are the scores for that game:")
    pretty_print_game_scores(player_lookup, scores.values())

    click.confirm(f"\n{'-' * 20}\nDo you want to record these scores?", default=True, abort=True)

    with connection:
        db.record_scores(connection, game, hours, scores.values())
        current_totals = db.get_scores(connection)

    output_scores(current_totals)


def pretty_print_game_scores(player_lookup: dict[int, str], scores: Iterable[TourneyScore]):
    pretty_scores = {player_lookup[score['player_id']]: score for score in scores}
    for key, value in pretty_scores.items():
        click.echo(f"{key} ->  {value['tournament_score']}")


@cli.command()
def get_scores():
    with db.get_connection() as connection:
        current_totals = db.get_scores(connection)

    output_scores(current_totals)


@cli.command()
def log():
    with db.get_connection() as connection:
        records = db.get_all_records(connection)

    for record in records:
        string = ""
        for key, value in dict(record).items():
            string += f"| {key}: {value} "
        click.echo(string)


@cli.command()
def recalc():
    with db.get_connection() as connection:
        records = db.get_all_records(connection)

    player_lookup = {}
    games_to_hours = {}
    scores_by_game = defaultdict(list)
    for record in records:
        scores_by_game[record['game']].append(TourneyScore(
            player_id=record['player_id'],
            game_score=record['points_or_rank'],
            tournament_score=record['score'],
            game_score_type=record['game_score_type'],
            score_id=record['score_id']
        ))
        player_lookup[record['player_id']] = record['name']
        games_to_hours[record['game']] = record['hours']

    new_scores = {}
    for game, scores in scores_by_game.items():
        players = [
            Player(id=score['player_id'], name=player_lookup[score['player_id']])
            for score in scores
        ]
        if scores[0]['game_score_type'] == 'points':
            scorer = PointScorer(players, games_to_hours[game])
        else:
            scorer = RankScorer(players, games_to_hours[game])
        new_scores[game] = scorer.recalculate(scores)

    for game, scores in new_scores.items():
        click.echo(f"\n-----\nHere's the score for game {game}")
        pretty_print_game_scores(player_lookup, scores)

    click.confirm(f"\n{'-' * 20}\nDo you want to record these scores?", default=True, abort=True)

    with connection:
        for game, scores in new_scores.items():
            db.update_scores(connection, scores)

        current_totals = db.get_scores(connection)
        output_scores(current_totals)


def output_scores(current_totals):
    click.echo(f"\n{'-' * 20}\nHere are the running total scores:")
    for player, score, game_count, avg_score in current_totals:
        click.echo(f'{player["name"]} -> avg: {avg_score}, total: {score}, games: {game_count}')


if __name__ == '__main__':
    cli.main()