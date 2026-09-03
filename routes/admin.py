"""
routes/admin.py — painel do administrador.

Mostra o registro completo do banco e as estatísticas de uso, aprova ou
rejeita os rascunhos de metas gerados por IA e administra os voluntários.
Todas as rotas exigem is_admin (helpers.admin_required).
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from helpers import admin_required, current_user
from models import (
    AIGoalDraft,
    CheckinLog,
    DailyGoal,
    MonthlyCycle,
    ProgramFeedback,
    SatisfactionEntry,
    SecretPost,
    User,
    Volunteer,
    VolunteerTicket,
    WeeklyGoal,
    db,
)
from services import goal_engine

bp = Blueprint("admin", __name__)


@bp.route("/admin")
@admin_required
def dashboard():
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
    secret_posts = SecretPost.query.order_by(SecretPost.created_at.desc()).limit(100).all()
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
        "admin/dashboard.html",
        users=users,
        total_users=total_users,
        total_points=total_points,
        avg_points=avg_points,
        total_checkins=total_checkins,
        total_goals_done=total_goals_done,
        secret_posts=secret_posts,
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


@bp.post("/admin/drafts/<int:draft_id>/aprovar")
@admin_required
def draft_aprovar(draft_id):
    admin_user = current_user()
    draft = AIGoalDraft.query.get_or_404(draft_id)
    if draft.status == "pendente":
        goal_engine.activate_draft(draft, admin_user)
        db.session.commit()
        flash("Bloco de metas aprovado e liberado para o usuário.")
    return redirect(url_for("admin.dashboard"))


@bp.post("/admin/drafts/<int:draft_id>/rejeitar")
@admin_required
def draft_rejeitar(draft_id):
    admin_user = current_user()
    draft = AIGoalDraft.query.get_or_404(draft_id)
    note = request.form.get("note", "")
    if draft.status == "pendente":
        goal_engine.reject_draft(draft, admin_user, note)
        db.session.commit()
        flash("Rascunho rejeitado.")
    return redirect(url_for("admin.dashboard"))


@bp.post("/admin/secret/<int:post_id>/apagar")
@admin_required
def secret_delete(post_id):
    post = SecretPost.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash("Post do Secret removido.")
    return redirect(url_for("admin.dashboard"))


@bp.post("/admin/volunteers")
@admin_required
def create_volunteer():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    if not name or not email or len(password) < 6:
        flash("Nome, e-mail e senha (mín. 6 caracteres) são obrigatórios.")
        return redirect(url_for("admin.dashboard"))
    if Volunteer.query.filter_by(email=email).first():
        flash("Já existe um voluntário com esse e-mail.")
        return redirect(url_for("admin.dashboard"))
    volunteer = Volunteer(name=name, email=email, active=True)
    volunteer.set_password(password)
    db.session.add(volunteer)
    db.session.commit()
    flash("Voluntário criado.")
    return redirect(url_for("admin.dashboard"))


@bp.post("/admin/volunteers/<int:volunteer_id>/toggle")
@admin_required
def toggle_volunteer(volunteer_id):
    volunteer = Volunteer.query.get_or_404(volunteer_id)
    volunteer.active = not volunteer.active
    db.session.commit()
    flash(f"Voluntário {'ativado' if volunteer.active else 'desativado'}.")
    return redirect(url_for("admin.dashboard"))
