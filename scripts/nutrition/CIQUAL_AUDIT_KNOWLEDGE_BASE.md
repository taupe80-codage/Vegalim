# CIQUAL Pipeline — Base de connaissances audit
> `build_ciqual_flat_v3.py` — maintenu à jour au fil des sessions  
> Dernière mise à jour : v6.15 (avril 2026)

---

## Conventions CIQUAL à connaître

| Fait | Détail |
|---|---|
| **Base d'expression** | Tous les macros sur poids frais (100g), **sauf** `fiber_g` pour les items `dried` → exprimé sur matière sèche |
| **Glucides disponibles** | CIQUAL FR utilise le système des "glucides disponibles" (excluent les fibres) — `carbs_g` ≠ `carbs_total` |
| **Polyols dans carbs_g** | `carbs_g` **inclut** les polyols. `polyols_g` est un champ séparé mais redondant si inclus dans carbs |
| **LOD/2 convention** | Valeurs `< X` encodées à `X/2`. Pour les AGS courts (C4:0–C14:0), LOD typique = 0.01g → valeur = 0.005g |
| **Mesures indépendantes** | CIQUAL mesure chaque nutriment sur des aliquots différents → les sous-totaux ne sont pas contraints arithmétiquement |
| **Aliments moyens** | `generic_type="aliment_moyen"` = agrégat inter-lots. Leurs sous-fractions (sucres, FA, vitamines) ne sont **pas co-mesurées** → incohérences structurelles attendues |
| **Facteurs énergétiques** | Règlement UE 1169/2011 : protéines 17 kJ/g · lipides 37 kJ/g · glucides 17 kJ/g · fibres 8 kJ/g · alcool 29 kJ/g · acides organiques 13 kJ/g · polyols 10 kJ/g |

---

## Checks d'audit — catalogue des anomalies connues

### ✅ `fiber_vs_carbs` — 11 vrais positifs résiduels irréductibles

| Item | fiber | carbs | Motif |
|---|---|---|---|
| Romarin, Thym frais | 14.0–14.1 | 6.6–10.5 | Herbes ligneuses, fibres structurelles élevées |
| Estragon frais | 6.2 | 4.1 | water=None, rebase impossible |
| Olive noire à l'huile, Tapenade, Moutarde | 4.5–11.6 | 2.2–4.33 | Fibres pectiques naturellement > glucides nets |
| Noisette grillée salée | 9.43 | 7.67 | dried water=None, rebase impossible |
| Mélange graines grillées | 10.5 | 9.69 | water=None, rebase impossible |
| Haricot coco/blanc/flageolet cuits | 13.8–15.8 | 12.0–13.7 | Delta ≤ 2.1g, ratio 1.15 — légumineuses réhydratées |

**Règle :** `fiber > carbs` est normal pour (1) légumes à water ≥ 75%, (2) items dried/lowwater post-rebase, (3) aliments quasi-acarbonés (carbs < 1g).

---

### ✅ `fiber_vs_carbs_postdry` — 55 items, severity `info`

Items dried + quasi-secs (water < 15%) post-rebase où fiber > carbs persiste. Biologiquement cohérent pour épices, algues, oléagineux concentrés. Non actionnable.

---

### ✅ `omega_vs_pufa` — 206 items, downgraded `info`

Σ(ALA+EPA+DHA+ARA+linoléique) mesurés sur aliquots séparés > PUFA total mesuré globalement. Non co-contraints dans CIQUAL. Fréquent sur fruits, légumes, produits laitiers, huiles.

---

### ✅ `salt_sodium` — 126 items, downgraded `info`

Sel mesuré par **conductimétrie** vs sodium par **absorption atomique** → deux méthodes indépendantes. Divergence attendue notamment pour : aliments transformés, fermentés, produits à Na trace (confiture, bonbons), herbes aromatiques.

---

### ✅ `chloride_sodium_balance` — 139 items, downgraded `info`

Cl organique + KCl dans épices, laits, fromages, algues — non issus de NaCl. Ratio Cl/Na ≠ 1.542 par nature. Très fréquent sur produits laitiers (Cl naturel du lait ~97–110 mg/100g).

---

### ✅ `retinol_vita_rae` — 0 après fix (seuil absolu > 5 µg)

CIQUAL calcule la RAE en incluant **alpha-carotène et bêta-cryptoxanthine** (absents du schéma). Pour céréales, riz, jus : retinol=0, bcar=None → rae ∈ {1.25, 2.08} µg uniquement via caroténoïdes mineurs. Delta 100% mais différence absolue < 3 µg → non significatif (< 0.5% AJR).

---

### ✅ `fa_sfa_subfractions` — 1 résiduel (Crudité aliment moyen)

**Cause principale résolue :** C4:0–C14:0 sont quasi-systématiquement sous LOD dans légumes/céréales (valeur 0.005 = LOD/2). Les exclure de la somme élimine ~45 faux positifs. La somme ne retient que les champs absents de `dl` (mesures réelles).

**Résiduel :** Crudité aliment moyen (25616) — AGS courts réellement mesurés à 0.011–0.013g → exclu via EXCL_CODES_HARD.

---

### ✅ `vit_d_subforms` — 0 après exclusion

Seul item concerné : `ciqual_24999` Dessert (aliment moyen) — D2+D3=0.179 > total=0.16. Exclu via EXCL_CODES_HARD. Inutilisable dans ALIM (trop générique).

---

### ✅ `energy_check` — 0 après fix polyols (v6.15)

**Cause racine :** `carbs_g` inclut les polyols dans CIQUAL, mais leur facteur énergétique est 10 kJ/g vs 17 kJ/g pour les glucides. L'ancienne formule additionnait `carbs×17 + polyols×10` → double-comptage.

**Fix appliqué :** `carbs_net = carbs_g - polyols_g`, puis `carbs_net×17 + polyols×10`.

| Item | polyols_g | delta avant | delta après |
|---|---|---|---|
| Chewing-gum sans sucres (31054) | 65.7 | 130% | 0.0% |
| Pastille rafraîchissante (31125) | 94.6 | 161% | 0.4% |
| Bonbon dur sans sucres (31128) | 95.6 | 166% | 0.3% |
| Abricot sec (13001) | 22.6 (sorbitol naturel) | 36% | 2.0% |
| Abricot sec moelleux (13623) | 17.6 | 34% | 1.3% |
| Champignon sauté (20125) | 3.0 | 32% | 0.2% |
| Céleri-rave bouilli (20315) | 1.8 | 27% | 0.5% |

---

### ✅ `sugar_subfractions` — 0 après skip aliments_moyens (v6.15)

Tous les items concernés étaient `generic_type="aliment_moyen"` : Fromage (12999), Boisson végétale (18112), Légume cuit (20499), Légume sec cuit (20700), Crudité (25616 — exclu EXCL_CODES_HARD).
Sous-fractions sucres mesurées sur lots analytiques indépendants → incohérence structurelle. `generic_type` désormais passé explicitement à `run_audit`, check skipé pour les aliments moyens.

---

### ✅ `fa_balance` — 0 après seuil fat_g < 0.1g (v6.15)

`ciqual_19050` Lait écrémé UHT — fat_g=0.021g mais SFA+MUFA+PUFA=0.17g. FA sub-fractions = valeurs LOD/2 issues d'un lot différent (lait entier probable), non représentatives du fat réel. Check skipé quand `fat_g < 0.1g`.

---

### ✅ `mass_balance` — 0 après exclusion (v6.15)

| Code | Item | Sigma | Motif |
|---|---|---|---|
| 31064 | Édulcorant saccharine | 3.0g (écart 97g) | Additif pur, macros quasi nuls → EXCL_CODES_HARD |
| 31047 | Gélifiant pour confitures | 84.2g (écart 15.8g) | Pectine/agar, minéraux non capturés → EXCL_CODES_HARD |

---

## Codes exclus (EXCL_CODES_HARD) — raisons

| Code | Nom | Raison |
|---|---|---|
| 24999 | Dessert (aliment moyen) | D2+D3 > vitamin_d_total, trop générique |
| 25616 | Crudité, sans assaisonnement (aliment moyen) | AGS sous-fractions > total, trop générique |
| 31064 | Édulcorant à la saccharine | mass_balance critique (Sigma=3g), additif pur |
| 31047 | Gélifiant pour confitures | mass_balance 84.2g, additif technologique |

---

## Rebase fiber — logique v6.9

```
water_g disponible + level1 == "dried"     → rebase, _fiber_rebase_reason = "dried"
water_g < 15 + level1 != "dried"           → rebase, _fiber_rebase_reason = "lowwater"
water_g >= 75                              → exception silencieuse fiber_vs_carbs
carbs_g < 1.0                              → exception silencieuse fiber_vs_carbs
```

Items lowwater typiques : son (water~5-10%), café moulu, lin, thé, cacao, sésame grillé, graines.

---

## Énergie — formule correcte avec polyols

```python
# ATTENTION : carbs_g inclut les polyols dans CIQUAL
# Il faut déduire polyols_g de carbs avant d'appliquer le facteur glucides
polyols = nut.get("polyols_g") or 0
carbs_net = max(0, carbs - polyols)
energy = (protein * 17 + carbs_net * 17 + fat * 37 +
          fiber * 8 + alcohol * 29 + organic_acids * 13 + polyols * 10)
```

---

## Statistiques pipeline (v6.15 — état final)

| Indicateur | Valeur |
|---|---|
| Total foods (net) | 1650 |
| Items avec issues | 436 |
| physical_error | **0** |
| major_quality | **0** |
| data_quality | **11** (irréductibles — tous fiber_vs_carbs) |
| info | ~500 (structurels analytiques documentés) |

### Évolution data_quality v6.8 → v6.15

| Version | Patch | data_quality |
|---|---|---|
| v6.8 | baseline | 653 |
| v6.9 | fiber_vs_carbs stratifié + rebase lowwater | 460 |
| v6.10–v6.11 | vit_d, retinol_vita_rae | 410 |
| v6.12 | fa_sfa_subfractions LOD/2 | ~365 |
| v6.13 | omega/salt/chloride → info | ~12 |
| v6.14 | exclusion aliments_moyens incohérents | 12 |
| **v6.15** | energy, sugar, fa_balance, mass_balance | **11** |
