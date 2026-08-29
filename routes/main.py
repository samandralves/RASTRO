"""
routes/main.py — as telas do dia a dia de quem está logado.

home, TALK, 1%, SECRET, PERFIL, "atualizar informações" e as APIs que essas
telas chamam (check-in, respostas do TALK, marcar metas, resgates e SECRET).
O WORLD tem blueprint próprio, em routes/world.py.
"""

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from data import (
    BARRIER_OPTIONS,
    BENEFITS,
    MOOD_OPTIONS,
    PATTERNS,
    REWARDS,
    SATISFACTION_CONTEXTS,
    detect_barrier,
    detect_objective,
    unlocked_elements,
    world_progress,
)
from helpers import (
    completed_count_for,
    current_user,
    login_required,
    owned_costs_for,
    unlock,
)
from models import (
    DAILY_POINTS,
    MONTHLY_POINTS,
    WEEKLY_POINTS,
    AIGoalDraft,
    BenefitRedemption,
    CheckinLog,
    DailyGoal,
    MonthlyCycle,
    ProgramFeedback,
    SatisfactionEntry,
    SecretPost,
    WeeklyGoal,
    db,
)
from services import ai_goals, goal_engine

bp = Blueprint("main", __name__)


@bp.route("/home")
@login_required
def home():
    user = current_user()
    owned = owned_costs_for(user)
    progress, remaining = world_progress(owned, user.points)
    return render_template(
        "user/home.html",
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


@bp.route("/talk")
@login_required
def talk():
    user = current_user()
    if user.talk_completed:
        return render_template("user/talk_menu.html", active="talk")
    return render_template(
        "user/talk.html",
        active="talk",
        objective=user.current_objective,
        barrier=user.current_barrier,
    )


@bp.route("/onepct")
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
            "user/onepct.html",
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
        return render_template("user/onepct.html", active="onepct", state="pendente", draft=draft)

    return render_template("user/onepct.html", active="onepct", state="nenhum")


@bp.route("/secret")
@login_required
def secret():
    posts = SecretPost.query.order_by(SecretPost.created_at.desc()).all()
    return render_template("user/secret.html", active="secret", posts=posts)


@bp.route("/perfil")
@login_required
def perfil():
    user = current_user()
    owned = owned_costs_for(user)
    return render_template(
        "user/perfil.html",
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


@bp.post("/api/checkin")
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


@bp.post("/api/talk/answer")
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


@bp.post("/api/goals/toggle")
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


@bp.post("/api/rewards/redeem")
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



@bp.post("/api/benefits/redeem")
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


@bp.post("/api/secret/post")
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


@bp.post("/api/secret/heart")
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


@bp.route("/atualizar-informacoes")
@login_required
def atualizar_informacoes():
    return render_template(
        "user/atualizar_informacoes.html",
        active="talk",
        satisfaction_contexts=SATISFACTION_CONTEXTS,
    )


@bp.post("/atualizar/feedback")
@login_required
def atualizar_feedback():
    helped = request.form.get("helped")
    comment = (request.form.get("comment") or "").strip()
    if helped in ("sim", "parcialmente", "nao"):
        db.session.add(ProgramFeedback(helped=helped, comment=comment[:500] or None))
        db.session.commit()
        flash("Obrigado pelo feedback!")
    return redirect(url_for("main.atualizar_informacoes"))


@bp.post("/atualizar/satisfacao")
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
    return redirect(url_for("main.atualizar_informacoes"))


@bp.post("/atualizar/objetivo")
@login_required
def atualizar_objetivo():
    user = current_user()
    text = (request.form.get("text") or "").strip()
    if not text:
        flash("Escreva um pouco sobre o que está vivendo agora.")
        return redirect(url_for("main.atualizar_informacoes"))

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
    return redirect(url_for("main.onepct"))
