from httpx import AsyncClient


async def test_register_then_login_then_me(client: AsyncClient):
    """The `client` fixture already registered+logged in "test@example.com"
    (conftest.py) - verifies /me reflects that same session, then exercises
    register/login for a second, distinct user explicitly.
    """
    me_response = await client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "test@example.com"

    register_response = await client.post(
        "/api/auth/register", json={"email": "second@example.com", "password": "secondpass123"}
    )
    assert register_response.status_code == 201
    assert register_response.json()["email"] == "second@example.com"

    login_response = await client.post(
        "/api/auth/token", data={"username": "second@example.com", "password": "secondpass123"}
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


async def test_register_duplicate_email_returns_400(client: AsyncClient):
    response = await client.post(
        "/api/auth/register", json={"email": "test@example.com", "password": "testpass123"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


async def test_login_with_wrong_password_returns_401(client: AsyncClient):
    response = await client.post(
        "/api/auth/token", data={"username": "test@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401


async def test_create_workflow_without_token_succeeds(client: AsyncClient):
    """Workflow routes no longer require auth (see the module docstring in
    app/api/routes/workflows.py) - the frontend never got a login UI built
    for the JWT system exercised by the other tests in this file, so every
    mutating call from a real browser session 401'd unconditionally. The
    auth system itself (register/login/me, above) is untouched and still
    works; it's just no longer required for these routes.
    """
    client.headers.pop("Authorization", None)
    response = await client.post(
        "/api/workflows", json={"repository_url": "https://github.com/example/project", "goal": "Audit SEO"}
    )
    assert response.status_code == 201


async def test_get_workflow_remains_public(client: AsyncClient):
    """GET endpoints (workflow status, findings, SSE events) are
    deliberately left unauthenticated in this phase - see
    review/CHANGELOG.md Phase 10 notes on scope. A 404 (not 401) for a
    random id confirms the route didn't reject for lack of auth.
    """
    import uuid

    response = await client.get(f"/api/workflows/{uuid.uuid4()}")
    assert response.status_code == 404
