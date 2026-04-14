import os
import json
from pathlib import Path


class DataLoader:

    def __init__(self):
        self.mode = os.getenv("DATA_MODE", "real")

        try:
            from backend.engine.config import DATA_ROOT
            self.data_root = DATA_ROOT
        except ImportError:
            self.data_root = Path(__file__).resolve().parents[2] / "backend/data"

    # =========================
    # RECIPES
    # =========================

    def load_recipes(self) -> list:
        if self.mode == "real":
            return self._load_recipes_real()
        elif self.mode == "fake":
            return self._load_recipes_fake()
        elif self.mode == "secure":
            return self._load_recipes_secure()
        else:
            raise ValueError(f"DATA_MODE inconnu : {self.mode!r}")

    def _load_recipes_real(self) -> list:
        path = self.data_root / "recipes" / "recipes.json"
        data = self._load_json(path)
        return data.get("recipes", data) if isinstance(data, dict) else data

    def _load_recipes_fake(self) -> list:
        path = Path(__file__).parent.parent.parent / "data_fake" / "recipes_fake_advanced.json"
        data = self._load_json(path)
        return data if isinstance(data, list) else data.get("recipes", [])

    def _load_recipes_secure(self) -> list:
        key  = os.getenv("SECRET_KEY")
        path = os.getenv("RECIPES_PATH")

        if not key or not path:
            raise EnvironmentError("DATA_MODE=secure requiert SECRET_KEY et RECIPES_PATH")

        from cryptography.fernet import Fernet

        cipher    = Fernet(key.encode())
        encrypted = Path(path).read_bytes()
        decrypted = cipher.decrypt(encrypted)
        data      = json.loads(decrypted.decode())

        return data.get("recipes", data) if isinstance(data, dict) else data

    # =========================
    # NUTRITION (SOURCE UNIQUE)
    # =========================

    def load_nutrition(self) -> dict:
        """
        Charge la base nutritionnelle unifiée.

        Source UNIQUE et obligatoire :
            nutrition/processed/nutrition_clean.json
        """
        path = self.data_root / "nutrition" / "processed" / "nutrition_clean.json"
        return self._load_json(path)

    # =========================
    # GENERIC
    # =========================

    def _load_json(self, path) -> dict | list:
        p = Path(path)

        if not p.exists():
            raise FileNotFoundError(f"Fichier introuvable : {p}")

        with open(p, encoding="utf-8") as f:
            return json.load(f)