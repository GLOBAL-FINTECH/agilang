import json
import time
from pathlib import Path

from agilang.translator import AGILTranslator
from agilang.web import (
    hash_password,
    html_response,
    json_response,
    render_template,
    sign_cookie,
    sqlite_db,
    verify_cookie,
    verify_password,
    web_app,
    web_get,
    web_post_json,
)


def test_web_route_json_response_and_params():
    app = web_app(debug=True)

    def profile(request):
        return json_response({"id": request.params["id"], "active": request.query.get("active")})

    app.get("/users/<id>", profile)
    server = app.listen("127.0.0.1", 0).run_background()
    try:
        payload = json.loads(web_get(server.url + "/users/42?active=1"))
        assert payload == {"id": "42", "active": "1"}
    finally:
        server.stop()


def test_web_post_json_body():
    app = web_app(debug=True)

    def create(request):
        payload = request.json({})
        return json_response({"amount": payload.get("amount"), "status": "accepted"}, status=201)

    app.post("/transactions", create)
    server = app.listen("127.0.0.1", 0).run_background()
    try:
        payload = json.loads(web_post_json(server.url + "/transactions", {"amount": 99.5}))
        assert payload["amount"] == 99.5
        assert payload["status"] == "accepted"
    finally:
        server.stop()


def test_template_cookie_password_helpers():
    assert render_template("<h1>{{ name }}</h1>", {"name": "A&B"}) == "<h1>A&amp;B</h1>"
    encoded = hash_password("secret")
    assert verify_password("secret", encoded)
    assert not verify_password("wrong", encoded)
    token = sign_cookie({"user_id": "u1"}, "dev-secret", max_age=60)
    assert verify_cookie(token, "dev-secret") == {"user_id": "u1"}
    assert verify_cookie(token, "wrong") is None


def test_static_files_and_sqlite(tmp_path: Path):
    static_dir = tmp_path / "public"
    static_dir.mkdir()
    (static_dir / "app.css").write_text("body{font-family:sans-serif}", encoding="utf-8")
    app = web_app(debug=True).static("/assets", static_dir)
    server = app.listen("127.0.0.1", 0).run_background()
    try:
        assert "font-family" in web_get(server.url + "/assets/app.css")
    finally:
        server.stop()

    db = sqlite_db(tmp_path / "app.db")
    db.execute("create table users(id integer primary key, name text)")
    db.execute("insert into users(name) values (?)", ["Ada"])
    assert db.one("select name from users where id = ?", [1])["name"] == "Ada"


def test_translator_exposes_web_functions():
    py = AGILTranslator().translate('fn main() -> i32:\n    let app = web_app("demo", True)\n    return 0\n')
    assert 'app = web_app("demo", True)' in py
