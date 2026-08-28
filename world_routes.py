# world_routes.py
#
# Blueprint isolado do World interativo (PixiJS). Nenhuma rota, model ou
# import existente é alterado — este arquivo só é "ligado" ao app com duas
# linhas no app.py (ver instruções no final).
#
# Fase atual: Dia 1 — base do mundo (ilha, casa, céu vivo). O estado do
# mundo ainda é um stub fixo; no Dia 2 isso passa a vir do banco (tabela
# world_items que já existe em models.py).

from flask import Blueprint, jsonify, render_template
from flask_login import login_required, current_user  # ajuste o import se o
# projeto usa outro sistema de sessão (ex: session['user_id'] manual)

world_bp = Blueprint(
    "world_pixi",
    __name__,
    template_folder="templates",
    static_folder="static",
)


@world_bp.route("/world-novo")
@login_required
def world_novo():
    """Renderiza a nova versão interativa do World (PixiJS).
    Rota separada de /world para não conflitar com a página atual
    enquanto o novo mundo ainda está em teste.
    """
    return render_template("world_pixi.html")


@world_bp.route("/api/world/state")
@login_required
def world_state():
    """Retorna o estado atual do mundo do usuário.

    Formato pensado para ser fácil de estender no Dia 2 (itens comprados
    vindos da tabela world_items) sem quebrar o frontend:
    {
        "points": int,
        "items": [ { "type": str, "x": float, "y": float } ]
    }
    """
    # STUB temporário — Dia 2 troca isso por uma query real em WorldItem
    return jsonify({
        "points": getattr(current_user, "points", 0),
        "items": [],
    })


# ---------------------------------------------------------------------------
# Como ligar isso ao app.py (só isso, nada mais precisa mudar lá):
#
#   from world_routes import world_bp
#   app.register_blueprint(world_bp)
#
# Coloque essas duas linhas perto de onde outros blueprints (se houver) já
# são registrados, ou logo após a criação do `app = Flask(__name__)`.
# ---------------------------------------------------------------------------
