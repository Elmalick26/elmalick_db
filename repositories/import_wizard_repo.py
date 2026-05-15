"""
repositories/import_wizard_repo.py
SQL centralisé pour import_wizard.py (importation groupée des étudiants).
"""


class ImportWizardRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_next_class_number(self, class_id, year_id) -> int:
        """Renvoie le prochain numéro d'ordre dans le fصل / السنة donnés."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(MAX(class_number), 0) + 1 "
                "FROM StudentClassNumbers WHERE class_id = %s AND year_id = %s",
                (class_id, year_id),
            )
            row = cur.fetchone()
            return row[0] if row else 1

    def insert_student(self, data: dict) -> int:
        """Insère un étudiant et retourne son id."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO Students
                    (first_name_fr, last_name_fr, first_name_ar, last_name_ar,
                     birth_date, birth_place, gender, address,
                     parent_name, parent_phone, parent_email, parent_address,
                     status)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Active')
                RETURNING id
                """,
                (
                    data.get("first_name_fr", ""),
                    data.get("last_name_fr", ""),
                    data.get("first_name_ar", ""),
                    data.get("last_name_ar", ""),
                    data.get("birth_date") or None,
                    data.get("birth_place", ""),
                    data.get("gender", ""),
                    data.get("address", ""),
                    data.get("parent_name", ""),
                    data.get("parent_phone", ""),
                    data.get("parent_email", ""),
                    data.get("parent_address", ""),
                ),
            )
            return cur.fetchone()[0]

    def insert_student_class_number(self, student_id, class_id, year_id, class_number) -> None:
        """Lie l'étudiant au fصل et à l'année."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO StudentClassNumbers
                    (student_id, class_id, year_id, class_number)
                VALUES (%s, %s, %s, %s)
                """,
                (student_id, class_id, year_id, class_number),
            )

    def list_academic_years(self) -> list:
        """(id, year_label) ORDER BY is_active DESC, id DESC."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, year_label FROM AcademicYears ORDER BY is_active DESC, id DESC")
            return cur.fetchall()

    def list_classes(self) -> list:
        """(id, class_name_fr) ORDER BY sort_order, id."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, class_name_fr FROM Classes ORDER BY sort_order, id")
            return cur.fetchall()
