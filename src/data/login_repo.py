"""
repositories/login_repo.py
SQL centralisé pour login_window.py (authentification utilisateur).
"""

from __future__ import annotations

from typing import Any


class LoginRepository:
    def __init__(self, conn: Any) -> None:
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

    # ─── Lockout persistant (DB-based) ────────────────────────────────────────

    def get_lockout_status(self, username: str) -> tuple[int, bool]:
        """Retourne (attempt_count, is_locked). is_locked = lockout_until > NOW()."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT attempt_count,
                           lockout_until IS NOT NULL AND lockout_until > NOW()
                    FROM LoginAttempts WHERE username = %s
                    """,
                    (username,),
                )
                row = cur.fetchone()
                if row:
                    return int(row[0]), bool(row[1])
        except Exception:
            pass
        return 0, False

    def record_failed_attempt(self, username: str) -> bool:
        """Incrémente les tentatives. Retourne True si le compte est maintenant verrouillé."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO LoginAttempts (username, attempt_count, last_attempt)
                    VALUES (%s, 1, NOW())
                    ON CONFLICT (username) DO UPDATE
                        SET attempt_count = LoginAttempts.attempt_count + 1,
                            last_attempt = NOW()
                    RETURNING attempt_count
                    """,
                    (username,),
                )
                row = cur.fetchone()
                count = row[0] if row else 1
                if count >= 5:
                    cur.execute(
                        """
                        UPDATE LoginAttempts
                        SET lockout_until = NOW() + INTERVAL '5 minutes',
                            attempt_count = 0
                        WHERE username = %s
                        """,
                        (username,),
                    )
                    return True
        except Exception:
            pass
        return False

    def clear_attempts(self, username: str) -> None:
        """Supprime le compteur après une connexion réussie."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM LoginAttempts WHERE username = %s", (username,))
        except Exception:
            pass
