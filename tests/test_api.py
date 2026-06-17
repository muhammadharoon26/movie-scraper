"""API endpoint tests — auth, movies CRUD, and health."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.security import create_access_token
from tests.conftest import make_movie, make_scrape_log


# ── Auth ──────────────────────────────────────────────────


class TestLogin:
    def test_login_success(self, client: TestClient, test_user):
        resp = client.post(
            "/auth/login",
            json={"username": test_user.username, "password": "testpassword123"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        assert resp.json()["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, test_user):
        resp = client.post(
            "/auth/login", json={"username": test_user.username, "password": "wrong"}
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        resp = client.post(
            "/auth/login", json={"username": "ghost", "password": "irrelevant"}
        )
        assert resp.status_code == 401


class TestRegister:
    def test_register_success(self, client: TestClient, auth_headers):
        resp = client.post(
            "/auth/register",
            json={
                "username": f"new_{uuid.uuid4().hex[:8]}",
                "password": "securepass123",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert "hashed_password" not in resp.json()

    def test_register_duplicate(self, client: TestClient, auth_headers, test_user):
        resp = client.post(
            "/auth/register",
            json={"username": test_user.username, "password": "another123"},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    def test_register_without_auth(self, client: TestClient):
        resp = client.post(
            "/auth/register", json={"username": "noauth", "password": "password123"}
        )
        assert resp.status_code == 401


class TestJWTEnforcement:
    def test_no_token(self, client: TestClient):
        assert client.get("/movies").status_code == 401

    def test_invalid_token(self, client: TestClient):
        assert (
            client.get(
                "/movies", headers={"Authorization": "Bearer garbage"}
            ).status_code
            == 401
        )

    def test_expired_token(self, client: TestClient):
        token = create_access_token(
            subject=str(uuid.uuid4()), expires_delta=timedelta(seconds=-1)
        )
        assert (
            client.get(
                "/movies", headers={"Authorization": f"Bearer {token}"}
            ).status_code
            == 401
        )


# ── Movies ────────────────────────────────────────────────


class TestListMovies:
    def test_empty(self, client: TestClient, auth_headers):
        resp = client.get("/movies", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"] == []
        assert resp.json()["meta"]["total"] == 0

    def test_populated(self, client: TestClient, auth_headers, db_session: Session):
        make_movie(db_session, title="A", tmdb_id=10001)
        make_movie(db_session, title="B", tmdb_id=10002)
        resp = client.get("/movies", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    def test_pagination(self, client: TestClient, auth_headers, db_session: Session):
        for i in range(5):
            make_movie(db_session, title=f"M{i}", tmdb_id=20000 + i)
        resp = client.get("/movies?page=2&limit=2", headers=auth_headers)
        assert resp.status_code == 200
        meta = resp.json()["meta"]
        assert meta["page"] == 2
        assert meta["total"] == 5
        assert meta["total_pages"] == 3


class TestGetMovie:
    def test_found(self, client: TestClient, auth_headers, db_session: Session):
        movie = make_movie(db_session, title="Detail", tmdb_id=30001)
        resp = client.get(f"/movies/{movie.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Detail"

    def test_not_found(self, client: TestClient, auth_headers):
        assert (
            client.get(f"/movies/{uuid.uuid4()}", headers=auth_headers).status_code
            == 404
        )

    def test_soft_deleted(self, client: TestClient, auth_headers, db_session: Session):
        movie = make_movie(db_session, tmdb_id=30002)
        movie.deleted_at = datetime.now(timezone.utc)
        db_session.add(movie)
        db_session.flush()
        assert (
            client.get(f"/movies/{movie.id}", headers=auth_headers).status_code == 404
        )


class TestPatchMovie:
    def test_update_title(self, client: TestClient, auth_headers, db_session: Session):
        movie = make_movie(db_session, title="Old", tmdb_id=40001)
        resp = client.patch(
            f"/movies/{movie.id}", json={"title": "New"}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New"
        assert resp.json()["updated_at"] is not None

    def test_update_genres(self, client: TestClient, auth_headers, db_session: Session):
        movie = make_movie(db_session, tmdb_id=40002, genres=["Action"])
        resp = client.patch(
            f"/movies/{movie.id}", json={"genres": ["Comedy"]}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["genres"] == ["Comedy"]

    def test_empty_body(self, client: TestClient, auth_headers, db_session: Session):
        movie = make_movie(db_session, tmdb_id=40003)
        assert (
            client.patch(
                f"/movies/{movie.id}", json={}, headers=auth_headers
            ).status_code
            == 422
        )

    def test_not_found(self, client: TestClient, auth_headers):
        assert (
            client.patch(
                f"/movies/{uuid.uuid4()}", json={"title": "X"}, headers=auth_headers
            ).status_code
            == 404
        )


class TestDeleteMovie:
    def test_delete(self, client: TestClient, auth_headers, db_session: Session):
        movie = make_movie(db_session, tmdb_id=50001)
        assert (
            client.delete(f"/movies/{movie.id}", headers=auth_headers).status_code
            == 204
        )
        assert (
            client.get(f"/movies/{movie.id}", headers=auth_headers).status_code == 404
        )

    def test_not_found(self, client: TestClient, auth_headers):
        assert (
            client.delete(f"/movies/{uuid.uuid4()}", headers=auth_headers).status_code
            == 404
        )


# ── Health ────────────────────────────────────────────────


class TestHealth:
    def test_no_logs(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["last_scrape_at"] is None

    def test_with_log(self, client: TestClient, db_session: Session):
        make_scrape_log(db_session, status="success")
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["last_scrape_status"] == "success"

    def test_no_auth_required(self, client: TestClient):
        assert client.get("/health").status_code == 200
