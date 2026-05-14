"""Repository for InventoryManagement — items, movements, reports."""


class InventoryRepository:
    def __init__(self, conn):
        self.conn = conn

    # --- Items ---

    def list_all_items(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM InventoryItems ORDER BY name_fr")
        return cursor.fetchall()

    def get_item_quantity(self, item_id: int) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT quantity FROM InventoryItems WHERE id=%s", (item_id,))
        row = cursor.fetchone()
        return int(row[0] or 0) if row else 0

    def update_item_quantity(self, item_id: int, new_qty: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("UPDATE InventoryItems SET quantity=%s WHERE id=%s", (new_qty, item_id))

    def insert_item(self, name_fr: str, name_ar: str, category: str,
                    quantity: int, min_quantity: int,
                    unit_price: float, location: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO InventoryItems (name_fr, name_ar, category, quantity, min_quantity, unit_price, location)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (name_fr, name_ar, category, quantity, min_quantity, unit_price, location),
        )
        return cursor.fetchone()[0]

    # --- Movement log ---

    def insert_movement_log(self, item_id: int, m_type: str, qty: int,
                            date_str: str, notes: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO InventoryLog (item_id, transaction_type, quantity, transaction_date, notes)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (item_id, m_type, qty, date_str, notes),
        )

    def list_movement_history(self, limit: int = 50) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT L.transaction_date,
                   L.transaction_type,
                   COALESCE(I.name_fr, '[Article supprim\u00e9]') AS item_name,
                   L.quantity,
                   L.notes
            FROM InventoryLog L LEFT JOIN InventoryItems I ON L.item_id = I.id
            ORDER BY L.id DESC LIMIT %s
            """,
            (limit,),
        )
        return cursor.fetchall()

    # --- Reports ---

    def get_stock_value_by_category(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT category, COUNT(*) AS items_count,
                   SUM(quantity) AS total_qty,
                   SUM(quantity * unit_price) AS total_value
            FROM InventoryItems
            GROUP BY category
            ORDER BY total_value DESC
            """
        )
        return cursor.fetchall()

    def get_low_stock_items(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT name_fr, category, quantity, min_quantity, location
            FROM InventoryItems
            WHERE quantity <= min_quantity
            ORDER BY (min_quantity - quantity) DESC, name_fr
            """
        )
        return cursor.fetchall()

    def get_movements_by_period(self, date_from: str, date_to_full: str) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT I.name_fr,
                   SUM(CASE WHEN L.transaction_type = 'IN' THEN L.quantity ELSE 0 END) AS total_in,
                   SUM(CASE WHEN L.transaction_type = 'OUT' THEN L.quantity ELSE 0 END) AS total_out,
                   SUM(CASE WHEN L.transaction_type = 'IN' THEN L.quantity ELSE -L.quantity END) AS net_qty
            FROM InventoryLog L
            JOIN InventoryItems I ON I.id = L.item_id
            WHERE CAST(L.transaction_date AS TIMESTAMP) BETWEEN CAST(%s AS TIMESTAMP) AND CAST(%s AS TIMESTAMP)
            GROUP BY I.id, I.name_fr
            ORDER BY I.name_fr
            """,
            (date_from, date_to_full),
        )
        return cursor.fetchall()
