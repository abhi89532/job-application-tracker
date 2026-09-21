import sqlite3

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test",
            "DATABASE": str(tmp_path / "test.db"),
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


def valid_application(**changes):
    data = {
        "company": "Example Corp",
        "position": "Python Developer",
        "status": "Applied",
        "application_date": "2026-09-20",
        "job_url": "https://example.com/jobs/1",
        "location": "Remote",
        "notes": "Submitted through company website.",
    }
    data.update(changes)
    return data


def test_empty_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"No applications found" in response.data


def test_add_and_search_application(client):
    response = client.post("/applications/new", data=valid_application(), follow_redirects=True)
    assert response.status_code == 200
    assert b"Application added successfully" in response.data
    assert b"Example Corp" in response.data

    response = client.get("/?q=Python")
    assert b"Example Corp" in response.data
    response = client.get("/?q=Missing")
    assert b"No applications found" in response.data


def test_validation_rejects_bad_input(client):
    response = client.post(
        "/applications/new",
        data=valid_application(company="", job_url="example.com"),
    )
    assert response.status_code == 200
    assert b"Company is required" in response.data
    assert b"Job URL must begin" in response.data


def test_edit_and_delete_application(app, client):
    client.post("/applications/new", data=valid_application())
    response = client.post(
        "/applications/1/edit",
        data=valid_application(status="Interview", notes="Phone screen booked."),
        follow_redirects=True,
    )
    assert b"Application updated successfully" in response.data
    assert b"Interview" in response.data
    assert b"Phone screen booked" in response.data

    response = client.post("/applications/1/delete", follow_redirects=True)
    assert b"Application deleted" in response.data
    assert b"No applications found" in response.data

    with sqlite3.connect(app.config["DATABASE"]) as db:
        assert db.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 0


def test_status_filter(client):
    client.post("/applications/new", data=valid_application(status="Applied"))
    client.post(
        "/applications/new",
        data=valid_application(company="Second Corp", status="Offer"),
    )
    response = client.get("/?status=Offer")
    assert b"Second Corp" in response.data
    assert b"Example Corp" not in response.data
