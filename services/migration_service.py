"""Year-end migration business service for El Malick Gest."""

from __future__ import annotations

from app_logger import AppLogger


class MigrationService:
    """Handles year-end migration persistence independently from the UI layer."""

    def execute_migration(
        self, conn, migration_rows: list[dict], target_year_id: int, change_active_year: bool = False
    ) -> int:
        """Apply year-end migration decisions and return the number of processed students."""
        cursor = conn.cursor()
        processed_count = 0

        for row in migration_rows:
            student_id = int(row["student_id"])
            decision = row["decision"]
            current_class_id = row["current_class_id"]
            next_class_id = row.get("next_class_id")

            destination_class_id = None
            if decision == "Admis":
                destination_class_id = next_class_id
            elif decision == "Redouble":
                destination_class_id = current_class_id

            if decision == "Exclu":
                cursor.execute("UPDATE Students SET status='Exclu' WHERE id=%s", (student_id,))
            elif decision == "Admis" and not destination_class_id:
                cursor.execute("UPDATE Students SET status='Diplômé' WHERE id=%s", (student_id,))
            elif destination_class_id:
                cursor.execute(
                    "SELECT MAX(class_number) FROM StudentClassNumbers WHERE class_id=%s AND year_id=%s",
                    (destination_class_id, target_year_id),
                )
                max_number_result = cursor.fetchone()
                next_number = (max_number_result[0] or 0) + 1

                cursor.execute(
                    "SELECT id FROM StudentClassNumbers WHERE student_id=%s AND year_id=%s",
                    (student_id, target_year_id),
                )
                existing_row = cursor.fetchone()

                if existing_row:
                    cursor.execute(
                        "UPDATE StudentClassNumbers SET class_id=%s, class_number=%s WHERE id=%s",
                        (destination_class_id, next_number, existing_row[0]),
                    )
                else:
                    cursor.execute(
                        "INSERT INTO StudentClassNumbers (student_id, class_id, year_id, class_number) VALUES (%s, %s, %s, %s)",
                        (student_id, destination_class_id, target_year_id, next_number),
                    )

                cursor.execute("UPDATE Students SET status='Active' WHERE id=%s", (student_id,))

            processed_count += 1

        if change_active_year:
            cursor.execute("UPDATE AcademicYears SET is_active=0")
            cursor.execute("UPDATE AcademicYears SET is_active=1 WHERE id=%s", (target_year_id,))

        AppLogger.info(
            "MigrationService",
            f"Processed {processed_count} students for year-end migration to year_id={target_year_id}",
        )
        return processed_count
