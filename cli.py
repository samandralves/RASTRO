"""
cli.py — comandos de terminal do projeto (`flask --app app <comando>`).

    flask --app app init-db           cria as tabelas
    flask --app app create-admin      cria/promove um administrador
    flask --app app create-volunteer  cadastra um voluntário
"""

from models import User, Volunteer, WorldItem, db


def register(app):
    """Registra os comandos no app."""

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
