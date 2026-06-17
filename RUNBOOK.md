# Runbook — El Malick Gest v2.0.0-rc1

**Dernière mise à jour**: 25 mai 2026
**Audience**: Développeur principal, Tech Lead

---

## 1. Déploiement initial (Production)

### Prérequis
- Python 3.14+ installé, `.venv` créé
- PostgreSQL 16+ actif et accessible
- `pg_dump` / `psql` dans le PATH

### Étapes de déploiement

```bash
# 1. Cloner / mettre à jour le dépôt
git pull origin main

# 2. Installer les dépendances
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Configurer les variables d'environnement
set ELMALICK_API_SECRET=<clé-forte>
set ALLOWED_ORIGINS=https://votre-domaine.com
set ELMALICK_ENV=production
set DB_HOST=localhost
set DB_PORT=5432
set DB_NAME=elmalick_db
set DB_USER=elmalick_user
set DB_PASSWORD=<mot-de-passe-fort>

# 4. Appliquer les migrations Alembic
.venv\Scripts\python.exe -m alembic upgrade head
# Résultat attendu: Running upgrade ... -> 009

# 5. Vérifier la dérive de schéma (optionnel)
.venv\Scripts\python.exe -c "from database_setup import DatabaseManager; db = DatabaseManager(); db.initialize()"

# 6. Lancer l'application de bureau
.venv\Scripts\python.exe main_dashbord.py

# 7. Lancer l'API REST
.venv\Scripts\uvicorn.exe api.main:app --host 0.0.0.0 --port 8000 --workers 2
```

### Smoke tests post-déploiement

```bash
# Tests automatisés (944 attendus)
.venv\Scripts\python.exe -m pytest tests/ -p no:qt -q --tb=short

# Vérification API
curl http://localhost:8000/api/health
# Attendu: {"status":"ok","database":"connected",...}
```

---

## 2. Mise à jour (Upgrade)

```bash
# 1. Sauvegarde AVANT toute migration
python auto_backup.py   # ou via l'interface système

# 2. Mettre à jour le code
git pull origin main

# 3. Appliquer uniquement les nouvelles migrations
.venv\Scripts\python.exe -m alembic upgrade head

# 4. Redémarrer les services
# (arrêter uvicorn, relancer avec la nouvelle version)
```

---

## 3. Rollback (retour arrière en < 30 minutes)

### Rollback de migration (1 révision en arrière)

```bash
# Vérifier la révision actuelle
.venv\Scripts\python.exe -m alembic current

# Reculer d'une révision
.venv\Scripts\python.exe -m alembic downgrade -1

# Revenir à la version précédente du code
git checkout <commit-précédent>

# Relancer les services
```

### Rollback complet (restauration depuis sauvegarde)

```bash
# 1. Stopper les services
# 2. Identifier la sauvegarde à restaurer (dans backups/ ou racine)
# 3. Restaurer
psql -h HOST -p PORT -U USER -d elmalick_db -f backups/backup_auto_YYYYMMDD_HHMMSS.sql

# 4. Relancer les services
# Durée estimée: 5 minutes | Cible RTO: 30 minutes
```

---

## 4. Surveillance (Monitoring)

### Vérification de l'état

| Source | Ce qu'on vérifie | Fréquence |
|--------|-----------------|-----------|
| `GET /api/health` | DB connectée, latence, pool | Quotidien |
| `logs/app_YYYYMMDD.log` | Erreurs [E-DB-xxx], [E-AUTH-xxx] | Quotidien |
| `AuditLogs` table | Actions inhabituelles | Hebdomadaire |
| `pg_stat_activity` | Connexions actives | Si lenteur |

### Seuils d'alerte

| Indicateur | Seuil d'alerte | Action |
|------------|---------------|--------|
| `db_latency_ms` | > 500 ms | Vérifier pg_stat_activity, indexes |
| `pool.utilization_pct` | > 80% | Augmenter `_POOL_MAX_CONN` |
| Erreurs E-DB-002 répétées | > 3 en 5 min | Vérifier la connexion PostgreSQL |
| Échecs d'authentification | > 10 en 1 min | Suspecter attaque brute force |

---

## 5. Gestion des incidents

### P0 — Application inaccessible

1. Vérifier les logs : `logs/app_*.log`
2. Vérifier PostgreSQL : `psql -h HOST -U USER -c "SELECT 1"`
3. Si DB inaccessible → Rollback depuis sauvegarde (section 3)
4. Si code corrompu → `git stash` ou rollback de commit

### P1 — Données corrompues ou perte partielle

1. Stopper immédiatement les écritures (arrêter l'API et l'application)
2. Identifier la fenêtre de corruption dans les `AuditLogs`
3. Restaurer depuis la dernière sauvegarde valide
4. Rejouer les transactions manquantes si possible

### P2 — Dégradation des performances

1. Vérifier `/api/health` → `db_latency_ms` et `pool.utilization_pct`
2. Exécuter `python -m services.performance_monitor` pour un rapport baseline
3. Identifier les requêtes lentes dans `pg_stat_statements`
4. Appliquer les index manquants si nécessaire

---

## 6. Contacts d'escalade

| Type d'incident | Contact principal | Contact secondaire |
|----------------|------------------|-------------------|
| Base de données | Développeur principal | DBA |
| Sécurité / intrusion | Tech Lead | Responsable IT |
| API REST / intégration | Développeur principal | Tech Lead |
| Application de bureau | Développeur principal | Support utilisateurs |

---

## 7. Commandes de référence rapide

```bash
# Tester les migrations
alembic upgrade head
alembic downgrade -1 && alembic upgrade head

# Vérifier la couverture de tests
pytest tests/ -p no:qt --cov=security_utils --cov=api.auth --cov=src.data.finance_repo -q

# Générer un rapport de performance
python -m services.performance_monitor

# Vérifier les erreurs récentes
Select-String -Path logs\app_*.log -Pattern "\[E-DB|E-AUTH|ERROR" | Select-Object -Last 20
```
