"""
repositories/login_repo.py
SQL centralisé pour login_window.py (authentification utilisateur).
"""


class LoginRepository:
    def __init__(self, conn):
        self.conn = conn

    def count_users(self) -> int:
        """Renvoie le nombre total d'utilisateurs."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM Users")
            row = cur.fetchone()
            return row[0] if row else 0

    def insert_default_admin(self, password_hash: str) -> None:
        """Insère le compte administrateur par défaut."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO Users (username, email, password_hash, role, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                ("admin", "admin@school.local", password_hash, "Admin", "Actif"),
            )

    def get_user_for_login(self, username: str) -> tuple | None:
        """Retourne (id, role, password_hash, status) ou None."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, role, password_hash, status FROM Users WHERE username=%s",
                (username,),
            )
            return cur.fetchone()

    def update_password_hash(self, user_id: int, new_hash: str) -> None:
        """Met à jour le hachage du mot de passe d'un utilisateur."""
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE Users SET password_hash=%s WHERE id=%s",
                (new_hash, user_id),
            )

    def update_admin_credentials(self, new_hash: str, new_username: str) -> None:
        """Met à jour le nom d'utilisateur et le mot de passe de l'admin initial."""
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE Users SET password_hash=%s, username=%s WHERE username='admin' OR id=1",
                (new_hash, new_username),
            )
