# world_routes.py
#
# Blueprint isolado do World interativo (PixiJS). Nenhuma rota, model ou
# import existente em app.py é alterado — este arquivo só é "ligado" ao app
# com duas linhas (ver instruções no final).
#
# Segue o mesmo esquema de sessão manual do app.py (session["user_id"]),
# sem depender de flask_login.
#
# Fase atual: Dia 1 — base do mundo (ilha, casa, céu vivo). O estado do
# mundo ainda é um stub fixo; no Dia 2 isso passa a vir do banco (tabela
# world_items que já existe em models.py).

from functools import wraps

from flask import Blueprint, jsonify, redirect, render_template, session, url_for

from models import User, db

world_bp = Blueprint(
    "world_pixi",
    __name__,
    template_folder="templates",
)


def _current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def _login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("landing", tab="login"))
        return view(*args, **kwargs)

    return wrapped


@world_bp.route("/world-novo")
@_login_required
def world_novo():
    """Renderiza a nova versão interativa do World (PixiJS).
    Rota separada de /world para não conflitar com a página atual
    enquanto o novo mundo ainda está em teste.
    """
    return render_template("world_pixi.html")


@world_bp.route("/api/world/state")
@_login_required
def world_state():
    """Retorna o estado atual do mundo do usuário.

    Formato pensado para ser fácil de estender no Dia 2 (itens comprados
    vindos da tabela world_items) sem quebrar o frontend:
    {
        "points": int,
        "items": [ { "type": str, "x": float, "y": float } ]
    }
    """
    user = _current_user()
    # STUB temporário — Dia 2 troca isso por uma query real em WorldItem
    return jsonify({
        "points": user.points if user else 0,
        "items": [],
    })


# ---------------------------------------------------------------------------
# Como ligar isso ao app.py (só isso, nada mais precisa mudar lá):
#
#   from world_routes import world_bp
#   app.register_blueprint(world_bp)
#
# Coloque essas duas linhas logo depois de `db.init_app(app)`.
# ---------------------------------------------------------------------------
