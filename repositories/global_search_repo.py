"""
repositories/global_search_repo.py
SQL centralisé pour global_search_dialog.py (recherche globale).
"""


class GlobalSearchRepository:
    def __init__(self, conn):
        self.conn = conn

    def search_all(self, pat: str, limit: int = 30) -> list[tuple]:
        """
        Recherche dans Students, Staff, Payments et AuditLogs.
        Retourne une liste de tuples:
            (category, name_fr, subtitle, module_key, record_id)
        """
        results = []

        with self.conn.cursor() as cur:
            # 1. Élèves
            cur.execute(
                """
                SELECT id,
                       first_name_fr || ' ' || last_name_fr,
                       COALESCE(first_name_ar, '') || ' ' || COALESCE(last_name_ar, '')
                FROM Students
                WHERE (first_name_fr ILIKE %s OR last_name_fr ILIKE %s
                       OR first_name_ar ILIKE %s OR last_name_ar ILIKE %s)
                  AND status != 'Archived'
                ORDER BY last_name_fr
                LIMIT %s
                """,
                (pat, pat, pat, pat, limit),
            )
            for sid, name_fr, name_ar in cur.fetchall():
                subtitle = name_ar.strip() or ""
                results.append(("Élève", name_fr.strip(), subtitle, "student_management", sid))

            # 2. Personnel
            cur.execute(
                """
                SELECT id,
                       first_name || ' ' || last_name,
                       role
                FROM Staff
                WHERE (first_name ILIKE %s OR last_name ILIKE %s OR role ILIKE %s)
                  AND COALESCE(status, 'Actif') != 'Archived'
                ORDER BY last_name
                LIMIT %s
                """,
                (pat, pat, pat, limit),
            )
            for sid, name, role in cur.fetchall():
                results.append(("Personnel", name.strip(), role or "", "staff_management", sid))

            # 3. Paiements
            cur.execute(
                """
                SELECT P.id,
                       COALESCE(S.first_name_fr,'') || ' ' || COALESCE(S.last_name_fr,''),
                       CAST(P.transaction_date AS TEXT),
                       P.amount_paid
                FROM Payments P
                JOIN Students S ON P.student_id = S.id
                WHERE (CAST(P.id AS TEXT) ILIKE %s
                       OR COALESCE(P.details,'') ILIKE %s
                       OR S.first_name_fr ILIKE %s
                       OR S.last_name_fr  ILIKE %s)
                ORDER BY P.transaction_date DESC
                LIMIT %s
                """,
                (pat, pat, pat, pat, limit),
            )
            for pid, name, tx_date, amount in cur.fetchall():
                date_str = str(tx_date)[:10] if tx_date else ""
                subtitle = f"Reçu #{pid}  •  {date_str}  •  {float(amount or 0):,.0f} F"
                results.append(("Paiement", name.strip(), subtitle, "finance_payments", pid))

            # 4. AuditLogs
            cur.execute(
                """
                SELECT id, actor, action || ' → ' || COALESCE(target,''),
                       CAST(timestamp AS TEXT)
                FROM AuditLogs
                WHERE actor ILIKE %s OR action ILIKE %s OR target ILIKE %s
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (pat, pat, pat, limit),
            )
            for aid, actor, action_target, ts in cur.fetchall():
                date_str = str(ts)[:16] if ts else ""
                subtitle = f"{actor}  •  {date_str}"
                results.append(("Audit", action_target, subtitle, None, aid))

        return results
