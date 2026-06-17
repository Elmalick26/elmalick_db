# Release Notes — El Malick Gest v2.0.0-rc1

**Date de sortie**: 25 mai 2026
**Branche**: `main`
**Statut**: Release Candidate 1

---

## Résumé des changements majeurs

Cette version marque la finalisation du cycle de développement stratégique (Semaines 1–11) avec :
- Sécurisation complète de l'API REST (JWT, CORS, rate limiting, audit logs)
- Gouvernance de la base de données par Alembic (migrations 001→007)
- Optimisation des performances (index GIN pg_trgm, index composites, élimination N+1)
- Standardisation de la gestion d'erreurs (codes d'erreur centralisés, retry exponentiel)
- Contrôle d'accès granulaire (RBAC, IDOR, session timeout)

---

## Nouvelles fonctionnalités

### API REST (Semaines 1–6)
- Authentification JWT avec `ELMALICK_API_SECRET` (HS256, expiration 60 min)
- CORS configurable via `ALLOWED_ORIGINS` — protection wildcard automatique
- Rate limiting : 5 requêtes/min sur `/api/v1/login`
- Routes versionnées `/api/v1/` avec routes legacy `/api/` (en-tête `Deprecation`)
- Portail parent : login PIN, accès notes/absences/solde (IDOR protégé par token JWT)
- Audit log pour toutes les opérations sensibles (VIEW_DUES, LOGIN, RESET_PARENT_PIN)
- Endpoint `/api/health` : connectivité DB, latence, taille, dernier backup, **pool metrics**

### Contrôle d'accès (Semaines 5–7)
- Matrice RBAC : Admin, Enseignant, Personnel, Parent (18 modules protégés)
- `PermissionChecker` centralisé — interdiction d'accès granulaire par feature
- Timeout de session configurable (défaut : 60 min)
- Verrouillage de compte après 5 tentatives échouées — persisté en DB (`LoginAttempts`)

### Performances (Semaines 9–10)
- **Révision 007** : extension `pg_trgm` + 4 index GIN (recherche ILIKE sur Students)
- 4 index composites : `StudentClassNumbers`, `Grades`, `StudentAttendance`, `StudentDues`
- Élimination N+1 dans `list_late_payers` : 6 sous-requêtes corrélées → 1 CTE + LEFT JOIN
- Pool metrics en temps réel dans `/api/health` (`active_connections`, `utilization_pct`)

### Gestion d'erreurs (Semaine 8)
- `error_codes.py` : 16 codes d'erreur normalisés (E-DB-xxx, E-AUTH-xxx, E-VALID-xxx, E-IO-xxx, E-NET-xxx)
- IDs d'opération uniques (8 chars hex) dans chaque message d'erreur UI
- Retry exponentiel x3 sur `OperationalError` dans `DatabaseManager` (0.5s → 1s → 2s)

### Migrations Alembic (Semaines 3–10)
| Révision | Description |
|----------|-------------|
| 001 | Schéma initial |
| 002 | Contraintes et dates académiques |
| 003 | Slots emploi du temps et présences |
| 004 | Discipline et créneaux |
| 005 | Portail parent et multi-école |
| 006 | Contraintes CHECK financières |
| 007 | Index de performance (pg_trgm + composites) |

---

## Corrections de bugs

- `staff_management.py` : remplacement de `print(f"Failed to copy photo")` par `AppLogger.error()`
- `api/auth.py` : `RuntimeError` au démarrage si `ELMALICK_API_SECRET` par défaut en production
- `api/main.py` : `allow_credentials=False` automatique si `ALLOWED_ORIGINS=*`

---

## Tests

- **944 tests** passent (0 échec)
- Couverture `api/auth.py` : 81%
- Couverture `security_utils.py` : 88%
- Couverture `src/data/finance_repo.py` : 100%

---

## Notes de migration

### Prérequis
```
Python 3.14+, PostgreSQL 16+, pg_trgm disponible (inclus par défaut)
```

### Variables d'environnement requises en production
```bash
ELMALICK_API_SECRET=<clé-forte-256-bits>   # OBLIGATOIRE
ALLOWED_ORIGINS=https://votre-domaine.com  # recommandé
ELMALICK_ENV=production
```

### Exécuter les migrations
```bash
alembic upgrade head   # applique 001 → 007
```

---

## Changements incompatibles (Breaking changes)

Aucun — la v2.0.0-rc1 est rétrocompatible avec les données v1.x.

---

## Contacts

| Rôle | Responsabilité |
|------|---------------|
| Développeur principal | Architecture, DB, API |
| Tech Lead | Sécurité, qualité, déploiement |
