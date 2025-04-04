import functools
import sqlite3
import textwrap
from collections import defaultdict
from datetime import datetime
from typing import Iterable, Callable, Concatenate

import click
import yaml

from gametournament import db, tournament_tools
from gametournament.constants import DEFAULT_DURATION_MULTIPLIER, DEFAULT_RANK_MULTIPLIER
from gametournament.db import DB_FILE
from gametournament.models import TourneyScore, Player, Tournament
from gametournament.point_scorer import PointScorer, PointFormula
from gametournament.rank_scorer import RankScorer, RankFormula


def require_dbfile[**P, R](func: Callable[Concatenate[sqlite3.Connection, P], R]) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if not db.DB_FILE.exists():
            raise click.Abort("You need to run the init command!")
        with db.get_connection() as connection:
            return func(connection, *args,  **kwargs)
    return wrapper

def require_current_tournament[**P, R](func: Callable[Concatenate[Tournament, P], R]) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        tournament = tournament_tools.get_current_tournament()
        if tournament is None:
            raise click.Abort("No currently selected tournament")
        return func(tournament, *args, **kwargs)
    return wrapper

@click.group()
def cli():
    """This is a CLI Tool for creating and running rankings for a Board Game Tournament.

    It creates a "meta-score" for each game, whether there are points for the game or only
    just a set of rankings.

    Rather than being an "elimination" tournament, it calculates an average meta-score across
    all games.

    In order to run a tournament, you need to run the "init" command to set up the database.
    After that, you can use the "add-scores" command
    """
    pass


@cli.command(short_help="Sets up the tournament database.")
def init():
    click.echo("Setting up tournament...")
    if DB_FILE.exists():
        click.confirm("This will replace the current database. Are you sure you want to proceed?", abort=True)

    with db.get_connection() as connection:
        db.create_tables(connection)

@cli.group(short_help="Commands related to tournaments")
def tournament():
    pass

@tournament.command(short_help="Creates a new tournament")
@click.argument("name")
@click.option(
    '-r',
    '--rank-multiplier',
    type=click.FLOAT,
    default=DEFAULT_RANK_MULTIPLIER,
    show_default=True,
    help="Multiplier to apply to the INVERSE rank for a game",
    prompt=True
)
@click.option(
    '-d',
    '--duration-multiplier',
    type=click.FLOAT,
    default=DEFAULT_DURATION_MULTIPLIER,
    show_default=True,
    help="Multiplier to apply to the number of game hours. Set this to 0 if you don't want to apply duration bonus.",
    prompt=True,
)
@click.option(
    '--bonus/--no-bonus',
    default=True,
    show_default=True,
    help="Whether to apply a bonus or penalty to metascores on basis of standard deviations from average",
    prompt=True,
)
@require_dbfile
def new(
    connection: sqlite3.Connection,
    name: str,
    rank_multiplier: float,
    duration_multiplier: float,
    bonus: bool,
):
    tournament = Tournament(
        name=name,
        start_date=datetime.now(),
        rank_multiplier=rank_multiplier,
        duration_multiplier=duration_multiplier,
        apply_bonus_or_penalty=bonus,
    )
    tournament = db.create_tournament(connection, tournament)
    players = []
    while True:
        player = click.prompt("Enter player name or hit enter if finished", default="", show_default=False)
        if player.strip() == "":
            break
        players.append(player)
    db.insert_players(connection, tournament['id'], players)
    tournament_tools.set_current_tournament(tournament)

@tournament.command(short_help="Gets current tournament info")
@require_dbfile
@require_current_tournament
def get(tournament: Tournament, connection: sqlite3.Connection):
    click.echo("Current Tournament:")
    click.echo("-" * 20)
    as_yaml = yaml.dump(tournament)
    indented = textwrap.indent(as_yaml, '>> ')
    click.echo(indented)
    click.echo("Tournament Players:")
    click.echo("-" * 20)
    players = db.get_players(connection, tournament['id'])
    for player in players:
        click.echo(f">> {player['name']}")

@tournament.command(short_help="Selects a pre-existing tournament as the current tournament")
@require_dbfile
def select(connection: sqlite3.Connection):
    tournaments = db.get_tournaments(connection)
    tournament_map = {}
    tournament_selection = "Select tournament by id\n"

    if len(tournaments) == 0:
        click.echo("No tournaments to select")
        raise click.Abort()

    for tournament in tournaments:
        tournament_map[tournament['id']] = tournament
        tournament_selection += f'* {tournament["start_date"]}\tID: {tournament["id"]}\t{tournament["name"]}\n'

    tournament_selection_lines = tournament_selection.splitlines()
    if len(tournament_selection_lines) > 10:
        click.echo_via_pager(tournament_selection_lines)
    else:
        click.echo(tournament_selection)

    tournament_id = click.prompt("Which id do you want to select?", type=click.INT)
    tournament = tournament_map[tournament_id]
    click.echo(f"Setting tournament named \"{tournament["name"]}\" as current tournament.")
    tournament_tools.set_current_tournament(tournament)

@tournament.command(short_help="Adds a player to a tournament")
@click.argument("player-name")
@require_dbfile
@require_current_tournament
def add_player(tournament: Tournament, connection: sqlite3.Connection, player_name):
    player_name = player_name.strip()
    if player_name == "":
        raise click.Abort("Invalid player name!")

    db.insert_players(connection, tournament['id'], [player_name])
    click.echo(f"Player {player_name} added to tournament: {tournament['name']}")

@tournament.command(short_help="Displays the scoring formulae for the tournament")
@require_current_tournament
def show_formulae(tournament: Tournament):
    point_formula = PointFormula(tournament, 1).show()
    rank_formula = RankFormula(tournament, 1).show()
    click.echo(f"Metascore formula for point-based games:\n\t{point_formula}")
    click.echo(f"\nMetascore formula for rank-based games:\n\t{rank_formula}")

@cli.group(short_help="Commands for working with scores")
def scores():
    pass

@scores.command(short_help="Adds scores for a game")
@require_dbfile
@require_current_tournament
def record(tournament: Tournament, connection: sqlite3.Connection):
    all_players = db.get_players(connection, tournament['id'])

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
        scorer = PointScorer(tournament, players, hours)
    else:
        scorer = RankScorer(tournament, players, hours)

    scores = scorer.score()
    formula = scorer.get_formula()

    click.echo(f"Metascore formula:\n\t{formula}")

    player_lookup = {player['id']: player['name'] for player in players}
    click.echo(f"\n{'-' * 20}\nHere are the meta-scores for that game:")
    pretty_print_game_scores(player_lookup, scores.values())

    click.confirm(f"\n{'-' * 20}\nDo you want to record these scores?", default=True, abort=True)

    db.record_scores(connection, tournament['id'], game, hours, scores.values())
    current_totals = db.get_scores(connection, tournament['id'])

    output_scores(current_totals)


def pretty_print_game_scores(player_lookup: dict[int, str], scores: Iterable[TourneyScore]):
    pretty_scores = {player_lookup[score['player_id']]: score for score in scores}
    for key, value in pretty_scores.items():
        click.echo(f"{key} ->  {value['tournament_score']}")


@scores.command(short_help="Gets the current rankings/scores for the tournament")
@require_dbfile
@require_current_tournament
def get(tournament: Tournament, connection: sqlite3.Connection):
    current_totals = db.get_scores(connection, tournament['id'])
    output_scores(current_totals)


@tournament.command(short_help="Gets ALL scores currently entered for the tournament")
@require_dbfile
@require_current_tournament
def log(tournament: Tournament, connection: sqlite3.Connection):
    records = db.get_all_records(connection, tournament['id'])

    for record in records:
        string = ""
        for key, value in dict(record).items():
            string += f"| {key}: {value} "
        click.echo(string)


@scores.command(short_help="Recalculate all scores")
@require_dbfile
@require_current_tournament
def recalc(tournament: Tournament, connection: sqlite3.Connection):
    records = db.get_all_records(connection, tournament['id'])

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
            scorer = PointScorer(tournament, players, games_to_hours[game])
        else:
            scorer = RankScorer(tournament, players, games_to_hours[game])
        new_scores[game] = scorer.recalculate(scores)

    for game, scores in new_scores.items():
        click.echo(f"\n-----\nHere's the score for game {game}")
        pretty_print_game_scores(player_lookup, scores)

    click.confirm(f"\n{'-' * 20}\nDo you want to record these scores?", default=True, abort=True)

    with connection:
        for game, scores in new_scores.items():
            db.update_scores(connection, scores)

        current_totals = db.get_scores(connection, tournament['id'])
        output_scores(current_totals)


def output_scores(current_totals):
    click.echo(f"\n{'-' * 20}\nHere are the running total scores:")
    for player, score, game_count, avg_score in current_totals:
        click.echo(f'{player["name"]} -> avg: {round(avg_score, 3)}, total: {round(score, 3)}, games: {game_count}')




if __name__ == '__main__':
    cli.main()
