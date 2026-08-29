"""
routes — um blueprint por área do app.

auth      login, cadastro, logout e entrada do administrador
main      home, TALK, 1%, SECRET, PERFIL, atualizar informações e as APIs
world     WORLD: a ilha (PixiJS), o Mundo Real e /api/world/*
admin     painel /admin
volunteer voluntariado: chat do usuário e painel do voluntário
db_sync   /admin/sync-db, sincroniza models.py com o banco
"""

from routes.admin import bp as admin_bp
from routes.auth import bp as auth_bp
from routes.db_sync import bp as db_sync_bp
from routes.main import bp as main_bp
from routes.volunteer import bp as volunteer_bp
from routes.world import bp as world_bp

ALL = (auth_bp, main_bp, world_bp, admin_bp, volunteer_bp, db_sync_bp)


def register(app):
    """Liga todos os blueprints no app."""
    for bp in ALL:
        app.register_blueprint(bp)
