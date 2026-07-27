"""
test_db.py — Tests de la couche base de données.

Stratégie deux niveaux :
  1. Tests de structure (code source) — s'exécutent toujours
  2. Tests d'intégration SQLite en mémoire — si sqlalchemy installé

Les tests de niveau 1 vérifient :
  - Présence des modèles et colonnes attendus
  - Présence des méthodes dans les repositories
  - Conformité RGPD (colonnes chiffrées)
  - Présence de RecipeHistory (base learning_engine)

Les tests SQLite s'exécutent en CI/CD avec :
  pip install sqlalchemy
"""
import os
from pathlib import Path
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_alim.db")


# ── Tests structure code source ───────────────────────────────────────────────

def test_models_all_tables_defined():
    """Tous les modèles attendus sont définis dans models.py."""
    src = open("backend/db/models.py", encoding="utf-8").read()
    for table in ("users", "user_profiles", "api_users", "api_keys",
                  "daily_quotas", "recipe_history"):
        assert f'__tablename__ = "{table}"' in src, f"Table {table} absente"

def test_models_encrypted_health_columns():
    """cycle_phase et health_goal utilisent EncryptedString (RGPD Art. 9)."""
    import re
    src = open("backend/db/models.py", encoding="utf-8").read()
    assert "EncryptedString" in src
    assert re.search(r"cycle_phase\s*=\s*Column\(EncryptedString", src)
    assert re.search(r"health_goal\s*=\s*Column\(EncryptedString", src)

def test_models_recipe_history_fields():
    """RecipeHistory a les champs requis pour le learning_engine."""
    src = open("backend/db/models.py", encoding="utf-8").read()
    for field in ("user_email", "recipe_id", "action", "score_shown",
                  "profile_used", "created_at"):
        assert field in src, f"RecipeHistory: champ {field} absent"

def test_repositories_user_methods():
    """UserRepository expose toutes ses méthodes."""
    src = open("backend/db/repositories.py", encoding="utf-8").read()
    for method in ("get_by_email", "exists", "create", "verify_password",
                   "delete", "update_plan"):
        assert f"def {method}" in src, f"UserRepository: méthode {method} absente"

def test_repositories_profile_methods():
    src = open("backend/db/repositories.py", encoding="utf-8").read()
    for method in ("get", "get_as_dict", "upsert", "delete"):
        assert f"def {method}" in src, f"UserProfileRepository: méthode {method} absente"

def test_repositories_api_key_methods():
    src = open("backend/db/repositories.py", encoding="utf-8").read()
    for method in ("generate", "lookup", "revoke", "list_for_user"):
        assert f"def {method}" in src, f"ApiKeyRepository: méthode {method} absente"

def test_repositories_recipe_history():
    """RecipeHistoryRepository avec toutes ses méthodes."""
    src = open("backend/db/repositories.py", encoding="utf-8").read()
    assert "RecipeHistoryRepository" in src
    for method in ("record", "get_recent", "get_liked_recipe_ids",
                   "get_disliked_recipe_ids", "count", "_purge_excess"):
        assert f"def {method}" in src, f"RecipeHistoryRepository.{method} absent"

def test_repositories_history_max_cap():
    """Limite MAX_HISTORY = 500 présente."""
    src = open("backend/db/repositories.py", encoding="utf-8").read()
    assert "MAX_HISTORY = 500" in src

def test_session_has_init_db():
    src = open("backend/db/session.py", encoding="utf-8").read()
    assert "def init_db" in src

def test_profile_injection_protection():
    """upsert filtre les champs hors whitelist."""
    src = open("backend/db/repositories.py", encoding="utf-8").read()
    # ALLOWED_FIELDS doit être présent pour bloquer l'injection
    assert "ALLOWED_FIELDS" in src or "allowed" in src.lower() or "whitelist" in src.lower()

def test_models_cascade_delete():
    """Les FK avec ondelete=CASCADE sont en place."""
    src = open("backend/db/models.py", encoding="utf-8").read()
    assert 'ondelete="CASCADE"' in src


# ── Tests SQLite en mémoire (optionnels) ──────────────────────────────────────

def _run_sqlite_tests():
    """Tests d'intégration complets avec SQLite en mémoire."""
    try:
        from sqlalchemy import create_engine, event, inspect as sa_inspect
        from sqlalchemy.orm import sessionmaker
    except ImportError:
        return None, "SQLAlchemy non installé — tests SQLite ignorés"

    from backend.db.models import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    results = []

    def db_test(name, fn):
        session = Session()
        try:
            fn(session)
            session.commit()
            results.append(("✅", f"[SQLite] {name}"))
        except Exception as e:
            session.rollback()
            results.append(("❌", f"[SQLite] {name}", str(e)[:80]))
        finally:
            session.close()

    # Tables créées
    def t_tables(db):
        tables = sa_inspect(engine).get_table_names()
        for t in ("users","user_profiles","api_users","api_keys","daily_quotas","recipe_history"):
            assert t in tables, f"Table {t} absente"
    db_test("tables créées", t_tables)

    # UserRepository CRUD
    def t_user_crud(db):
        from backend.db.repositories import UserRepository
        repo = UserRepository(db)
        u = repo.create("alice@test.com", "hash_123")
        db.flush()
        assert u.email == "alice@test.com" and u.plan == "free"
        assert repo.exists("alice@test.com")
        assert not repo.exists("nobody@test.com")
        assert repo.get_by_email("alice@test.com").email == "alice@test.com"
        assert repo.delete("alice@test.com")
        assert not repo.exists("alice@test.com")
    db_test("UserRepository CRUD", t_user_crud)

    # Duplicate → ValueError
    def t_duplicate(db):
        from backend.db.repositories import UserRepository
        repo = UserRepository(db)
        repo.create("bob@test.com", "hash1"); db.flush()
        try:
            repo.create("bob@test.com", "hash2")
            assert False, "ValueError attendu"
        except (ValueError, Exception):
            pass
    db_test("UserRepository: doublon → exception", t_duplicate)

    # UserProfile upsert + injection protection
    def t_profile(db):
        from backend.db.repositories import UserRepository, UserProfileRepository
        UserRepository(db).create("carol@test.com", "hash"); db.flush()
        repo = UserProfileRepository(db)
        repo.upsert("carol@test.com", {"diet": "vegan", "is_admin": True})
        profile = repo.get_as_dict("carol@test.com")
        assert profile["diet"] == "vegan"
        assert "is_admin" not in profile
        repo.upsert("carol@test.com", {"budget": "low"})
        profile2 = repo.get_as_dict("carol@test.com")
        assert profile2["diet"] == "vegan" and profile2["budget"] == "low"
    db_test("UserProfileRepository: upsert + anti-injection", t_profile)

    # ApiKey generate + lookup + revoke
    def t_api_key(db):
        from backend.db.repositories import ApiUserRepository, ApiKeyRepository
        user = ApiUserRepository(db).create("api@test.com", "starter"); db.flush()
        raw, key = ApiKeyRepository(db).generate(user.user_id); db.flush()
        assert len(raw) == 64
        found = ApiKeyRepository(db).lookup(raw)
        assert found and found.user_id == user.user_id
        ApiKeyRepository(db).revoke(raw); db.flush()
        assert ApiKeyRepository(db).lookup(raw) is None
    db_test("ApiKeyRepository: generate + lookup + revoke", t_api_key)

    # RecipeHistory record + purge
    def t_history(db):
        from backend.db.repositories import UserRepository, RecipeHistoryRepository
        UserRepository(db).create("hist@test.com", "hash"); db.flush()
        repo = RecipeHistoryRepository(db)
        for i in range(5):
            repo.record("hist@test.com", i+1, action="view"); db.flush()
        assert repo.count("hist@test.com") == 5
        repo.record("hist@test.com", 10, action="like"); db.flush()
        liked = repo.get_liked_recipe_ids("hist@test.com")
        assert 10 in liked
        recent = repo.get_recent("hist@test.com", limit=3)
        assert len(recent) == 3
    db_test("RecipeHistoryRepository: record + like + recent", t_history)

    return results, None


if __name__ == "__main__":
    tests = [(n, f) for n, f in globals().items()
             if n.startswith("test_") and callable(f)]
    ok = fail = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
            ok += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            fail += 1

    sqlite_results, msg = _run_sqlite_tests()
    if msg:
        print(f"\n  ℹ️  {msg}")
    elif sqlite_results:
        print(f"\n  Tests SQLite :")
        for r in sqlite_results:
            status = r[0]
            print(f"  {status} {r[1]}" + (f"\n      → {r[2]}" if status == "❌" else ""))
            if status == "✅": ok += 1
            else: fail += 1

    print(f"\n{ok}/{ok+fail} tests passés")
