"""
routes/volunteer.py — voluntariado.

Duas pontas da mesma conversa:
  * o usuário abre um chamado em /voluntario e conversa por /api/voluntario/*
  * o voluntário atende pelo painel em /voluntario/painel

A triagem por urgência (data.classify_ticket_urgency) é por palavras-chave,
não é diagnóstico: na dúvida ela classifica como mais grave, nunca menos.
"""

from datetime import datetime

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from data import (
    CVV_MESSAGE,
    VOLUNTEER_INTRO_MESSAGE,
    VOLUNTEER_TICKET_AREAS,
    VOLUNTEER_WAIT_MESSAGE,
    classify_ticket_urgency,
)
from helpers import current_user, current_volunteer, login_required, volunteer_login_required
from models import Volunteer, VolunteerMessage, VolunteerTicket, db

bp = Blueprint("volunteer", __name__)


@bp.route("/voluntario/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("volunteer/login.html")

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    volunteer = Volunteer.query.filter_by(email=email).first()

    if not volunteer or not volunteer.active or not volunteer.check_password(password):
        flash("E-mail ou senha de voluntário inválidos.")
        return redirect(url_for("volunteer.login"))

    session.clear()
    session["volunteer_id"] = volunteer.id
    volunteer.last_login_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for("volunteer.panel"))


@bp.route("/voluntario/painel")
@volunteer_login_required
def panel():
    volunteer = current_volunteer()
    # aba "Painel": fila de espera, ainda não assumida por ninguém
    tickets = (
        VolunteerTicket.query
        .filter_by(status="fila", volunteer_id=None)
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
    # aba "Conversas": atendimentos que este voluntário já assumiu e segue ativo
    conversations = (
        VolunteerTicket.query
        .filter_by(volunteer_id=volunteer.id, status="em_atendimento")
        .order_by(VolunteerTicket.updated_at.desc())
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
    return render_template(
        "volunteer/painel.html",
        volunteer=volunteer,
        tickets=tickets,
        conversations=conversations,
        history=history,
        areas=VOLUNTEER_TICKET_AREAS,
    )


@bp.post("/voluntario/tickets/<int:ticket_id>/assumir")
@volunteer_login_required
def assume_ticket(ticket_id):
    volunteer = current_volunteer()
    ticket = VolunteerTicket.query.get_or_404(ticket_id)
    if ticket.status != "fila" or (ticket.volunteer_id and ticket.volunteer_id != volunteer.id):
        flash("Esse atendimento não está disponível para ser assumido.")
        return redirect(url_for("volunteer.panel"))
    ticket.volunteer_id = volunteer.id
    ticket.volunteer_name = volunteer.name
    ticket.status = "em_atendimento"
    db.session.commit()
    flash("Atendimento assumido.")
    return redirect(url_for("volunteer.panel"))


@bp.get("/voluntario/tickets/<int:ticket_id>/mensagens")
@volunteer_login_required
def get_messages(ticket_id):
    volunteer = current_volunteer()
    ticket = VolunteerTicket.query.get_or_404(ticket_id)
    if ticket.volunteer_id != volunteer.id:
        return jsonify({"error": "not_allowed"}), 403
    return jsonify({
        "status": ticket.status,
        "messages": [
            {"id": m.id, "sender": m.sender, "text": m.text, "created_at": m.created_at.strftime("%H:%M")}
            for m in ticket.messages
        ],
    })


@bp.post("/voluntario/tickets/<int:ticket_id>/mensagem")
@volunteer_login_required
def send_message(ticket_id):
    volunteer = current_volunteer()
    ticket = VolunteerTicket.query.get_or_404(ticket_id)
    if ticket.volunteer_id != volunteer.id or ticket.status != "em_atendimento":
        return jsonify({"error": "not_allowed"}), 403
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "empty"}), 400
    msg = VolunteerMessage(ticket_id=ticket.id, sender="voluntario", text=text[:2000])
    db.session.add(msg)
    ticket.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": {"id": msg.id, "sender": msg.sender, "text": msg.text, "created_at": msg.created_at.strftime("%H:%M")}})


@bp.post("/voluntario/tickets/<int:ticket_id>/cvv")
@volunteer_login_required
def forward_cvv(ticket_id):
    volunteer = current_volunteer()
    ticket = VolunteerTicket.query.get_or_404(ticket_id)
    if ticket.volunteer_id != volunteer.id or ticket.status != "em_atendimento":
        flash("Esse atendimento não pertence a você.")
        return redirect(url_for("volunteer.panel"))
    db.session.add(VolunteerMessage(ticket_id=ticket.id, sender="voluntario", text=CVV_MESSAGE))
    ticket.status = "encaminhado_cvv"
    ticket.closing_note = ticket.closing_note or "Encaminhado ao CVV pelo voluntário."
    db.session.commit()
    flash("Conversa encaminhada para a mensagem do CVV e encerrada.")
    return redirect(url_for("volunteer.panel"))


@bp.post("/voluntario/tickets/<int:ticket_id>/encerrar")
@volunteer_login_required
def close_ticket(ticket_id):
    volunteer = current_volunteer()
    ticket = VolunteerTicket.query.get_or_404(ticket_id)
    if ticket.volunteer_id != volunteer.id:
        flash("Esse atendimento não pertence a você.")
        return redirect(url_for("volunteer.panel"))
    note = (request.form.get("closing_note") or "").strip()
    if not note:
        flash("Escreva uma anotação antes de encerrar o atendimento.")
        return redirect(url_for("volunteer.panel"))
    ticket.closing_note = note
    ticket.status = "encerrado"
    db.session.commit()
    flash("Atendimento encerrado e salvo no histórico.")
    return redirect(url_for("volunteer.panel"))


@bp.route("/voluntario/logout")
def logout():
    session.pop("volunteer_id", None)
    return redirect(url_for("volunteer.login"))


def _serialize_volunteer_message(msg):
    return {
        "id": msg.id,
        "sender": msg.sender,
        "text": msg.text,
        "created_at": msg.created_at.strftime("%H:%M"),
    }


@bp.route("/voluntario")
@login_required
def chat():
    user = current_user()
    active_ticket = (
        VolunteerTicket.query
        .filter_by(user_id=user.id)
        .filter(VolunteerTicket.status.in_(("fila", "em_atendimento")))
        .order_by(VolunteerTicket.created_at.desc())
        .first()
    )
    closed_ticket = None
    if not active_ticket:
        closed_ticket = (
            VolunteerTicket.query
            .filter_by(user_id=user.id, outcome_rating=None)
            .filter(VolunteerTicket.status.in_(("encerrado", "encaminhado_cvv")))
            .order_by(VolunteerTicket.updated_at.desc())
            .first()
        )
    ticket = active_ticket or closed_ticket
    return render_template(
        "volunteer/chat.html",
        active="talk",
        areas=VOLUNTEER_TICKET_AREAS,
        intro_message=VOLUNTEER_INTRO_MESSAGE,
        ticket=ticket,
        ticket_open=bool(active_ticket),
        awaiting_outcome=bool(closed_ticket),
        messages=[_serialize_volunteer_message(m) for m in ticket.messages] if ticket else [],
    )


@bp.post("/api/voluntario/ticket")
@login_required
def api_ticket():
    user = current_user()
    existing = (
        VolunteerTicket.query
        .filter_by(user_id=user.id)
        .filter(VolunteerTicket.status.in_(("fila", "em_atendimento")))
        .first()
    )
    if existing:
        return jsonify({"error": "already_open"}), 400

    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    areas = [a for a in (data.get("areas") or []) if a in VOLUNTEER_TICKET_AREAS]
    if not text:
        return jsonify({"error": "empty"}), 400

    urgency, is_crisis = classify_ticket_urgency(text)

    ticket = VolunteerTicket(
        user_id=user.id,
        description=text[:2000],
        urgency=urgency,
        areas=",".join(areas),
        status="encaminhado_cvv" if is_crisis else "fila",
    )
    db.session.add(ticket)
    db.session.flush()

    db.session.add(VolunteerMessage(ticket_id=ticket.id, sender="sistema", text=VOLUNTEER_INTRO_MESSAGE))
    db.session.add(VolunteerMessage(ticket_id=ticket.id, sender="usuario", text=text[:2000]))

    if is_crisis:
        db.session.add(VolunteerMessage(ticket_id=ticket.id, sender="sistema", text=CVV_MESSAGE))
    else:
        db.session.add(VolunteerMessage(ticket_id=ticket.id, sender="sistema", text=VOLUNTEER_WAIT_MESSAGE))

    db.session.commit()

    return jsonify({
        "crisis": is_crisis,
        "ticket_id": ticket.id,
        "messages": [_serialize_volunteer_message(m) for m in ticket.messages],
    })


@bp.post("/api/voluntario/mensagem")
@login_required
def api_mensagem():
    user = current_user()
    data = request.get_json(force=True)
    ticket_id = data.get("ticket_id")
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "empty"}), 400

    ticket = VolunteerTicket.query.get_or_404(ticket_id)
    if ticket.user_id != user.id or ticket.status not in ("fila", "em_atendimento"):
        return jsonify({"error": "not_allowed"}), 403

    msg = VolunteerMessage(ticket_id=ticket.id, sender="usuario", text=text[:2000])
    db.session.add(msg)
    ticket.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": _serialize_volunteer_message(msg)})


@bp.get("/api/voluntario/mensagens/<int:ticket_id>")
@login_required
def api_mensagens(ticket_id):
    user = current_user()
    ticket = VolunteerTicket.query.get_or_404(ticket_id)
    if ticket.user_id != user.id:
        return jsonify({"error": "not_allowed"}), 403
    return jsonify({
        "status": ticket.status,
        "messages": [_serialize_volunteer_message(m) for m in ticket.messages],
    })


@bp.post("/api/voluntario/ticket/<int:ticket_id>/resultado")
@login_required
def api_resultado(ticket_id):
    user = current_user()
    ticket = VolunteerTicket.query.get_or_404(ticket_id)
    if ticket.user_id != user.id or ticket.status not in ("encerrado", "encaminhado_cvv"):
        return jsonify({"error": "not_allowed"}), 403
    data = request.get_json(force=True)
    rating = data.get("rating")
    if rating not in ("sim", "parcialmente", "nao"):
        return jsonify({"error": "invalid_rating"}), 400
    ticket.outcome_rating = rating
    ticket.outcome_comment = (data.get("comment") or "").strip()[:500] or None
    db.session.commit()
    return jsonify({"ok": True})
