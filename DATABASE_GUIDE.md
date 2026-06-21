# Database Guide

## SQLite

```agi
const DB_PATH = os.environ.get("DATABASE_PATH", "../storage/app.sqlite")

fn db():
    ensure_dir("../storage")
    return sqlite_db(DB_PATH)
```

## MySQL

```agi
let app_db = mysql_db(
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DATABASE
)
```

## Query Methods

```agi
app_db.execute(sql, params)
app_db.one(sql, params)
app_db.query(sql, params)
```

## CLI MySQL Migrations

```bash
agilang db create
agilang db table create users --columns "name:VARCHAR(255),email:VARCHAR(255) UNIQUE"
agilang db migrate
agilang db status
```
