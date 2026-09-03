"""
RASTRO — modelos do banco (MySQL via SQLAlchemy).

Cada usuário guarda seu progresso (pontos, humor atual, objetivo/barreira
detectados no TALK, quais áreas já foram desbloqueadas etc). As metas do 1%
e os posts do SECRET viram tabelas próprias, ligadas ao usuário por
user_id — isso é o que permite ao painel de admin listar tudo e calcular
estatísticas agregadas.
"""

import json
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

# limiares (em nº de itens concluídos no ciclo) que desbloqueiam cada semanal
# e liberam os diários da semana seguinte. semana 1 já nasce com os diários
# disponíveis; as demais liberam junto com a respectiva meta semanal.
WEEKLY_UNLOCK_THRESHOLDS = [5, 35, 70, 105]
DAILY_GOALS_PER_WEEK = 35
WEEKLY_GOALS_PER_CYCLE = 4
TOTAL_ITEMS_PER_CYCLE = 145  # 140 diárias + 4 semanais + 1 mensal
CYCLE_BONUS_POINTS = 1000
DAILY_POINTS = 10
WEEKLY_POINTS = 50
MONTHLY_POINTS = 100


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)

    # progresso / preferências que o app vai atualizando conforme o uso
    points = db.Column(db.Integer, default=0, nullable=False)
    completed_steps = db.Column(db.Integer, default=0, nullable=False)
    barriers_overcome = db.Column(db.Integer, default=0, nullable=False)
    checkins = db.Column(db.Integer, default=0, nullable=False)

    current_mood = db.Column(db.String(30))
    current_objective = db.Column(db.String(60))
    current_barrier = db.Column(db.String(60))
    pattern = db.Column(db.String(255))

    # TALK guarda em que etapa da conversa o usuário está, pra poder
    # retomar caso ele saia no meio
    talk_step = db.Column(db.Integer, default=0, nullable=False)
    talk_completed = db.Column(db.Boolean, default=False, nullable=False)

    # desbloqueio progressivo: talk -> 1% -> world -> secret -> perfil
    unlocked_onepct = db.Column(db.Boolean, default=False, nullable=False)
    unlocked_world = db.Column(db.Boolean, default=False, nullable=False)
    unlocked_secret = db.Column(db.Boolean, default=False, nullable=False)
    unlocked_perfil = db.Column(db.Boolean, default=False, nullable=False)

    goals = db.relationship("Goal", backref="user", cascade="all, delete-orphan", lazy=True)
    secret_posts = db.relationship("SecretPost", backref="author", cascade="all, delete-orphan", lazy=True)
    checkin_logs = db.relationship("CheckinLog", backref="user", cascade="all, delete-orphan", lazy=True)
    world_items = db.relationship("WorldItem", backref="user", cascade="all, delete-orphan", lazy=True)
    monthly_cycles = db.relationship("MonthlyCycle", backref="user", cascade="all, delete-orphan", lazy=True)
    # AIGoalDraft possui DUAS referências para users:
    # - user_id: usuário dono do rascunho
    # - reviewed_by: administrador que revisou o rascunho
    # Por isso, precisamos informar explicitamente qual FK cada relação usa.
    ai_drafts = db.relationship(
        "AIGoalDraft",
        foreign_keys="AIGoalDraft.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy=True,
    )
    reviewed_ai_drafts = db.relationship(
        "AIGoalDraft",
        foreign_keys="AIGoalDraft.reviewed_by",
        back_populates="reviewer",
        lazy=True,
    )
    volunteer_tickets = db.relationship("VolunteerTicket", backref="user", cascade="all, delete-orphan", lazy=True)
    benefit_redemptions = db.relationship("BenefitRedemption", back_populates="user", cascade="all, delete-orphan", lazy=True)
    world_real_preference = db.relationship("WorldRealPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    world_real_interactions = db.relationship("WorldRealInteraction", back_populates="user", cascade="all, delete-orphan", lazy=True)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def unlocked_map(self):
        return {
            "talk": True,
            "onepct": self.unlocked_onepct,
            "world": self.unlocked_world,
            "secret": self.unlocked_secret,
            "perfil": self.unlocked_perfil,
        }


class Goal(db.Model):
    __tablename__ = "goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    text = db.Column(db.String(255), nullable=False)
    tag = db.Column(db.String(60))
    done = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SecretPost(db.Model):
    __tablename__ = "secret_posts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    text = db.Column(db.String(500), nullable=False)
    hearts = db.Column(db.Integer, default=0, nullable=False)
    reports = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CheckinLog(db.Model):
    """Histórico de check-ins de humor — usado nas estatísticas do admin."""

    __tablename__ = "checkin_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    mood = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class WorldItem(db.Model):
    """Marca do WORLD já obtida pelo usuário (identificada pelo custo/threshold
    do elemento em data.WORLD_ELEMENTS)."""

    __tablename__ = "world_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    cost = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "cost", name="uq_world_item_user_cost"),)


# ==================== NOVO SISTEMA DE METAS (mensal/semanal/diária + IA) ====================

class AIGoalDraft(db.Model):
    """Rascunho de um bloco de metas (1 mensal + 4 semanais + 140 diárias) gerado
    pela IA (ou pelo fallback baseado em regras), aguardando aprovação do admin
    antes de virar um MonthlyCycle ativo para o usuário."""

    __tablename__ = "ai_goal_drafts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    cycle_number = db.Column(db.Integer, nullable=False)
    objective = db.Column(db.String(60))
    barrier = db.Column(db.String(60))

    # payload_json guarda {"monthly": str, "weekly": [str x4], "daily": [[str x35] x4]}
    payload_json = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(20), default="ia", nullable=False)  # "ia" ou "regra" (fallback)

    status = db.Column(db.String(20), default="pendente", nullable=False)  # pendente/aprovado/rejeitado
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    review_note = db.Column(db.String(255))

    # Relações explícitas para eliminar a ambiguidade entre user_id e reviewed_by.
    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="ai_drafts",
    )
    reviewer = db.relationship(
        "User",
        foreign_keys=[reviewed_by],
        back_populates="reviewed_ai_drafts",
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)

    def payload(self):
        return json.loads(self.payload_json)


class MonthlyCycle(db.Model):
    """Um 'mês' do programa 1%: 1 meta mensal + 4 semanais + 140 diárias (145 no total).
    Ao completar tudo, o usuário ganha o bônus e um novo AIGoalDraft é solicitado."""

    __tablename__ = "monthly_cycles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    cycle_number = db.Column(db.Integer, nullable=False)
    objective = db.Column(db.String(60))
    barrier = db.Column(db.String(60))

    monthly_text = db.Column(db.String(255), nullable=False)
    monthly_done = db.Column(db.Boolean, default=False, nullable=False)

    status = db.Column(db.String(20), default="ativo", nullable=False)  # ativo/concluido
    completed_items = db.Column(db.Integer, default=0, nullable=False)  # 0..145

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    weekly_goals = db.relationship(
        "WeeklyGoal", backref="cycle", cascade="all, delete-orphan", lazy=True,
        order_by="WeeklyGoal.order",
    )

    def progress_percent(self):
        return round((self.completed_items / TOTAL_ITEMS_PER_CYCLE) * 100, 1)


class WeeklyGoal(db.Model):
    __tablename__ = "weekly_goals"

    id = db.Column(db.Integer, primary_key=True)
    cycle_id = db.Column(db.Integer, db.ForeignKey("monthly_cycles.id"), nullable=False, index=True)
    order = db.Column(db.Integer, nullable=False)  # 1..4
    text = db.Column(db.String(255), nullable=False)

    unlocked = db.Column(db.Boolean, default=False, nullable=False)  # a meta semanal em si já apareceu?
    daily_available = db.Column(db.Boolean, default=False, nullable=False)  # os diários dessa semana liberados?
    done = db.Column(db.Boolean, default=False, nullable=False)

    unlocked_at = db.Column(db.DateTime)
    done_at = db.Column(db.DateTime)

    daily_goals = db.relationship(
        "DailyGoal", backref="weekly", cascade="all, delete-orphan", lazy=True,
        order_by="DailyGoal.position",
    )


class DailyGoal(db.Model):
    __tablename__ = "daily_goals"

    id = db.Column(db.Integer, primary_key=True)
    weekly_id = db.Column(db.Integer, db.ForeignKey("weekly_goals.id"), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False)  # 1..35 dentro da semana
    day_number = db.Column(db.Integer, nullable=False)  # 1..7 dentro da semana
    text = db.Column(db.String(255), nullable=False)
    done = db.Column(db.Boolean, default=False, nullable=False)
    done_at = db.Column(db.DateTime)


# ==================== VOLUNTARIADO / TRIAGEM ====================

class VolunteerTicket(db.Model):
    """Pedido de conversa com um voluntário. Nasce de uma triagem: o texto do
    usuário é classificado por urgência; casos críticos são encaminhados
    diretamente ao CVV (188) em vez de entrarem na fila."""

    __tablename__ = "volunteer_tickets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)

    urgency = db.Column(db.String(20), nullable=False)  # baixa/media/alta/critica
    status = db.Column(db.String(30), default="fila", nullable=False)
    # fila / em_atendimento / encerrado / encaminhado_cvv

    partner_university = db.Column(db.String(120))
    volunteer_name = db.Column(db.String(120))
    volunteer_id = db.Column(db.Integer, db.ForeignKey("volunteers.id"), nullable=True, index=True)
    admin_note = db.Column(db.Text)
    closing_note = db.Column(db.Text)

    # áreas que o próprio usuário marcou como envolvidas no problema (chaves
    # de data.VOLUNTEER_TICKET_AREAS, separadas por vírgula)
    areas = db.Column(db.String(255))

    # resultado da conversa: preenchido pelo USUÁRIO depois que o atendimento
    # é encerrado (não pelo voluntário/admin) — é o que o admin pode ver.
    outcome_rating = db.Column(db.String(20))  # sim/parcialmente/nao
    outcome_comment = db.Column(db.String(500))

    volunteer = db.relationship(
        "Volunteer",
        foreign_keys=[volunteer_id],
        back_populates="tickets",
    )
    messages = db.relationship(
        "VolunteerMessage",
        backref="ticket",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="VolunteerMessage.created_at",
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def area_labels(self):
        from data import VOLUNTEER_TICKET_AREAS
        keys = (self.areas or "").split(",") if self.areas else []
        return [VOLUNTEER_TICKET_AREAS.get(k, k) for k in keys if k]


class VolunteerMessage(db.Model):
    """Mensagem trocada dentro de um atendimento de voluntariado. sender é
    'usuario', 'voluntario' ou 'sistema' (mensagens automáticas do Rastro)."""

    __tablename__ = "volunteer_messages"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("volunteer_tickets.id"), nullable=False, index=True)
    sender = db.Column(db.String(20), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ==================== ESTATÍSTICAS DE INSATISFAÇÃO (anônimas) ====================

class SatisfactionEntry(db.Model):
    """Registro anônimo (sem user_id de propósito) sobre o que incomoda o
    usuário — usado só para estatísticas agregadas no /admin, para eventuais
    parceiros (escolas, empresas, prefeituras)."""

    __tablename__ = "satisfaction_entries"

    id = db.Column(db.Integer, primary_key=True)
    context = db.Column(db.String(40), nullable=False)  # escola/empresa/cidade/outro
    reason_tag = db.Column(db.String(60))
    reason_text = db.Column(db.String(500))
    origin = db.Column(db.String(20), nullable=False)  # talk / atualizar_info
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProgramFeedback(db.Model):
    """'O 1% ajudou a resolver seu problema?' — coletado na tela de atualizar
    informações. Também anônimo para as estatísticas, mas guardamos o
    cycle_number pra cruzar com o progresso médio se for útil no futuro."""

    __tablename__ = "program_feedback"

    id = db.Column(db.Integer, primary_key=True)
    helped = db.Column(db.String(20), nullable=False)  # sim/parcialmente/nao
    comment = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ==================== VOLUNTÁRIOS ====================

class Volunteer(db.Model):
    """Conta independente para quem atende usuários no Rastro.
    Voluntários não usam a sessão de usuário comum: a autenticação usa
    session['volunteer_id'].
    """

    __tablename__ = "volunteers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)

    tickets = db.relationship(
        "VolunteerTicket",
        foreign_keys="VolunteerTicket.volunteer_id",
        back_populates="volunteer",
        lazy=True,
    )

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


# ==================== BENEFÍCIOS ====================

class BenefitRedemption(db.Model):
    """Histórico de trocas de pontos por benefícios de saúde."""

    __tablename__ = "benefit_redemptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    benefit_id = db.Column(db.String(80), nullable=False)
    benefit_label = db.Column(db.String(160), nullable=False)
    points_cost = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), default="solicitado", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="benefit_redemptions")


# ==================== MUNDO REAL ====================

class WorldRealPreference(db.Model):
    """Interesses escolhidos pelo usuário para personalizar o Mundo Real."""

    __tablename__ = "world_real_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True)
    interests_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", back_populates="world_real_preference")

    def interests(self):
        try:
            return json.loads(self.interests_json)
        except (TypeError, ValueError):
            return []


class WorldRealInteraction(db.Model):
    """Ação do usuário sobre um local do Mundo Real."""

    __tablename__ = "world_real_interactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    place_id = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(30), nullable=False)  # liked/saved/not_interested
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", back_populates="world_real_interactions")
    __table_args__ = (
        db.UniqueConstraint("user_id", "place_id", name="uq_world_real_user_place"),
    )
