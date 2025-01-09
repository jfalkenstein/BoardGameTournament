import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

from gametournament.models import TourneyScore, Tournament, Player

DB_FILE = Path(__file__).parent.parent / "tournament.db"


def get_connection():
    connection = sqlite3.connect(str(DB_FILE), detect_types=True)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables(connection: sqlite3.Connection):
    cursor = connection.cursor()

    cursor.execute("DROP TABLE IF EXISTS tournaments;")
    cursor.execute("""
        CREATE TABLE tournaments (
            id integer PRIMARY KEY,
            name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            rank_multiplier REAL NOT NULL,
            duration_multiplier REAL NOT NULL,
            apply_bonus_or_penalty BOOLEAN NOT NULL,
            participation_award REAL NOT NULL
        );
    """)

    cursor.execute("DROP TABLE IF EXISTS players;")
    cursor.execute(
        """
        CREATE TABLE players (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            tournament_id INTEGER NOT NULL,
            FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
        );
        """
    )

    cursor.execute("DROP TABLE IF EXISTS scores")
    cursor.execute("""
        CREATE TABLE scores (
            score_id INTEGER PRIMARY KEY,
            game TEXT NOT NULL,
            hours REAL NOT NULL,
            player_id INTEGER NOT NULL,
            score REAL NOT NULL,
            points_or_rank INTEGER NOT NULL,
            game_score_type TEXT NOT NULL,
            tournament_id INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
        );
    """)

def insert_players(connection: sqlite3.Connection, tournament_id: int, player_names: list[str]):
    cursor = connection.cursor()
    cursor.executemany("""
        INSERT INTO players(name, tournament_id)
        VALUES (?, ?)
    """, [(name, tournament_id) for name in player_names])

def create_tournament(connection: sqlite3.Connection, tournament: Tournament) -> Tournament:
    cursor = connection.cursor()
    sql = """
    INSERT INTO tournaments(
        name, 
        start_date, 
        rank_multiplier, 
        duration_multiplier, 
        apply_bonus_or_penalty,
        participation_award
    ) 
    VALUES (?, ?, ?, ?, ?, ?) 
    RETURNING id;
    """
    params = (
        tournament['name'],
        tournament['start_date'],
        tournament['rank_multiplier'],
        tournament['duration_multiplier'],
        tournament['apply_bonus_or_penalty'],
        tournament['participation_award']
    )
    cursor.execute(sql, params)
    result = cursor.fetchone()
    tournament['id'] = result['id']
    return tournament

def get_tournaments(connection: sqlite3.Connection) -> list[Tournament]:
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM tournaments ORDER BY start_date DESC;")
    results: list[sqlite3.Row] = cursor.fetchall()
    tournaments = [Tournament(result) for result in results]
    return tournaments


def get_players(connection: sqlite3.Connection, tournament_id: int) -> list[Player]:
    cursor = connection.cursor()
    cursor.execute("SELECT id, name FROM players WHERE tournament_id = ?;", (tournament_id,))
    rows: list[sqlite3.Row] = cursor.fetchall()
    players = [Player(r) for r in rows]
    return players


def record_scores(connection: sqlite3.Connection, tournament_id: int, game: str, hours: float, scores: Iterable[TourneyScore]):
    cursor = connection.cursor()
    params = [
        (game, hours, score['player_id'], score['tournament_score'], tournament_id, score['game_score'], score['game_score_type'])
        for score in scores
    ]
    query = """
        INSERT INTO scores(game, hours, player_id, score, tournament_id, points_or_rank, game_score_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    cursor.executemany(query, params)


def get_scores(connection: sqlite3.Connection, tournament_id: int) -> list[tuple[Player, float, int, float]]:
    query = """
    SELECT p.id, 
        p.name, 
        sum(coalesce(s.score, 0)) as total_score, 
        coalesce(count(s.score_id), 0) as game_count, 
        coalesce(sum(s.score)/count(s.score_id), 0) as average_score
    FROM players as p
    LEFT JOIN scores as s ON s.player_id = p.id
    WHERE p.tournament_id = ?
    GROUP BY p.id, p.name
    ORDER BY average_score desc
    """
    cursor = connection.cursor()
    cursor.execute(query, (tournament_id,))
    results = []
    for row in cursor:
        player = Player(id=row[0], name=row[1])
        results.append((player, row[2], row[3], row[4]))

    return results


def get_all_records(connection: sqlite3.Connection, tournament_id: int) -> list[sqlite3.Row]:
    query = """
        SELECT players.name, scores.* 
        FROM scores
        JOIN players ON scores.player_id = players.id
        WHERE players.tournament_id = ?;
    """
    cursor = connection.cursor()
    cursor.execute(query, (tournament_id,))
    return cursor.fetchall()


def update_scores(connection: sqlite3.Connection, scores: list[TourneyScore]):
    query = """
        UPDATE scores SET score = ? WHERE score_id = ?;
    """
    cursor = connection.cursor()
    for score in scores:
        cursor.execute(query, [score['tournament_score'], score['score_id']])