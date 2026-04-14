# Conditions Générales d'Utilisation — ALIM v5

**Date d'entrée en vigueur :** 1er janvier 2026
**Responsable du traitement :** ALIM Platform

---

## 1. Objet du service

ALIM est une plateforme de recommandation culinaire végétarienne personnalisée.
Elle fournit des recommandations de recettes, des plans repas et des analyses
nutritionnelles basées sur les préférences et le profil de l'utilisateur.

## 2. Données collectées

| Donnée | Base légale | Durée |
|--------|------------|-------|
| Adresse e-mail | Contrat | Durée du compte |
| Régime alimentaire | Intérêt légitime | Durée du compte |
| Historique de navigation | Intérêt légitime | 6 mois glissants |
| Données de santé (cycle, objectif santé) | **Consentement explicite** | Révocable à tout moment |

## 3. Données de santé (RGPD Art. 9)

Les données de santé (phase du cycle menstruel, objectif santé médical) sont des
**données sensibles** au sens du RGPD. Leur collecte requiert votre **consentement
explicite** via `PATCH /profil/consent`.

Vous pouvez retirer ce consentement à tout moment. Les données seront alors effacées.

## 4. Vos droits

- **Droit d'accès** : `GET /profil/export` — télécharger toutes vos données
- **Droit de rectification** : `POST /profil/update`
- **Droit à l'effacement** : `DELETE /profil/` ou `DELETE /auth/account`
- **Droit à la portabilité** : `GET /profil/export` (format JSON)
- **Droit d'opposition** : contact responsable ci-dessous

## 5. Contact responsable du traitement

Pour exercer vos droits : **privacy@alim-platform.com**

## 6. Sécurité

- Données de santé chiffrées au repos (AES-128 Fernet)
- Mots de passe hashés (bcrypt)
- Tokens JWT avec expiration
- Rate limiting par IP et par utilisateur

## 7. Modifications

Ces CGU peuvent être mises à jour. La date d'entrée en vigueur sera modifiée.
L'utilisation continue du service vaut acceptation des nouvelles conditions.
