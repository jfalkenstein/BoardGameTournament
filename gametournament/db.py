import sqlite3
from pathlib import Path
from typing import TypedDict, Iterable

from gametournament.models import TourneyScore

DB_FILE = Path(__file__).parent.parent / "tournament.db"


def get_connection():
    connection = sqlite3.connect(str(DB_FILE), detect_types=True)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables(connection: sqlite3.Connection, players: list[str]):
    cursor = connection.cursor()
    cursor.execute("DROP TABLE IF EXISTS players;")
    cursor.execute(
        """
        CREATE TABLE if not exists players (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        """
    )

    cursor.executemany(f"INSERT INTO players(id, name) VALUES (NULL, ?)", [(p,) for p in players])
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
            FOREIGN KEY (player_id) REFERENCES players(id)
        );
    """)


class Player(TypedDict):
    id: int
    name: str


def get_players(connection: sqlite3.Connection) -> list[Player]:
    cursor = connection.cursor()
    cursor.execute("SELECT id, name FROM players;")
    rows: list[sqlite3.Row] = cursor.fetchall()
    players = [Player(r) for r in rows]
    return players


def record_scores(connection: sqlite3.Connection, game: str, hours: float, scores: Iterable[TourneyScore]):
    cursor = connection.cursor()
    params = [
        (game, hours, score['player_id'], score['tournament_score'], score['game_score'])
        for score in scores
    ]
    query = """
        INSERT INTO scores(game, hours, player_id, score, points_or_rank)
        VALUES (?, ?, ?, ?, ?)
    """
    cursor.executemany(query, params)


def get_scores(connection: sqlite3.Connection) -> list[tuple[Player, float, int, float]]:
    query = """
    SELECT p.id, p.name, sum(s.score) as total_score, count(*) as game_count, sum(s.score)/count(*) as average_score
    FROM players as p
    JOIN scores as s ON s.player_id = p.id
    GROUP BY p.id, p.name
    ORDER BY average_score desc
    """
    cursor = connection.cursor()
    cursor.execute(query)
    results = []
    for row in cursor:
        player = Player(id=row[0], name=row[1])
        results.append((player, row[2], row[3], row[4]))

    return results


def get_all_records(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    query = """
        SELECT players.name, scores.* FROM scores
        JOIN players ON scores.player_id = players.id;
    """
    cursor = connection.cursor()
    cursor.execute(query)
    return cursor.fetchall()


def update_scores(connection: sqlite3.Connection, scores: list[TourneyScore]):
    query = """
        UPDATE scores SET score = ? WHERE score_id = ?;
    """
    cursor = connection.cursor()
    for score in scores:
        cursor.execute(query, [score['tournament_score'], score['score_id']])