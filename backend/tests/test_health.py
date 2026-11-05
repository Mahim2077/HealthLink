from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "HealthLink Test",
        "environment": "test",
    }
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "SAMEORIGIN"
    assert response.headers["referrer-policy"] == "same-origin"
    assert response.headers["permissions-policy"] == "geolocation=(self), camera=(), microphone=()"
    assert response.headers["content-security-policy"] == (
        "base-uri 'self'; form-action 'self'; frame-ancestors 'self'"
    )


def test_health_endpoint_allows_configured_frontend_origin(
    client: TestClient,
) -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"
