"""Student repository for read operations in El Malick Gest."""

from __future__ import annotations


class StudentRepository:
    """Data access for student-related queries."""

    def __init__(self, conn):
        self.conn = conn

    def get_student_for_edit(self, active_year_id: int, student_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            """
                SELECT S.first_name_fr, S.last_name_fr, S.first_name_ar, S.last_name_ar,
                       S.birth_date, S.birth_place, S.gender, S.address, S.parent_name, S.parent_phone,
                       S.parent_email, S.parent_address, S.registration_date, S.status, S.photo_path,
                       SCN.class_id
                FROM Students S
                LEFT JOIN StudentClassNumbers SCN ON S.id = SCN.student_id AND SCN.year_id = %s
                WHERE S.id = %s
            """,
            (active_year_id, student_id),
        )
        return cursor.fetchone()

    def list_students(self, year_id: int, cycle_id=None, class_id=None, search: str = "", date_from=None, date_to=None):
        cursor = self.conn.cursor()
        query = """
            SELECT S.id, S.first_name_fr, S.last_name_fr, S.first_name_ar, S.last_name_ar,
                   S.gender, C.class_name_fr, S.parent_name, S.parent_phone,
                   S.registration_date, SCN.class_number, S.student_code
            FROM Students S
            LEFT JOIN StudentClassNumbers SCN ON SCN.student_id = S.id AND SCN.year_id = %s
            LEFT JOIN Classes C ON SCN.class_id = C.id
            WHERE 1=1
        """
        params = [year_id]

        if class_id:
            query += " AND SCN.class_id = %s"
            params.append(class_id)
        elif cycle_id:
            query += " AND C.cycle_id = %s"
            params.append(cycle_id)

        if search:
            query += " AND (S.last_name_fr ILIKE %s OR S.first_name_fr ILIKE %s OR S.last_name_ar ILIKE %s OR S.first_name_ar ILIKE %s)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param, search_param])

        if date_from and date_to:
            query += " AND S.registration_date BETWEEN %s AND %s"
            params.extend([date_from, date_to])

        query += " ORDER BY S.id DESC"
        cursor.execute(query, params)
        return cursor.fetchall()

    def list_students_detailed(self, year_id: int, cycle_id=None, class_id=None, search: str = "", date_from=None, date_to=None):
        cursor = self.conn.cursor()
        query = """
            SELECT S.id, S.first_name_fr, S.last_name_fr, S.first_name_ar, S.last_name_ar,
                   S.birth_date, S.birth_place, S.gender, S.address, C.class_name_fr,
                   SCN.class_number, S.student_code,
                   S.parent_name, S.parent_phone, S.parent_email,
                   S.registration_date, S.status
            FROM Students S
            LEFT JOIN StudentClassNumbers SCN ON SCN.student_id = S.id AND SCN.year_id = %s
            LEFT JOIN Classes C ON SCN.class_id = C.id
            WHERE 1=1
        """
        params = [year_id]

        if class_id:
            query += " AND SCN.class_id = %s"
            params.append(class_id)
        elif cycle_id:
            query += " AND C.cycle_id = %s"
            params.append(cycle_id)

        if search:
            query += " AND (S.last_name_fr ILIKE %s OR S.first_name_fr ILIKE %s OR S.last_name_ar ILIKE %s OR S.first_name_ar ILIKE %s)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param, search_param])

        if date_from and date_to:
            query += " AND S.registration_date BETWEEN %s AND %s"
            params.extend([date_from, date_to])

        query += " ORDER BY S.last_name_fr, S.first_name_fr"
        cursor.execute(query, params)
        return cursor.fetchall()

    def add_student(self, data: dict) -> int:
        """Insert a new student record. Returns the new student id.

        Expected keys in *data*:
          first_name_fr, last_name_fr, first_name_ar, last_name_ar,
          birth_date, birth_place, gender, address, parent_name,
          parent_phone, parent_email, parent_address,
          registration_date, status, photo_path (may be None)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO Students (
                first_name_fr, last_name_fr, first_name_ar, last_name_ar,
                birth_date, birth_place, gender, address, parent_name,
                parent_phone, parent_email, parent_address,
                registration_date, status, photo_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                data["first_name_fr"], data["last_name_fr"],
                data["first_name_ar"], data["last_name_ar"],
                data["birth_date"], data["birth_place"], data["gender"],
                data["address"], data["parent_name"], data["parent_phone"],
                data["parent_email"], data["parent_address"],
                data["registration_date"], data["status"], data.get("photo_path"),
            ),
        )
        return cursor.fetchone()[0]

    def update_student(self, student_id: int, data: dict) -> None:
        """Update an existing student record.

        Same keys as add_student; photo_path is optional — if absent or None
        and not explicitly set, the existing value is preserved.
        """
        cursor = self.conn.cursor()
        base_params = [
            data["first_name_fr"], data["last_name_fr"],
            data["first_name_ar"], data["last_name_ar"],
            data["birth_date"], data["birth_place"], data["gender"],
            data["address"], data["parent_name"], data["parent_phone"],
            data["parent_email"], data["parent_address"],
            data["registration_date"], data["status"],
        ]
        if data.get("photo_path"):
            query = """
                UPDATE Students SET
                    first_name_fr=%s, last_name_fr=%s, first_name_ar=%s, last_name_ar=%s,
                    birth_date=%s, birth_place=%s, gender=%s, address=%s, parent_name=%s,
                    parent_phone=%s, parent_email=%s, parent_address=%s,
                    registration_date=%s, status=%s, photo_path=%s
                WHERE id=%s
            """
            base_params.append(data["photo_path"])
        else:
            query = """
                UPDATE Students SET
                    first_name_fr=%s, last_name_fr=%s, first_name_ar=%s, last_name_ar=%s,
                    birth_date=%s, birth_place=%s, gender=%s, address=%s, parent_name=%s,
                    parent_phone=%s, parent_email=%s, parent_address=%s,
                    registration_date=%s, status=%s
                WHERE id=%s
            """
        base_params.append(student_id)
        cursor.execute(query, base_params)

    def delete_student(self, student_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM StudentClassNumbers WHERE student_id=%s", (student_id,))
        cursor.execute("DELETE FROM Students WHERE id=%s", (student_id,))
