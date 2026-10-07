from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.types import Message, Receive, Scope, Send

from app.db.dependencies import DbSession


@pytest.mark.parametrize(
    "failure,status",
    [(None, 200), ("http", 409), ("handler", 500), ("cleanup", 500)],
)
def test_request_session_lifecycle(
    app: FastAPI, failure: str | None, status: int
) -> None:
    sessions = [AsyncMock(spec=AsyncSession), AsyncMock(spec=AsyncSession)]
    for session in sessions:
        session.__aenter__.return_value = session
        session.__aexit__.return_value = False
        if failure == "cleanup":
            session.__aexit__.side_effect = RuntimeError("cleanup")
    factory = Mock(side_effect=sessions)
    used: list[AsyncSession] = []
    starts: list[int] = []

    @app.get("/probe")
    async def probe(session: DbSession, repeated: DbSession) -> dict[str, bool]:
        assert session is repeated
        used.append(session)
        if failure == "http":
            raise HTTPException(status_code=409, detail="Rejected")
        if failure == "handler":
            raise RuntimeError("probe")
        return {"same": True}

    async def observe(scope: Scope, receive: Receive, send: Send) -> None:
        async def checked_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                assert factory.call_count == len(starts) + 1
                sessions[len(starts)].__aexit__.assert_awaited_once()
                starts.append(message["status"])
            await send(message)

        await app(scope, receive, checked_send)

    with TestClient(observe, raise_server_exceptions=False) as client:
        app.state.session_factory = factory
        for _ in sessions:
            response = client.get("/probe")
            assert response.status_code == status
            if failure is None:
                assert response.json() == {"same": True}
            elif failure == "http":
                assert response.json() == {"detail": "Rejected"}
            else:
                assert response.text == "Internal Server Error"

    assert factory.call_count == 2
    assert used == sessions
    assert starts == [status, status]
    for session in sessions:
        session.__aenter__.assert_awaited_once_with()
        session.__aexit__.assert_awaited_once()
        session.commit.assert_not_awaited()
        error_type, error, _ = session.__aexit__.await_args.args
        if failure == "http":
            assert error_type is HTTPException
            assert error.status_code == 409
        elif failure == "handler":
            assert error_type is RuntimeError
            assert str(error) == "probe"
        else:
            assert error_type is None
