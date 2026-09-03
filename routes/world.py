"""
routes/world.py — tudo do WORLD em um lugar só.

O WORLD tem uma única implementação: a cena interativa em PixiJS
(static/js/world.js + static/css/world.css). A versão antiga, desenhada
só com CSS, foi removida.

Este blueprint concentra:
  * /world                              → a cena do mundo (Pixi) + progresso
  * /world/mundo-real                   → mapa do Mundo Real
  * /world/mundo-real/questionario      → escolha de interesses
  * /api/world/state                    → estado do mundo (JSON)
  * /api/world/buy                      → compra de um elemento
  * /api/world/mundo-real/interacao     → curtir/salvar um lugar

Depende só de models/data/helpers, nunca de app.py — por isso não existe
import circular. O registro acontece em routes/__init__.py.
"""

import json
from datetime import datetime

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from helpers import current_user, login_required, owned_costs_for, unlock
from models import WorldItem, WorldRealInteraction, WorldRealPreference, db
from data import (
    BENEFITS,
    WORLD_ELEMENT_MESSAGES,
    WORLD_ELEMENTS,
    WORLD_REAL_INTERESTS,
    WORLD_REAL_PLACES,
    unlocked_elements,
    world_progress,
)

bp = Blueprint("world", __name__)


# ---------------- estado do mundo ----------------

def world_state_for(user):
    """Estado completo do mundo do usuário, no formato que o front consome.

    É a mesma estrutura usada na primeira renderização (embutida no HTML) e
    na rota /api/world/state (usada depois de comprar um elemento), então a
    cena Pixi nunca precisa recarregar a página para se atualizar.
    """
    owned = set(owned_costs_for(user))
    progress, remaining = world_progress(owned, user.points)
    return {
        "points": user.points,
        "progress": progress,
        "remaining": remaining,
        "elements": [
            {
                "cost": cost,
                "emoji": emoji,
                "label": label,
                "owned": cost in owned,
                "message": WORLD_ELEMENT_MESSAGES.get(cost, ""),
            }
            for cost, emoji, label in WORLD_ELEMENTS
        ],
    }


def get_world_real_interests(user):
    preference = WorldRealPreference.query.filter_by(user_id=user.id).first()
    return preference.interests() if preference else []


def world_real_places_for(user):
    interests = set(get_world_real_interests(user))
    interactions = {
        item.place_id: item.action
        for item in WorldRealInteraction.query.filter_by(user_id=user.id).all()
    }
    if not interests:
        return [], interactions

    places = [
        place for place in WORLD_REAL_PLACES
        if interests.intersection(place["interests"])
    ]
    return places, interactions


# ---------------- páginas ----------------

@bp.route("/world")
@login_required
def index():
    """Cena interativa do mundo (PixiJS) + progresso e benefícios."""
    user = current_user()
    unlock(user, "unlocked_secret")  # WORLD -> SECRET: ao visitar o WORLD pela 1ª vez
    db.session.commit()

    state = world_state_for(user)
    return render_template(
        "world/index.html",
        active="world",
        state=state,
        elements=unlocked_elements(owned_costs_for(user)),
        rewards=BENEFITS,
    )


@bp.route("/world/mundo-real/questionario", methods=["GET", "POST"])
@login_required
def real_questionario():
    user = current_user()
    if request.method == "POST":
        selected = request.form.getlist("interests")
        selected = [x for x in selected if x in WORLD_REAL_INTERESTS]
        if not selected:
            flash("Escolha pelo menos um interesse para personalizar seu Mundo Real.")
            return render_template(
                "world/questionario.html",
                active="world",
                interests=WORLD_REAL_INTERESTS,
                selected=selected,
            )
        preference = WorldRealPreference.query.filter_by(user_id=user.id).first()
        if not preference:
            preference = WorldRealPreference(
                user_id=user.id,
                interests_json=json.dumps(selected, ensure_ascii=False),
            )
            db.session.add(preference)
        else:
            preference.interests_json = json.dumps(selected, ensure_ascii=False)
            preference.updated_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for("world.real"))

    return render_template(
        "world/questionario.html",
        active="world",
        interests=WORLD_REAL_INTERESTS,
        selected=get_world_real_interests(user),
    )


@bp.route("/world/mundo-real")
@login_required
def real():
    user = current_user()
    if not get_world_real_interests(user):
        return redirect(url_for("world.real_questionario"))
    places, interactions = world_real_places_for(user)
    return render_template(
        "world/mundo_real.html",
        active="world",
        interests=get_world_real_interests(user),
        places=places,
        interactions=interactions,
        WORLD_REAL_INTERESTS=WORLD_REAL_INTERESTS,
    )


# ---------------- APIs ----------------

@bp.get("/api/world/state")
@login_required
def api_state():
    return jsonify(world_state_for(current_user()))


@bp.post("/api/world/buy")
@login_required
def api_buy():
    user = current_user()
    data = request.get_json(force=True)
    try:
        cost = int(data.get("cost"))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid"}), 400

    match = next((item for item in WORLD_ELEMENTS if item[0] == cost), None)
    if not match:
        return jsonify({"error": "not_found"}), 404
    if WorldItem.query.filter_by(user_id=user.id, cost=cost).first():
        return jsonify({"error": "already_owned"}), 400
    if user.points < cost:
        return jsonify({"error": "insufficient_points"}), 400

    db.session.add(WorldItem(user_id=user.id, cost=cost))
    db.session.commit()

    state = world_state_for(user)
    state.update({
        "ok": True,
        "label": match[2],
        "emoji": match[1],
        "message": WORLD_ELEMENT_MESSAGES.get(
            cost, "Cada conquista é um passo na direção do seu melhor."
        ),
    })
    return jsonify(state)


@bp.post("/api/world/mundo-real/interacao")
@login_required
def api_real_interaction():
    user = current_user()
    data = request.get_json(force=True)
    place_id = (data.get("place_id") or "").strip()
    action = (data.get("action") or "").strip()
    if not any(p["id"] == place_id for p in WORLD_REAL_PLACES):
        return jsonify({"error": "local inválido"}), 404
    if action not in ("liked", "saved", "not_interested"):
        return jsonify({"error": "ação inválida"}), 400

    interaction = WorldRealInteraction.query.filter_by(
        user_id=user.id, place_id=place_id
    ).first()
    if not interaction:
        interaction = WorldRealInteraction(
            user_id=user.id, place_id=place_id, action=action
        )
        db.session.add(interaction)
    else:
        interaction.action = action
        interaction.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True, "place_id": place_id, "action": action})
