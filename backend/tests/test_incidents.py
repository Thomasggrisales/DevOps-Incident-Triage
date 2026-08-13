import pytest

from conftest import auth_headers

from app.db import models
from app.core import security


def test_get_incidents_requires_auth(client):
    assert client.get("/incidents/").status_code == 401


def test_get_incidents_invalid_token(client):
    assert client.get("/incidents/", headers=auth_headers("token-falso")).status_code == 401


def test_get_incidents_inactive_user(client, user_factory):
    user = user_factory(active=False)
    token = security.create_access_token(subject=user.id)
    r = client.get("/incidents/", headers=auth_headers(token))
    assert r.status_code == 401


def test_get_incidents_valid_token_empty(client, access_token):
    r = client.get("/incidents/", headers=auth_headers(access_token))
    assert r.status_code == 200
    assert r.json() == []


def test_stats_requires_auth(client):
    assert client.get("/incidents/stats/").status_code == 401


def test_stats_with_data(client, access_token, session):
    session.add_all([
        models.Incident(title="A", description="a", source="prometheus", severity="critical", status="resolved"),
        models.Incident(title="B", description="b", source="prometheus", severity="high", status="open"),
    ])
    session.commit()

    r = client.get("/incidents/stats/", headers=auth_headers(access_token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert body["by_severity"]["critical"] == 1
    assert body["by_status"]["open"] == 1


def test_get_single_incident_requires_auth(client):
    assert client.get("/incidents/1").status_code == 401


def test_search_requires_auth(client):
    assert client.get("/incidents/search/", params={"q": "algo"}).status_code == 401


@pytest.mark.parametrize("path", ["/incidents/", "/incidents/stats/", "/incidents/search/", "/incidents/1"])
def test_incident_endpoints_need_bearer(client, path):
    r = client.get(path if "search" not in path else path, params={"q": "x"} if "search" in path else None)
    assert r.status_code == 401
