# db_sync_routes.py
#
# Ferramenta isolada para sincronizar models.py com o banco em produção,
# sem precisar rodar ALTER TABLE manualmente cada vez que surge uma coluna
# nova faltando. Resolve de vez o erro "Unknown column ... in field list".
#
# O QUE FAZ:
#   1. Cria, via db.create_all(), qualquer tabela inteira que ainda não
#      exista no banco (ex: uma classe nova adicionada em models.py).
#   2. Para tabelas que JÁ existiam, compara as colunas do banco com as
#      colunas que a classe Python espera, e roda um ALTER TABLE ADD COLUMN
#      só para as que estiverem faltando.
#
# O QUE NUNCA FAZ (segurança):
#   - Nunca apaga tabela ou coluna existente.
#   - Nunca altera o tipo de uma coluna já existente.
#   - Nunca marca uma coluna nova como NOT NULL (mesmo que o modelo diga
#     nullable=False) — isso evita erro em linhas que já existem no banco.
#     Se algum campo realmente precisar ser obrigatório dali pra frente,
#     isso é validado na aplicação, não no banco.
#
# Acesso restrito a administradores logados (mesma checagem is_admin do
# resto do painel /admin).
#
# COMO USAR:
#   1. Registre o blueprint no app.py (ver instruções no final deste arquivo).
#   2. Acesse /admin/sync-db logado como admin, sempre que aparecer um erro
#      "Unknown column" ou depois de adicionar algo novo no models.py.

from flask import Blueprint, redirect, render_template_string, session, url_for
from sqlalchemy import inspect, text

from models import User, db

db_sync_bp = Blueprint("db_sync", __name__)


def _current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


_PAGE = """
<html>
<head><meta charset="utf-8"><title>Sincronização do banco</title></head>
<body style="font-family: 'Courier New', monospace; background:#0a1220; color:#dfe8ff; padding:28px; line-height:1.6;">
  <h2 style="color:#4fe0b3;">Sincronização do banco — models.py &harr; MySQL</h2>
  <pre style="background:#0f1c33; padding:16px; border-radius:8px; white-space:pre-wrap;">{{ log_text }}</pre>
  <p style="color:#f7bd6a; font-size:13px; max-width:640px;">
    Colunas novas são sempre criadas como opcionais (aceitam NULL), mesmo
    que o modelo diga o contrário — isso evita erro em linhas que já
    existiam. Não precisa rodar de novo a menos que o models.py mude outra
    vez.
  </p>
  <p><a href="{{ back_url }}" style="color:#4fe0b3;">&larr; Voltar ao painel</a></p>
</body>
</html>
"""


@db_sync_bp.route("/admin/sync-db")
def sync_db():
    user = _current_user()
    if not user or not user.is_admin:
        return redirect(url_for("admin_login"))

    engine = db.engine
    inspector = inspect(engine)
    existing_tables_before = set(inspector.get_table_names())

    log = []

    # 1) cria tabelas inteiras que ainda não existem no banco
    db.create_all()

    inspector = inspect(engine)  # atualiza a leitura, agora com as tabelas novas
    existing_tables_after = set(inspector.get_table_names())
    for t in sorted(existing_tables_after - existing_tables_before):
        log.append(f"[TABELA CRIADA] {t}")

    # 2) para tabelas que já existiam, adiciona só as colunas que faltam
    for table in db.metadata.sorted_tables:
        table_name = table.name
        if table_name not in existing_tables_before:
            continue  # tabela nova — create_all() já criou com todas as colunas certas

        existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
        for column in table.columns:
            if column.name in existing_cols:
                continue
            try:
                col_type = column.type.compile(dialect=engine.dialect)
                ddl = f"ALTER TABLE `{table_name}` ADD COLUMN `{column.name}` {col_type}"
                with engine.connect() as conn:
                    conn.execute(text(ddl))
                    conn.commit()
                log.append(f"[COLUNA ADICIONADA] {table_name}.{column.name} ({col_type})")
            except Exception as exc:
                log.append(f"[FALHOU] {table_name}.{column.name} — {exc}")

    if not log:
        log.append("Nada para sincronizar — o banco já está alinhado com models.py.")

    return render_template_string(
        _PAGE,
        log_text="\n".join(log),
        back_url=url_for("admin_dashboard"),
    )


# ---------------------------------------------------------------------------
# Como ligar isso ao app.py (só isso, nada mais precisa mudar lá):
#
#   from db_sync_routes import db_sync_bp
#   app.register_blueprint(db_sync_bp)
#
# Coloque essas duas linhas junto das outras (perto de world_bp, se já
# estiver lá). Depois, sempre que precisar sincronizar, acesse logado como
# admin: https://rastro-esae.onrender.com/admin/sync-db
# ---------------------------------------------------------------------------
