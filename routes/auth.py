"""
routes/auth.py — porta de entrada do app.

Landing (login/cadastro), criação de conta, saída e o acesso separado do
administrador. Tudo que vem antes de existir uma sessão de usuário.
"""

from datetime import datetime

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from models import User, WorldItem, db

bp = Blueprint("auth", __name__)


@bp.route("/")
def landing():
    if session.get("user_id"):
        return redirect(url_for("main.home"))
    return render_template("auth/landing.html")


@bp.route("/privacidade")
def privacidade():
    return render_template("auth/privacidade.html")


@bp.post("/login")
def login():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        flash("E-mail ou senha inválidos.")
        return redirect(url_for("auth.landing", tab="login"))

    session["user_id"] = user.id
    user.last_login_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for("main.home"))


@bp.post("/cadastro")
def cadastro():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    if not name or not email or len(password) < 6:
        flash("Preencha nome, e-mail e uma senha com pelo menos 6 caracteres.")
        return redirect(url_for("auth.landing", tab="cadastro"))

    if User.query.filter_by(email=email).first():
        flash("Já existe uma conta com esse e-mail.")
        return redirect(url_for("auth.landing", tab="cadastro"))

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # gera user.id antes de criar dados relacionados

    # marca do primeiro passo, já "de fábrica" — espelha o protótipo original
    db.session.add(WorldItem(user_id=user.id, cost=0))
    db.session.commit()

    session["user_id"] = user.id
    # sinaliza pra próxima página renderizada mostrar o modal "Conta criada!"
    # (consumido uma única vez pelo context_processor em app.py)
    session["just_registered"] = True
    return redirect(url_for("main.home"))


@bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("auth/admin_login.html")

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    user = User.query.filter_by(email=email, is_admin=True).first()
    if not user or not user.check_password(password):
        flash("Credenciais de administrador inválidas.")
        return redirect(url_for("auth.admin_login"))

    session["user_id"] = user.id
    user.last_login_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for("admin.dashboard"))


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.landing"))
