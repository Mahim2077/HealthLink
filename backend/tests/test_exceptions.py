from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.exceptions import HealthLinkError
from app.main import create_app


def test_expected_application_error_uses_standard_detail_shape(
    test_settings: Settings,
) -> None:
    application: FastAPI = create_app(test_settings)

    @application.get("/_test/expected-error")
    def expected_error() -> None:
        raise HealthLinkError("Expected conflict", status_code=409)

    with TestClient(application) as client:
        response = client.get("/_test/expected-error")

    assert response.status_code == 409
    assert response.json() == {"detail": "Expected conflict"}
