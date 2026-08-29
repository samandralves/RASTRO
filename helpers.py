"""
helpers.py — utilidades compartilhadas por todos os blueprints.

Sessão (do usuário e do voluntário), decorators de acesso e leitura rápida
do progresso. Este módulo só depende de flask + models, então nenhum
blueprint precisa importar app.py — o que evita import circular.
"""

from functools import wraps

from flask import redirect, session, url_for

from models import MonthlyCycle, User, Volunteer, db


# ---------------- sessão ----------------

def current_user():
    """Usuário logado na sessão atual, ou None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.landing", tab="login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or not user.is_admin:
            return redirect(url_for("auth.admin_login"))
        return view(*args, **kwargs)

    return wrapped


# ---------------- progresso do usuário ----------------

def owned_costs_for(user):
    """Custos (thresholds) dos elementos do WORLD que o usuário já obteve."""
    return [item.cost for item in user.world_items]


def unlock(user, field):
    """Marca uma etapa da jornada como desbloqueada, se ainda não estava."""
    if not getattr(user, field):
        setattr(user, field, True)


# ---------------- sessão do voluntário ----------------

def current_volunteer():
    volunteer_id = session.get("volunteer_id")
    if not volunteer_id:
        return None
    return db.session.get(Volunteer, volunteer_id)


def volunteer_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("volunteer_id"):
            return redirect(url_for("volunteer.login"))
        return view(*args, **kwargs)

    return wrapped


def volunteer_or_admin_name():
    volunteer = current_volunteer()
    return volunteer.name if volunteer else "Administrador"


# ---------------- helpers de dados por usuário ----------------

# ---------------- progresso do usuário (continuação) ----------------

def completed_count_for(user):
    """Total de itens concluídos (diários+semanais+mensal) no ciclo ativo do
    usuário, ou o total acumulado do último ciclo se nenhum estiver ativo."""
    cycle = (
        MonthlyCycle.query.filter_by(user_id=user.id, status="ativo")
        .order_by(MonthlyCycle.cycle_number.desc())
        .first()
    )
    if not cycle:
        cycle = (
            MonthlyCycle.query.filter_by(user_id=user.id)
            .order_by(MonthlyCycle.cycle_number.desc())
            .first()
        )
    return cycle.completed_items if cycle else 0
