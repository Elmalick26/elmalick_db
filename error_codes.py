"""
error_codes.py — Taxonomie centralisée des erreurs / تصنيف مركزي للأخطاء

Catégories :
  E-DB-xxx   : Erreurs base de données
  E-AUTH-xxx : Authentification / autorisation
  E-VALID-xxx: Validation des données
  E-IO-xxx   : Fichiers / export / import
  E-NET-xxx  : Réseau / services externes

Utilisation :
    from error_codes import DB_QUERY, log_op_error, new_op_id
    op_id = new_op_id()
    log_op_error("ModuleName", DB_QUERY, e, op_id)
    QMessageBox.critical(self, f"Erreur [{DB_QUERY}]",
                         f"Erreur lors de la requête.\n\nID: {op_id}")
"""

from __future__ import annotations

import uuid

from app_logger import AppLogger

# ── E-DB : Erreurs base de données ──────────────────────────────────────────
DB_QUERY = "E-DB-001"  # Erreur d'exécution de requête SQL
DB_CONNECT = "E-DB-002"  # Perte de connexion à la base de données
DB_INTEGRITY = "E-DB-003"  # Violation de contrainte d'intégrité (FK, UNIQUE…)
DB_TRANSACTION = "E-DB-004"  # Erreur lors d'une transaction

# ── E-AUTH : Authentification / autorisation ─────────────────────────────────
AUTH_INVALID = "E-AUTH-001"  # Identifiants invalides
AUTH_EXPIRED = "E-AUTH-002"  # Session expirée
AUTH_FORBIDDEN = "E-AUTH-003"  # Accès refusé (rôle insuffisant)

# ── E-VALID : Validation des données ─────────────────────────────────────────
VALID_MISSING = "E-VALID-001"  # Champ obligatoire manquant
VALID_FORMAT = "E-VALID-002"  # Format de données incorrect
VALID_RANGE = "E-VALID-003"  # Valeur hors plage acceptable

# ── E-IO : Fichiers / export / import ────────────────────────────────────────
IO_PDF_GEN = "E-IO-001"  # Échec de génération PDF
IO_EXPORT = "E-IO-002"  # Échec d'export (rapport, fichier)
IO_FILE_READ = "E-IO-003"  # Échec de lecture d'un fichier
IO_FILE_WRITE = "E-IO-004"  # Échec d'écriture d'un fichier

# ── E-NET : Réseau / services externes ───────────────────────────────────────
NET_TIMEOUT = "E-NET-001"  # Délai d'attente réseau dépassé
NET_SMTP = "E-NET-002"  # Échec d'envoi email (SMTP)
NET_API = "E-NET-003"  # Erreur d'appel API externe


# ── Helpers ──────────────────────────────────────────────────────────────────
def new_op_id() -> str:
    """Génère un identifiant d'opération court (8 car.) pour la traçabilité."""
    return uuid.uuid4().hex[:8].upper()


def log_op_error(module: str, error_code: str, exc: Exception, op_id: str) -> None:
    """Enregistre une erreur structurée : code + module + op_id dans les logs."""
    AppLogger.error(module, f"[{error_code}] op:{op_id} — {exc}")
