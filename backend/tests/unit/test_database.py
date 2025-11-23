from contextlib import contextmanager

import pytest
import src.database as database


pytestmark = pytest.mark.unit


class DummyAsyncSession:
    def __init__(self, should_raise: bool = False) -> None:
        self.should_raise = should_raise
        self.executed = False
        self.rolled_back = False
        self.closed = False

    async def execute(self, *_args, **_kwargs):
        self.executed = True
        if self.should_raise:
            raise RuntimeError("execute failed")

    async def rollback(self):
        self.rolled_back = True

    async def close(self):
        self.closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
        return False


class DummySyncSession:
    def __init__(self) -> None:
        self.rolled_back = False
        self.closed = False

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


@pytest.mark.asyncio
async def test_get_async_session_raises_when_not_configured(monkeypatch):
    monkeypatch.setattr(database, "_get_engines", lambda: (None, None, None, None))

    with pytest.raises(RuntimeError):
        async with database.get_async_session():
            pass


@pytest.mark.asyncio
async def test_get_async_session_success_and_cleanup(monkeypatch):
    dummy = DummyAsyncSession()

    def fake_get_engines():
        return None, None, (lambda: dummy), None

    monkeypatch.setattr(database, "_get_engines", fake_get_engines)

    async with database.get_async_session() as session:
        assert session is dummy
        await session.execute("SELECT 1")

    assert dummy.executed is True
    assert dummy.closed is True
    assert dummy.rolled_back is False


@pytest.mark.asyncio
async def test_get_async_session_rollback_on_error(monkeypatch):
    dummy = DummyAsyncSession()

    def fake_get_engines():
        return None, None, (lambda: dummy), None

    monkeypatch.setattr(database, "_get_engines", fake_get_engines)

    with pytest.raises(RuntimeError):
        async with database.get_async_session() as _session:
            raise RuntimeError("boom")

    assert dummy.rolled_back is True
    assert dummy.closed is True


def test_get_sync_session_raises_when_not_configured(monkeypatch):
    monkeypatch.setattr(database, "_get_engines", lambda: (None, None, None, None))

    with pytest.raises(RuntimeError):
        with database.get_sync_session():
            pass


def test_get_sync_session_success_and_cleanup(monkeypatch):
    dummy = DummySyncSession()

    def fake_get_engines():
        return None, None, None, (lambda: dummy)

    monkeypatch.setattr(database, "_get_engines", fake_get_engines)

    with database.get_sync_session() as session:
        assert session is dummy

    assert dummy.closed is True
    assert dummy.rolled_back is False


def test_get_sync_session_rollback_on_error(monkeypatch):
    dummy = DummySyncSession()

    def fake_get_engines():
        return None, None, None, (lambda: dummy)

    monkeypatch.setattr(database, "_get_engines", fake_get_engines)

    with pytest.raises(RuntimeError):
        with database.get_sync_session() as _session:
            raise RuntimeError("boom")

    assert dummy.rolled_back is True
    assert dummy.closed is True


def test_provide_sync_session_wraps_get_sync_session(monkeypatch):
    @contextmanager
    def fake_get_sync_session():
        yield "SESSION"

    monkeypatch.setattr(database, "get_sync_session", fake_get_sync_session)

    gen = database.provide_sync_session()
    assert next(gen) == "SESSION"
    with pytest.raises(StopIteration):
        next(gen)


@pytest.mark.asyncio
async def test_check_database_connection_returns_false_when_not_configured(monkeypatch):
    monkeypatch.setattr(database, "_get_engines", lambda: (None, None, None, None))

    result = await database.check_database_connection()

    assert result is False


@pytest.mark.asyncio
async def test_check_database_connection_true_on_success(monkeypatch):
    dummy = DummyAsyncSession()

    def fake_get_engines():
        return None, None, (lambda: dummy), None

    monkeypatch.setattr(database, "_get_engines", fake_get_engines)

    result = await database.check_database_connection()

    assert result is True
    assert dummy.executed is True
    assert dummy.closed is True


@pytest.mark.asyncio
async def test_check_database_connection_returns_false_on_error(monkeypatch):
    dummy = DummyAsyncSession(should_raise=True)

    def fake_get_engines():
        return None, None, (lambda: dummy), None

    monkeypatch.setattr(database, "_get_engines", fake_get_engines)

    result = await database.check_database_connection()

    assert result is False
    assert dummy.closed is True


class DummyConn:
    def __init__(self) -> None:
        self.run_sync_called = False

    async def run_sync(self, _fn):
        self.run_sync_called = True


class DummyEngineContext:
    def __init__(self, conn: DummyConn) -> None:
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyEngine:
    def __init__(self) -> None:
        self.conn = DummyConn()

    def begin(self):
        return DummyEngineContext(self.conn)


@pytest.mark.asyncio
async def test_create_tables_raises_when_not_configured(monkeypatch):
    monkeypatch.setattr(database, "_get_engines", lambda: (None, None, None, None))

    with pytest.raises(RuntimeError):
        await database.create_tables()


@pytest.mark.asyncio
async def test_create_tables_runs_with_engine(monkeypatch):
    engine = DummyEngine()

    def fake_get_engines():
        return engine, None, None, None

    monkeypatch.setattr(database, "_get_engines", fake_get_engines)

    await database.create_tables()

    assert engine.conn.run_sync_called is True
