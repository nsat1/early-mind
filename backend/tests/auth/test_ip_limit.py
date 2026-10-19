import hashlib
import hmac

import pytest
from fastapi.testclient import TestClient
from redis import Redis as SyncRedis

from app.core.config import Settings

pytestmark = pytest.mark.integration

LOGOUT_URL = "/api/v1/auth/logout"
LIMIT = 30
PAUSE_SECONDS = 15 * 60


def test_auth_requests_are_limited_per_address(client: TestClient) -> None:
    for _ in range(LIMIT):
        assert client.post(LOGOUT_URL).status_code == 204

    response = client.post(LOGOUT_URL)

    assert response.status_code == 429
    assert response.json()["detail"] == "Too many requests"
    assert PAUSE_SECONDS - 60 < int(response.headers["retry-after"]) <= PAUSE_SECONDS


def test_address_is_stored_as_keyed_hash(
    client: TestClient, settings: Settings, redis_store: SyncRedis
) -> None:
    assert client.post(LOGOUT_URL).status_code == 204

    secret = settings.auth_secret.get_secret_value().encode()
    digest = hmac.new(secret, b"testclient", hashlib.sha256).hexdigest()
    assert redis_store.keys("rate:*") == [f"rate:{digest}"]
    assert not any("testclient" in key for key in redis_store.keys())


def test_cross_site_requests_do_not_use_limit(client: TestClient) -> None:
    for _ in range(LIMIT):
        response = client.post(LOGOUT_URL, headers={"Origin": "https://evil.example"})
        assert response.status_code == 403

    assert client.post(LOGOUT_URL).status_code == 204


def test_account_requests_are_not_limited(client: TestClient) -> None:
    for _ in range(LIMIT + 1):
        assert client.get("/api/v1/account").status_code == 401
