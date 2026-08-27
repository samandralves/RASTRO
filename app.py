"""
RASTRO — Flask + HTML + CSS + JS puro, com login real e dados em MySQL.

sidebar no desktop, bottom-nav no celular, cards em glassmorphism,
TALK → barreira → 1% → WORLD → PERFIL e SECRET.

Cada usuário autenticado guarda seu próprio progresso no banco (ver
models.py). O painel /admin lista o registro completo e estatísticas
agregadas para quem tiver is_admin=True.
"""

import os
import json
from datetime import datetime
from functools import wraps

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

import ai_goals
import goal_engine
from models import (
    DAILY_POINTS,
    MONTHLY_POINTS,
    WEEKLY_POINTS,
    AIGoalDraft,
    CheckinLog,
    BenefitRedemption,
    DailyGoal,
    Goal,
    MonthlyCycle,
    ProgramFeedback,
    SatisfactionEntry,
    SecretPost,
    User,
    Volunteer,
    WorldRealPreference,
    WorldRealInteraction,
    VolunteerTicket,
    WeeklyGoal,
    WorldItem,
    db,
)
from rastro_data import (
    BARRIER_OPTIONS,
    CVV_MESSAGE,
    MOOD_OPTIONS,
    PATTERNS,
    REWARDS,
    BENEFITS,
    WORLD_REAL_INTERESTS,
    WORLD_REAL_PLACES,
    SATISFACTION_CONTEXTS,
    SATISFACTION_REASON_TAGS,
    WORLD_ELEMENT_MESSAGES,
    WORLD_ELEMENTS,
    classify_ticket_urgency,
    detect_barrier,
    detect_objective,
    unlocked_elements,
    world_progress,
)

app = Flask(__name__)
app.secret_key = os.environ.get("RASTRO_SECRET_KEY", "rastro-dev-secret")

MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "90873600144!55KM")
MYSQL_DB = os.environ.get("MYSQL_DB", "rastrodb")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# ---------------- autenticação ----------------

def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def current_volunteer():
    volunteer_id = session.get("volunteer_id")
    if not volunteer_id:
        return None
    return db.session.get(Volunteer, volunteer_id)


def volunteer_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("volunteer_id"):
            return redirect(url_for("volunteer_login"))
        return view(*args, **kwargs)

    return wrapped


def volunteer_or_admin_name():
    volunteer = current_volunteer()
    return volunteer.name if volunteer else "Administrador"


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


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("landing", tab="login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or not user.is_admin:
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped


# ---------------- helpers de dados por usuário ----------------

def owned_costs_for(user):
    return [item.cost for item in user.world_items]


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


def unlock(user, field):
    """Marca uma etapa como desbloqueada, se ainda não estava."""
    if not getattr(user, field):
        setattr(user, field, True)


# ---------------- páginas públicas (login / cadastro) ----------------

@app.route("/")
def landing():
    if session.get("user_id"):
        return redirect(url_for("home"))
    return render_template("landing.html")


@app.post("/login")
def login():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        flash("E-mail ou senha inválidos.")
        return redirect(url_for("landing", tab="login"))

    session["user_id"] = user.id
    user.last_login_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for("home"))


@app.post("/cadastro")
def cadastro():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    if not name or not email or len(password) < 6:
        flash("Preencha nome, e-mail e uma senha com pelo menos 6 caracteres.")
        return redirect(url_for("landing", tab="cadastro"))

    if User.query.filter_by(email=email).first():
        flash("Já existe uma conta com esse e-mail.")
        return redirect(url_for("landing", tab="cadastro"))

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # gera user.id antes de criar dados relacionados

    # marca do primeiro passo, já "de fábrica" — espelha o protótipo original
    db.session.add(WorldItem(user_id=user.id, cost=0))

    db.session.commit()

    session["user_id"] = user.id
    return redirect(url_for("home"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin_login.html")

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    user = User.query.filter_by(email=email, is_admin=True).first()
    if not user or not user.check_password(password):
        flash("Credenciais de administrador inválidas.")
        return redirect(url_for("admin_login"))

    session["user_id"] = user.id
    user.last_login_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for("admin_dashboard"))



@app.route("/voluntario/login", methods=["GET", "POST"])
def volunteer_login():
    if request.method == "GET":
        return render_template("voluntario_login.html")

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    volunteer = Volunteer.query.filter_by(email=email).first()

    if not volunteer or not volunteer.active or not volunteer.check_password(password):
        flash("E-mail ou senha de voluntário inválidos.")
        return redirect(url_for("volunteer_login"))

    session.clear()
    session["volunteer_id"] = volunteer.id
    volunteer.last_login_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for("volunteer_panel"))


@app.route("/voluntario/painel")
@volunteer_login_required
def volunteer_panel():
    volunteer = current_volunteer()
    tickets = (
        VolunteerTicket.query
        .filter(
            VolunteerTicket.status.in_(("fila", "em_atendimento")),
            db.or_(
                VolunteerTicket.volunteer_id.is_(None),
                VolunteerTicket.volunteer_id == volunteer.id,
            ),
        )
        .order_by(
            db.case(
                (VolunteerTicket.urgency == "critica", 0),
                (VolunteerTicket.urgency == "alta", 1),
                (VolunteerTicket.urgency == "media", 2),
                else_=3,
            ),
            VolunteerTicket.created_at.asc(),
        )
        .all()
    )
    history = (
        VolunteerTicket.query
        .filter_by(volunteer_id=volunteer.id)
        .filter(VolunteerTicket.status.in_(("encerrado", "encaminhado_cvv")))
        .order_by(VolunteerTicket.updated_at.desc())
        .limit(50)
        .all()
    )
    return render_template("voluntario_painel.html", volunteer=volunteer, tickets=tickets, history=history)


@app.post("/voluntario/tickets/<int:ticket_id>/assumir")
@volunteer_login_required
def volunteer_assume_ticket(ticket_id):
    volunteer = current_volunteer()
    ticket = VolunteerTicket.query.get_or_404(ticket_id)
    if ticket.status != "fila" or (ticket.volunteer_id and ticket.volunteer_id != volunteer.id):
        flash("Esse atendimento não está disponível para ser assumido.")
        return redirect(url_for("volunteer_panel"))
    ticket.volunteer_id = volunteer.id
    ticket.volunteer_name = volunteer.name
    ticket.status = "em_atendimento"
    db.session.commit()
    flash("Atendimento assumido.")
    return redirect(url_for("volunteer_panel"))


@app.post("/voluntario/tickets/<int:ticket_id>/encerrar")
@volunteer_login_required
def volunteer_close_ticket(ticket_id):
    volunteer = current_volunteer()
    ticket = VolunteerTicket.query.get_or_404(ticket_id)
    if ticket.volunteer_id != volunteer.id:
        flash("Esse atendimento não pertence a você.")
        return redirect(url_for("volunteer_panel"))
    note = (request.form.get("closing_note") or "").strip()
    if not note:
        flash("Escreva uma anotação antes de encerrar o atendimento.")
        return redirect(url_for("volunteer_panel"))
    ticket.closing_note = note
    ticket.status = "encerrado"
    db.session.commit()
    flash("Atendimento encerrado e salvo no histórico.")
    return redirect(url_for("volunteer_panel"))


@app.route("/voluntario/logout")
def volunteer_logout():
    session.pop("volunteer_id", None)
    return redirect(url_for("volunteer_login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


# ---------------- painel administrativo ----------------

@app.route("/admin")
@admin_required
def admin_dashboard():
    users = User.query.order_by(User.created_at.desc()).all()
    total_users = len(users)
    total_points = sum(u.points for u in users)
    avg_points = round(total_points / total_users, 1) if total_users else 0
    total_checkins = sum(u.checkins for u in users)
    total_goals_done = (
        db.session.query(db.func.count(DailyGoal.id)).filter_by(done=True).scalar()
        + db.session.query(db.func.count(WeeklyGoal.id)).filter_by(done=True).scalar()
        + db.session.query(db.func.count(MonthlyCycle.id)).filter_by(monthly_done=True).scalar()
    )
    total_secret_posts = SecretPost.query.count()

    stage_counts = {"TALK": total_users, "1%": 0, "WORLD": 0, "SECRET": 0, "PERFIL": 0}
    for u in users:
        if u.unlocked_onepct:
            stage_counts["1%"] += 1
        if u.unlocked_world:
            stage_counts["WORLD"] += 1
        if u.unlocked_secret:
            stage_counts["SECRET"] += 1
        if u.unlocked_perfil:
            stage_counts["PERFIL"] += 1

    mood_counts = {}
    for mood, in db.session.query(CheckinLog.mood).all():
        mood_counts[mood] = mood_counts.get(mood, 0) + 1

    # ---- rascunhos de IA pendentes de aprovação ----
    pending_drafts = AIGoalDraft.query.filter_by(status="pendente").order_by(AIGoalDraft.created_at).all()

    # ---- voluntariado ----
    tickets = VolunteerTicket.query.order_by(VolunteerTicket.created_at.desc()).limit(50).all()
    volunteers = Volunteer.query.order_by(Volunteer.created_at.desc()).all()
    ticket_urgency_counts = {}
    for urgency, in db.session.query(VolunteerTicket.urgency).all():
        ticket_urgency_counts[urgency] = ticket_urgency_counts.get(urgency, 0) + 1

    # ---- estatísticas de insatisfação (anônimas) ----
    satisfaction_by_context = {}
    total_satisfaction = SatisfactionEntry.query.count()
    for context, in db.session.query(SatisfactionEntry.context).all():
        satisfaction_by_context[context] = satisfaction_by_context.get(context, 0) + 1
    satisfaction_percent = {
        context: round((count / total_satisfaction) * 100, 1) if total_satisfaction else 0
        for context, count in satisfaction_by_context.items()
    }

    # ---- feedback do programa 1% ----
    feedback_counts = {"sim": 0, "parcialmente": 0, "nao": 0}
    for helped, in db.session.query(ProgramFeedback.helped).all():
        feedback_counts[helped] = feedback_counts.get(helped, 0) + 1
    total_feedback = sum(feedback_counts.values())

    return render_template(
        "admin_dashboard.html",
        users=users,
        total_users=total_users,
        total_points=total_points,
        avg_points=avg_points,
        total_checkins=total_checkins,
        total_goals_done=total_goals_done,
        total_secret_posts=total_secret_posts,
        stage_counts=stage_counts,
        mood_counts=mood_counts,
        pending_drafts=pending_drafts,
        tickets=tickets,
        ticket_urgency_counts=ticket_urgency_counts,
        volunteers=volunteers,
        satisfaction_by_context=satisfaction_by_context,
        satisfaction_percent=satisfaction_percent,
        total_satisfaction=total_satisfaction,
        feedback_counts=feedback_counts,
        total_feedback=total_feedback,
    )


@app.post("/admin/drafts/<int:draft_id>/aprovar")
@admin_required
def admin_draft_aprovar(draft_id):
    admin_user = current_user()
    draft = AIGoalDraft.query.get_or_404(draft_id)
    if draft.status == "pendente":
        goal_engine.activate_draft(draft, admin_user)
        db.session.commit()
        flash("Bloco de metas aprovado e liberado para o usuário.")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/drafts/<int:draft_id>/rejeitar")
@admin_required
def admin_draft_rejeitar(draft_id):
    admin_user = current_user()
    draft = AIGoalDraft.query.get_or_404(draft_id)
    note = request.form.get("note", "")
    if draft.status == "pendente":
        goal_engine.reject_draft(draft, admin_user, note)
        db.session.commit()
        flash("Rascunho rejeitado.")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/tickets/<int:ticket_id>/atualizar")
@admin_required
def admin_ticket_atualizar(ticket_id):
    ticket = VolunteerTicket.query.get_or_404(ticket_id)
    status = request.form.get("status")
    if status in ("fila", "em_atendimento", "encerrado", "encaminhado_cvv"):
        ticket.status = status
    volunteer_id = request.form.get("volunteer_id")
    if volunteer_id:
        volunteer = db.session.get(Volunteer, int(volunteer_id))
        if volunteer:
            ticket.volunteer_id = volunteer.id
            ticket.volunteer_name = volunteer.name
    ticket.partner_university = request.form.get("partner_university", "").strip() or ticket.partner_university
    ticket.admin_note = request.form.get("admin_note", "").strip() or ticket.admin_note
    db.session.commit()
    flash("Ticket atualizado.")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/volunteers")
@admin_required
def admin_create_volunteer():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    if not name or not email or len(password) < 6:
        flash("Nome, e-mail e senha (mín. 6 caracteres) são obrigatórios.")
        return redirect(url_for("admin_dashboard"))
    if Volunteer.query.filter_by(email=email).first():
        flash("Já existe um voluntário com esse e-mail.")
        return redirect(url_for("admin_dashboard"))
    volunteer = Volunteer(name=name, email=email, active=True)
    volunteer.set_password(password)
    db.session.add(volunteer)
    db.session.commit()
    flash("Voluntário criado.")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/volunteers/<int:volunteer_id>/toggle")
@admin_required
def admin_toggle_volunteer(volunteer_id):
    volunteer = Volunteer.query.get_or_404(volunteer_id)
    volunteer.active = not volunteer.active
    db.session.commit()
    flash(f"Voluntário {'ativado' if volunteer.active else 'desativado'}.")
    return redirect(url_for("admin_dashboard"))


# ---------------- páginas do app (exigem login) ----------------

@app.route("/home")
@login_required
def home():
    user = current_user()
    owned = owned_costs_for(user)
    progress, remaining = world_progress(owned, user.points)
    return render_template(
        "index.html",
        active="home",
        points=user.points,
        completed=completed_count_for(user),
        current_mood=user.current_mood,
        current_objective=user.current_objective,
        current_barrier=user.current_barrier,
        pattern=user.pattern,
        world_elements=unlocked_elements(owned),
        progress=progress,
        remaining=remaining,
    )


@app.route("/talk")
@login_required
def talk():
    user = current_user()
    if user.talk_completed:
        return render_template("talk_menu.html", active="talk")
    return render_template(
        "talk.html",
        active="talk",
        objective=user.current_objective,
        barrier=user.current_barrier,
    )


@app.route("/world")
@login_required
def world():
    user = current_user()
    unlock(user, "unlocked_secret")  # WORLD -> SECRET: ao visitar o WORLD pela 1ª vez
    db.session.commit()

    owned = owned_costs_for(user)
    progress, remaining = world_progress(owned, user.points)
    return render_template(
        "world.html",
        active="world",
        points=user.points,
        elements=unlocked_elements(owned),
        owned_costs=owned,
        progress=progress,
        remaining=remaining,
        rewards=BENEFITS,
    )



@app.route("/world/mundo-real/questionario", methods=["GET", "POST"])
@login_required
def world_real_questionario():
    user = current_user()
    if request.method == "POST":
        selected = request.form.getlist("interests")
        selected = [x for x in selected if x in WORLD_REAL_INTERESTS]
        if not selected:
            flash("Escolha pelo menos um interesse para personalizar seu Mundo Real.")
            return render_template(
                "mundo_real_questionario.html",
                active="world",
                interests=WORLD_REAL_INTERESTS,
                selected=selected,
            )
        preference = WorldRealPreference.query.filter_by(user_id=user.id).first()
        if not preference:
            preference = WorldRealPreference(user_id=user.id, interests_json=json.dumps(selected, ensure_ascii=False))
            db.session.add(preference)
        else:
            preference.interests_json = json.dumps(selected, ensure_ascii=False)
            preference.updated_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for("world_real"))

    selected = get_world_real_interests(user)
    return render_template(
        "mundo_real_questionario.html",
        active="world",
        interests=WORLD_REAL_INTERESTS,
        selected=selected,
    )


@app.route("/world/mundo-real")
@login_required
def world_real():
    user = current_user()
    if not get_world_real_interests(user):
        return redirect(url_for("world_real_questionario"))
    places, interactions = world_real_places_for(user)
    return render_template(
        "mundo_real.html",
        active="world",
        interests=get_world_real_interests(user),
        places=places,
        interactions=interactions,
        WORLD_REAL_INTERESTS=WORLD_REAL_INTERESTS,
    )


@app.post("/api/world/mundo-real/interacao")
@login_required
def api_world_real_interaction():
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


@app.route("/onepct")
@login_required
def onepct():
    user = current_user()
    cycle = (
        MonthlyCycle.query.filter_by(user_id=user.id, status="ativo")
        .order_by(MonthlyCycle.cycle_number.desc())
        .first()
    )
    if cycle:
        return render_template(
            "onepct.html",
            active="onepct",
            state="ativo",
            cycle=cycle,
            points={"monthly": MONTHLY_POINTS, "weekly": WEEKLY_POINTS, "daily": DAILY_POINTS},
        )

    draft = (
        AIGoalDraft.query.filter_by(user_id=user.id, status="pendente")
        .order_by(AIGoalDraft.created_at.desc())
        .first()
    )
    if draft:
        return render_template("onepct.html", active="onepct", state="pendente", draft=draft)

    return render_template("onepct.html", active="onepct", state="nenhum")


@app.route("/secret")
@login_required
def secret():
    posts = SecretPost.query.order_by(SecretPost.created_at.desc()).all()
    return render_template("secret.html", active="secret", posts=posts)


@app.route("/perfil")
@login_required
def perfil():
    user = current_user()
    owned = owned_costs_for(user)
    return render_template(
        "perfil.html",
        active="perfil",
        points=user.points,
        completed=completed_count_for(user),
        barriers_overcome=user.barriers_overcome,
        checkins=user.checkins,
        world_count=len(unlocked_elements(owned)),
        pattern=user.pattern,
        barrier=user.current_barrier,
        objective=user.current_objective,
    )


# ---------------- API ----------------

@app.post("/api/checkin")
@login_required
def api_checkin():
    user = current_user()
    data = request.get_json(force=True)
    mood = (data.get("mood") or "").strip().lower()
    if mood not in MOOD_OPTIONS:
        return jsonify({"error": "mood inválido"}), 400

    user.current_mood = mood
    user.checkins += 1
    db.session.add(CheckinLog(user_id=user.id, mood=mood))
    db.session.commit()
    return jsonify({"ok": True, "mood": mood, "checkins": user.checkins})


@app.post("/api/talk/answer")
@login_required
def api_talk_answer():
    user = current_user()
    data = request.get_json(force=True)
    step = int(data.get("step", 0))
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "empty"}), 400

    if step == 0:
        objective = detect_objective(text)
        barrier = detect_barrier(text)
        user.current_objective = objective
        user.current_barrier = barrier
        user.talk_step = 1
        db.session.commit()
        return jsonify({
            "done": False,
            "step": 1,
            "objective": objective,
            "barrier": barrier,
            "reply": f"Entendi. Isso parece estar ligado a <strong>{objective}</strong>. Um obstáculo que apareceu no que você contou foi <strong>{barrier}</strong>.<br><br>Qual dessas barreiras representa melhor o seu momento?",
            "options": BARRIER_OPTIONS,
        })

    if step == 1:
        barrier = text if text in BARRIER_OPTIONS else user.current_barrier
        user.current_barrier = barrier
        user.talk_step = 2
        db.session.commit()
        return jsonify({
            "done": False,
            "step": 2,
            "barrier": barrier,
            "reply": f"Perfeito. Então vamos trabalhar a partir de <strong>{barrier}</strong>.<br><br>Se você pudesse deixar uma única coisa 1% melhor hoje, qual seria? Pode responder livremente.",
        })

    if step == 2:
        user.talk_step = 3
        db.session.commit()
        return jsonify({
            "done": False,
            "step": 3,
            "reply": (
                "Obrigado por contar. Uma última coisa, totalmente opcional e anônima nas nossas "
                "estatísticas: o que mais tem te incomodado ultimamente? Se não quiser responder, "
                "é só escrever \"pular\"."
            ),
        })

    if step == 3:
        normalized = text.strip().lower()
        if normalized not in ("pular", "pular.", "não", "nao"):
            context = "outro"
            for candidate in SATISFACTION_CONTEXTS:
                if candidate in normalized:
                    context = candidate
                    break
            db.session.add(SatisfactionEntry(context=context, reason_text=text[:500], origin="talk"))

        objective = user.current_objective
        barrier = user.current_barrier
        user.pattern = PATTERNS.get(barrier, PATTERNS["não sei por onde começar"])
        user.talk_step = 4
        user.talk_completed = True
        unlock(user, "unlocked_onepct")  # TALK -> 1%: ao terminar a conversa inicial

        # gera o 1º bloco de metas (mensal + 4 semanais + 140 diárias), pendente de aprovação
        payload, source = ai_goals.generate_goal_payload(objective, barrier)
        goal_engine.request_new_draft(user, cycle_number=1, payload=payload, source=source)

        db.session.commit()

        return jsonify({
            "done": True,
            "step": 4,
            "objective": objective,
            "barrier": barrier,
            "reply": "Pronto. Já preparei seu primeiro bloco de metas do mês — ele está passando por uma revisão rápida e já aparece no 1% assim que for liberado.",
            "redirect": "/onepct",
        })

    return jsonify({"error": "step inválido"}), 400


@app.post("/api/goals/toggle")
@login_required
def api_goals_toggle():
    """Alterna uma meta mensal/semanal/diária. data = {kind: 'monthly'|'weekly'|'daily', id: <id>}."""
    user = current_user()
    data = request.get_json(force=True)
    kind = data.get("kind")
    try:
        item_id = int(data.get("id"))
    except (TypeError, ValueError):
        return jsonify({"error": "id inválido"}), 400

    if kind == "monthly":
        cycle = MonthlyCycle.query.filter_by(id=item_id, user_id=user.id, status="ativo").first()
        if not cycle:
            return jsonify({"error": "not_found"}), 404
        goal_engine.toggle_monthly_goal(user, cycle)
        if cycle.monthly_done:
            unlock(user, "unlocked_world")  # 1% -> WORLD: ao concluir a 1ª ação

    elif kind == "weekly":
        weekly = WeeklyGoal.query.get(item_id)
        cycle = weekly.cycle if weekly else None
        if not weekly or not cycle or cycle.user_id != user.id or cycle.status != "ativo":
            return jsonify({"error": "not_found"}), 404
        goal_engine.toggle_weekly_goal(user, cycle, weekly)
        if weekly.done:
            unlock(user, "unlocked_world")

    elif kind == "daily":
        daily = DailyGoal.query.get(item_id)
        weekly = daily.weekly if daily else None
        cycle = weekly.cycle if weekly else None
        if not daily or not weekly or not cycle or cycle.user_id != user.id or cycle.status != "ativo":
            return jsonify({"error": "not_found"}), 404
        goal_engine.toggle_daily_goal(user, cycle, daily)
        if daily.done:
            unlock(user, "unlocked_world")

    else:
        return jsonify({"error": "kind inválido"}), 400

    user.completed_steps = max(0, cycle.completed_items)
    user.barriers_overcome = max(2, 2 + user.completed_steps // 3)
    db.session.commit()

    owned = owned_costs_for(user)
    progress, remaining = world_progress(owned, user.points)
    return jsonify({
        "ok": True,
        "points": user.points,
        "completed_items": cycle.completed_items,
        "cycle_status": cycle.status,
        "progress": progress,
        "remaining": remaining,
    })


@app.post("/api/world/buy")
@login_required
def api_world_buy():
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

    owned = owned_costs_for(user)
    progress, remaining = world_progress(owned, user.points)
    return jsonify({
        "ok": True,
        "points": user.points,
        "label": match[2],
        "emoji": match[1],
        "message": WORLD_ELEMENT_MESSAGES.get(cost, "Cada conquista é um passo na direção do seu melhor."),
        "progress": progress,
        "remaining": remaining,
    })


@app.post("/api/rewards/redeem")
@login_required
def api_rewards_redeem():
    """Troca de pontos por uma recompensa (janela 'Troca de Pontos')."""
    user = current_user()
    data = request.get_json(force=True)
    reward_id = data.get("id")

    match = next((r for r in REWARDS if r["id"] == reward_id), None)
    if not match:
        return jsonify({"error": "not_found"}), 404
    if user.points < match["cost"]:
        return jsonify({"error": "insufficient_points"}), 400

    user.points -= match["cost"]
    db.session.commit()

    owned = owned_costs_for(user)
    progress, remaining = world_progress(owned, user.points)
    return jsonify({
        "ok": True,
        "points": user.points,
        "reward": match,
        "progress": progress,
        "remaining": remaining,
    })



@app.post("/api/benefits/redeem")
@login_required
def api_benefits_redeem():
    user = current_user()
    data = request.get_json(force=True)
    benefit_id = data.get("id")
    benefit = next((item for item in BENEFITS if item["id"] == benefit_id), None)
    if not benefit:
        return jsonify({"error": "not_found"}), 404
    if user.points < benefit["cost"]:
        return jsonify({"error": "insufficient_points"}), 400

    user.points -= benefit["cost"]
    redemption = BenefitRedemption(
        user_id=user.id,
        benefit_id=benefit["id"],
        benefit_label=benefit["label"],
        points_cost=benefit["cost"],
        status="solicitado",
    )
    db.session.add(redemption)
    db.session.commit()
    return jsonify({"ok": True, "points": user.points, "benefit": benefit, "redemption_id": redemption.id})


@app.post("/api/secret/post")
@login_required
def api_secret_post():
    user = current_user()
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "empty"}), 400
    if len(text) > 500:
        return jsonify({"error": "too_long"}), 400

    post = SecretPost(user_id=user.id, text=text, hearts=0)
    db.session.add(post)
    unlock(user, "unlocked_perfil")  # SECRET -> PERFIL: ao publicar ou reagir
    db.session.commit()
    return jsonify({"post": {"id": post.id, "text": post.text, "hearts": post.hearts}})


@app.post("/api/secret/heart")
@login_required
def api_secret_heart():
    user = current_user()
    data = request.get_json(force=True)
    post_id = data.get("id")

    post = SecretPost.query.get(post_id)
    if not post:
        return jsonify({"error": "not found"}), 404

    post.hearts += 1
    unlock(user, "unlocked_perfil")  # SECRET -> PERFIL: ao publicar ou reagir
    db.session.commit()
    return jsonify({"hearts": post.hearts})


# ---------------- voluntariado / triagem ----------------

@app.route("/voluntario")
@login_required
def voluntario():
    return render_template("voluntario.html", active="talk")


@app.post("/api/voluntario/ticket")
@login_required
def api_voluntario_ticket():
    user = current_user()
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "empty"}), 400

    urgency, is_crisis = classify_ticket_urgency(text)

    ticket = VolunteerTicket(
        user_id=user.id,
        description=text[:2000],
        urgency=urgency,
        status="encaminhado_cvv" if is_crisis else "fila",
    )
    db.session.add(ticket)
    db.session.commit()

    if is_crisis:
        return jsonify({"crisis": True, "message": CVV_MESSAGE})

    return jsonify({
        "crisis": False,
        "message": (
            "Recebemos o que você contou. Pelo nível de urgência, você entrou na nossa fila de "
            "atendimento e um voluntário (ou parceiro universitário) vai te retornar em breve."
        ),
    })


# ---------------- atualizar informações ----------------

@app.route("/atualizar-informacoes")
@login_required
def atualizar_informacoes():
    return render_template(
        "atualizar_informacoes.html",
        active="talk",
        satisfaction_contexts=SATISFACTION_CONTEXTS,
    )


@app.post("/atualizar/feedback")
@login_required
def atualizar_feedback():
    helped = request.form.get("helped")
    comment = (request.form.get("comment") or "").strip()
    if helped in ("sim", "parcialmente", "nao"):
        db.session.add(ProgramFeedback(helped=helped, comment=comment[:500] or None))
        db.session.commit()
        flash("Obrigado pelo feedback!")
    return redirect(url_for("atualizar_informacoes"))


@app.post("/atualizar/satisfacao")
@login_required
def atualizar_satisfacao():
    context = request.form.get("context")
    reason_text = (request.form.get("reason_text") or "").strip()
    if context in SATISFACTION_CONTEXTS:
        db.session.add(SatisfactionEntry(
            context=context,
            reason_text=reason_text[:500] or None,
            origin="atualizar_info",
        ))
        db.session.commit()
        flash("Obrigado por compartilhar, de forma anônima.")
    return redirect(url_for("atualizar_informacoes"))


@app.post("/atualizar/objetivo")
@login_required
def atualizar_objetivo():
    user = current_user()
    text = (request.form.get("text") or "").strip()
    if not text:
        flash("Escreva um pouco sobre o que está vivendo agora.")
        return redirect(url_for("atualizar_informacoes"))

    objective = detect_objective(text)
    barrier = detect_barrier(text)
    user.current_objective = objective
    user.current_barrier = barrier
    user.pattern = PATTERNS.get(barrier, PATTERNS["não sei por onde começar"])

    next_cycle_number = (
        db.session.query(db.func.max(MonthlyCycle.cycle_number))
        .filter_by(user_id=user.id)
        .scalar() or 0
    ) + 1

    payload, source = ai_goals.generate_goal_payload(objective, barrier)
    goal_engine.request_new_draft(user, cycle_number=next_cycle_number, payload=payload, source=source)
    db.session.commit()

    flash("Objetivo atualizado! Um novo bloco de metas foi gerado e está em aprovação.")
    return redirect(url_for("onepct"))


# ---------------- comandos de linha de comando (flask --app app <comando>) ----------------

@app.cli.command("init-db")
def init_db_command():
    """Cria as tabelas no banco configurado pelas variáveis MYSQL_*."""
    with app.app_context():
        db.create_all()
    print("Banco inicializado.")


@app.cli.command("create-admin")
def create_admin_command():
    """Cria (ou promove) um usuário administrador, pedindo os dados no terminal."""
    import getpass

    name = input("Nome: ").strip()
    email = input("E-mail: ").strip().lower()
    password = getpass.getpass("Senha: ")

    if not name or not email or len(password) < 6:
        print("Nome, e-mail e senha (mín. 6 caracteres) são obrigatórios.")
        return

    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_admin = True
            user.set_password(password)
            db.session.commit()
            print(f"Usuário {email} promovido a administrador.")
            return

        user = User(
            name=name,
            email=email,
            is_admin=True,
            unlocked_onepct=True,
            unlocked_world=True,
            unlocked_secret=True,
            unlocked_perfil=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        db.session.add(WorldItem(user_id=user.id, cost=0))
        db.session.commit()
        print(f"Administrador {email} criado.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=False, port=5000)


@app.cli.command("create-volunteer")
def create_volunteer_command():
    """Cria ou atualiza uma conta de voluntário pelo terminal."""
    import getpass

    name = input("Nome: ").strip()
    email = input("E-mail: ").strip().lower()
    password = getpass.getpass("Senha: ")

    if not name or not email or len(password) < 6:
        print("Nome, e-mail e senha (mín. 6 caracteres) são obrigatórios.")
        return

    with app.app_context():
        volunteer = Volunteer.query.filter_by(email=email).first()
        if volunteer:
            volunteer.name = name
            volunteer.active = True
            volunteer.set_password(password)
            db.session.commit()
            print(f"Voluntário {email} atualizado e ativado.")
            return

        volunteer = Volunteer(name=name, email=email, active=True)
        volunteer.set_password(password)
        db.session.add(volunteer)
        db.session.commit()
        print(f"Voluntário {email} criado com sucesso.")
