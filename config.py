"""
config.py — configuração do app, toda vinda de variáveis de ambiente.

DATABASE_URL, se definida, manda em tudo (útil para apontar para SQLite em
testes). Sem ela, a URI do MySQL é montada a partir das variáveis MYSQL_*,
com os padrões de desenvolvimento local.
"""

import os


class Config:
    SECRET_KEY = os.environ.get("RASTRO_SECRET_KEY", "rastro-dev-secret")

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "90873600144!55KM")
    MYSQL_DB = os.environ.get("MYSQL_DB", "rastrodb")

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
