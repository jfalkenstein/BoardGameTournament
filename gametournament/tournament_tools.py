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
        loaded: Tournament = json.load(f, object_hook=decode_datetimes)
    return loaded

def encode_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()

def decode_datetimes(object_dict) -> Tournament:
    object_dict['start_date'] = datetime.fromisoformat(object_dict['start_date'])
    return object_dict