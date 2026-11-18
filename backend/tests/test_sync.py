"""Site clients and incremental synchronisation, with fake transports."""
from __future__ import annotations

from sqlalchemy import func, select

from app.core.models import Account, Game
from app.services import jobs
from app.services.games import sync
from app.services.games.sources import chesscom_game, lichess_game
from tests.conftest import pgn


def test_chesscom_game_conversion():
    item = {
        "url": "https://www.chess.com/game/live/1", "uuid": "u-1", "rules": "chess",
        "time_class": "blitz", "rated": True, "end_time": 1760000000,
        "white": {"username": "Me", "rating": 1510}, "black": {"username": "Opp", "rating": 1490},
        "pgn": pgn("Me", "Opp", "1-0", "1. e4 {[%clk 0:02:59]} e5 {[%clk 0:02:58]} 2. Nf3"),
    }
    raw = chesscom_game(item)
    assert raw.platform == "chesscom" and raw.external_id == "u-1"
    assert raw.moves == ["e4", "e5", "Nf3"]
    assert (raw.white_elo, raw.time_class, raw.rated) == (1510, "blitz", True)
    assert raw.played_at.year == 2025
    assert chesscom_game({**item, "rules": "chess960"}) is None


def test_lichess_game_conversion():
    item = {
        "id": "abcd1234", "rated": True, "variant": "standard", "speed": "rapid",
        "createdAt": 1760000000000, "status": "resign", "winner": "black",
        "players": {"white": {"user": {"name": "Opp"}, "rating": 1600},
                    "black": {"user": {"name": "Me"}, "rating": 1650}},
        "moves": "d4 d5 c4",
    }
    raw = lichess_game(item)
    assert (raw.result, raw.black, raw.black_elo, raw.time_class) == ("0-1", "Me", 1650, "rapid")
    assert raw.url == "https://lichess.org/abcd1234"
    assert lichess_game({**item, "variant": "chess960"}) is None
    assert lichess_game({**item, "winner": None, "status": "draw"}).result == "1/2-1/2"
    assert lichess_game({**item, "winner": None, "status": "aborted"}).result == "*"


class FakeChesscom:
    def __init__(self, months: dict[str, list]):
        self.months = months
        self.fetched: list[str] = []

    def archives(self, username):
        return [(m, m) for m in sorted(self.months)]

    def games(self, url):
        self.fetched.append(url)
        yield from (chesscom_game(g) for g in self.months[url])


def _cc(uid: str, moves: str = "1. e4 e5") -> dict:
    return {"uuid": uid, "url": f"https://chess.com/{uid}", "rules": "chess", "time_class": "rapid",
            "white": {"username": "me", "rating": 1500}, "black": {"username": "x", "rating": 1500},
            "pgn": pgn("me", "x", "1-0", moves)}


def test_chesscom_sync_is_incremental(db_session):
    account = Account(platform="chesscom", username="me")
    db_session.add(account)
    db_session.commit()
    client = FakeChesscom({"2026/09": [_cc("a")], "2026/10": [_cc("b")]})
    state = jobs.JobState(kind="sync")

    assert len(sync.sync_chesscom(db_session, account, state, client)) == 2
    assert account.sync_cursor == "2026/10"

    # Next sync: only the last month is read again, and only new games are stored.
    client.months["2026/10"].append(_cc("c"))
    client.months["2026/11"] = [_cc("d")]
    client.fetched.clear()
    assert len(sync.sync_chesscom(db_session, account, state, client)) == 2
    assert client.fetched == ["2026/10", "2026/11"]
    assert db_session.scalar(select(func.count(Game.id))) == 4


def test_first_sync_can_be_limited_in_months(db_session, monkeypatch):
    account = Account(platform="chesscom", username="me")
    db_session.add(account)
    db_session.commit()
    monkeypatch.setattr(sync, "_months_ago", lambda months, now=None: "2026/10")
    client = FakeChesscom({"2025/01": [_cc("old")], "2026/10": [_cc("new")]})
    sync.sync_chesscom(db_session, account, jobs.JobState(kind="sync"), client, months=1)
    assert client.fetched == ["2026/10"]


class FakeLichess:
    def __init__(self, items):
        self.items = items
        self.since = None

    def games(self, username, since_ms=None):
        self.since = since_ms
        for item in self.items:
            if since_ms is None or item["createdAt"] > since_ms:
                yield lichess_game(item), item["createdAt"]


def _li(gid: str, created: int) -> dict:
    return {"id": gid, "variant": "standard", "speed": "blitz", "createdAt": created, "status": "mate",
            "winner": "white", "moves": "e4 e5 Qh5",
            "players": {"white": {"user": {"name": "me"}, "rating": 1500},
                        "black": {"user": {"name": "x"}, "rating": 1500}}}


def test_lichess_sync_resumes_after_the_last_game(db_session):
    account = Account(platform="lichess", username="me")
    db_session.add(account)
    db_session.commit()
    client = FakeLichess([_li("g1", 1000), _li("g2", 2000)])
    state = jobs.JobState(kind="sync")
    assert len(sync.sync_lichess(db_session, account, state, client)) == 2
    assert account.sync_cursor == "2000"

    client.items.append(_li("g3", 3000))
    assert len(sync.sync_lichess(db_session, account, state, client)) == 1
    assert client.since == 2000
    assert db_session.scalar(select(Game.my_result).where(Game.external_id == "g3")) == "win"


def test_months_ago():
    from datetime import datetime

    assert sync._months_ago(1, datetime(2026, 1, 15)) == "2025/12"
    assert sync._months_ago(12, datetime(2026, 11, 18)) == "2025/11"
