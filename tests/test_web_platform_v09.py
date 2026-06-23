from agilang.web import (
    auth_required,
    csrf_protect,
    csrf_token,
    html_response,
    integer,
    job_queue,
    json_response,
    login_user,
    migrate,
    model,
    sqlite_db,
    string,
    validate,
    web_app,
    web_get,
    web_post_json,
    wsgi_adapter,
)


def test_orm_model_and_migration(tmp_path):
    db = sqlite_db(tmp_path / "app.db")
    User = model("User", {"id": integer(primary_key=True, nullable=False), "email": string(nullable=False, unique=True), "name": string()})

    def create_users(db):
        User.create_table(db)

    applied = migrate(db, [("001_create_users", create_users)])
    assert applied == ["001_create_users"]
    assert migrate(db, [("001_create_users", create_users)]) == []
    user = User(email="a@example.com", name="Ada").save(db)
    assert user.id
    assert User.where(db, email="a@example.com").first().name == "Ada"


def test_validation_schema():
    result = validate({"email": "bad", "age": "12"}, {"email": "required|email", "age": "required|int"})
    assert not result.ok
    assert result.errors["email"] == ["email"]
    good = validate({"email": "ok@example.com", "age": "12"}, {"email": "required|email", "age": "int"})
    assert good.ok
    assert good.data["age"] == 12


def test_middleware_groups_auth_and_csrf():
    secret = "testing-secret"
    app = web_app("secure", True)
    app.middleware_group("secure", [auth_required(secret), csrf_protect(secret)])

    def login(request):
        return login_user(json_response({"ok": True}), {"id": 7, "email": "a@example.com"}, secret)

    def update(request):
        return json_response({"user": request.user, "ok": True})

    app.post("/login", login)
    app.post("/update", update, middleware="secure")
    server = app.listen("127.0.0.1", 0).run_background()
    try:
        import urllib.request
        import json
        login_req = urllib.request.Request(server.url + "/login", data=b"{}", headers={"Content-Type":"application/json"}, method="POST")
        with urllib.request.urlopen(login_req, timeout=5) as resp:
            cookie = resp.headers["Set-Cookie"].split(";", 1)[0]
        token = csrf_token(secret)
        update_req = urllib.request.Request(server.url + "/update", data=json.dumps({"_csrf": token}).encode(), headers={"Content-Type":"application/json", "Cookie": cookie}, method="POST")
        with urllib.request.urlopen(update_req, timeout=5) as resp:
            assert b'"ok":true' in resp.read().replace(b" ", b"")
    finally:
        server.stop()


def test_job_queue_runs_jobs():
    q = job_queue(workers=1)
    job_id = q.enqueue(lambda x: x + 1, 4)
    import time
    for _ in range(20):
        status = q.status(job_id)
        if status["status"] == "done":
            break
        time.sleep(0.05)
    assert q.status(job_id)["result"] == 5
    q.stop()


def test_wsgi_adapter():
    app = web_app("wsgi", True)
    app.get("/", lambda request: html_response("ok"))
    wsgi = wsgi_adapter(app)
    captured = {}
    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers
    body = b"".join(wsgi({"PATH_INFO":"/", "QUERY_STRING":"", "REQUEST_METHOD":"GET", "CONTENT_LENGTH":"0", "wsgi.input": __import__('io').BytesIO(b"")}, start_response))
    assert captured["status"].startswith("200")
    assert body == b"ok"
