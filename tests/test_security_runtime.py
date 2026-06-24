from agilang.security import api_key_hash, hmac_sign, hmac_verify, verify_api_key
from agilang.web import Request, WebApp, sign_cookie, verify_cookie


def test_api_key_hash_uses_unique_salt_and_verifies():
    encoded_a = api_key_hash("sample-api-key")
    encoded_b = api_key_hash("sample-api-key")

    assert encoded_a != encoded_b
    assert verify_api_key("sample-api-key", encoded_a)
    assert not verify_api_key("different-key", encoded_a)


def test_hmac_verify_accepts_only_matching_message():
    signature = hmac_sign("payload", "test-key")

    assert hmac_verify("payload", "test-key", signature)
    assert not hmac_verify("other-payload", "test-key", signature)


def test_signed_cookie_requires_matching_signing_key():
    token = sign_cookie({"user_id": "123"}, "test-key", max_age=60)

    assert verify_cookie(token, "test-key") == {"user_id": "123"}
    assert verify_cookie(token, "different-key") is None


def test_static_file_parent_path_is_forbidden(tmp_path):
    public = tmp_path / "public"
    public.mkdir()
    (public / "index.html").write_text("ok", encoding="utf-8")
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside", encoding="utf-8")

    app = WebApp()
    app.static("/static", public)

    request = Request(
        method="GET",
        path="/static/../outside.txt",
        query_string="",
        headers={},
        body=b"",
    )
    response = app.handle(request)

    assert response.status == 403


def test_web_app_debug_false_hides_exception_detail():
    app = WebApp(debug=False)

    def failing_route(_request):
        raise RuntimeError("internal detail")

    app.get("/boom", failing_route)
    response = app.handle(Request(method="GET", path="/boom", query_string="", headers={}, body=b""))

    assert response.status == 500
    assert response.body == "Internal Server Error"
