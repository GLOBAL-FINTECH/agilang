from pathlib import Path

from agilang.scaffold import create_project
from agilang.ml import ml_linear_regression, ml_predict_linear, ml_dataset_summary


def test_web_starter_uses_laravel_style_structure(tmp_path: Path) -> None:
    result = create_project('Professional Web', directory=tmp_path, template='web', force=True)
    root = result.root
    expected = [
        'config/app.agi',
        'config/database.agi',
        'config/auth.agi',
        'routes/web.agi',
        'routes/api.agi',
        'app/controllers/BaseController.agi',
        'app/controllers/HomeController.agi',
        'app/controllers/AuthController.agi',
        'app/controllers/DashboardController.agi',
        'app/controllers/ApiController.agi',
        'database/migrations.agi',
        'resources/views/home.ags',
        'resources/views/demo.ags',
        'resources/views/dashboard.ags',
        'resources/views/auth/login.ags',
        'resources/views/auth/register.ags',
        'resources/views/auth/forgot_password.ags',
        'resources/views/auth/reset_password.ags',
        'src/ml.agi',
        'docs/WEB_FRAMEWORK_STRUCTURE.md',
        'docs/ML_DATA_ANALYSIS.md',
    ]
    for relative in expected:
        assert (root / relative).exists(), relative
    main = (root / 'src/main.agi').read_text(encoding='utf-8')
    assert 'import "../routes/web.agi"' in main
    assert 'register_web_routes(app, app_db)' in main
    assert 'register_api_routes(app, app_db)' in main
    assert '/api/ml/demo' in (root / 'routes/api.agi').read_text(encoding='utf-8')


def test_web_starter_routes_are_not_defined_inline_only(tmp_path: Path) -> None:
    root = create_project('Routes App', directory=tmp_path, template='web', force=True).root
    main = (root / 'src/main.agi').read_text(encoding='utf-8')
    routes = (root / 'routes/web.agi').read_text(encoding='utf-8')
    assert 'app.get("/", home_page' not in main
    assert 'app.get("/", home_page' in routes
    assert 'app.get("/login", login_page' in routes
    assert 'app.post("/register", register_post' in routes


def test_dependency_free_ml_helpers_work() -> None:
    rows = [{'x': 1, 'y': 2}, {'x': 2, 'y': 4}, {'x': 3, 'y': 6}]
    summary = ml_dataset_summary(rows)
    assert summary['rows'] == 3
    model = ml_linear_regression(rows, 'y', ['x'])
    assert round(model['weights']['x'], 6) == 2.0
    assert round(ml_predict_linear(model, {'x': 10}), 6) == 20.0
