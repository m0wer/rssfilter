from app.main import app
import uuid


class TestSignupUser:
    def test_register_user(self, client):
        response = client.post(
            app.url_path_for("register_user"),
        )

        assert response.status_code == 201
        assert response.json()["user_id"]
        assert isinstance(response.json()["user_id"], str)
        # check its valid uuid4
        uuid.UUID(response.json()["user_id"], version=4)


class TestSignupProcessOPML:
    def test_process_opml_valid(self, client):
        response = client.post(
            app.url_path_for("process_opml"),
            files={"opml": ("test.opml", open("tests/data/test.opml", "rb"))},
        )

        assert response.status_code == 200
        assert response.text
        assert "xmlUrl" in response.text
        assert "rssfilter" in response.text
        assert "ycombinator" in response.text
