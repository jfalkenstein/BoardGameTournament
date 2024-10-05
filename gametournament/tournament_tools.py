import json
from datetime import datetime
from pathlib import Path

from gametournament.models import Tournament

TOURNAMENT_FILE = Path(__file__).parent.parent / "tournament-context.json"

def set_current_tournament(tournament: Tournament):
    with TOURNAMENT_FILE.open(mode="w") as f:
        json.dump(tournament, f, default=encode_datetime)

def get_current_tournament() -> Tournament:
    if not TOURNAMENT_FILE.exists():
        raise RuntimeError("Tournament context file doesn't exist. You must set the current tournament")

    with TOURNAMENT_FILE.open(mode="r") as f:
        return json.load(f)


def encode_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
