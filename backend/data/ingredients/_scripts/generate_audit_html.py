#!/usr/bin/env python3
"""
generate_audit_html.py
Régénère audit_names_v2.html depuis ingredients_tree_enriched_v2.json.
Nouveautés v3 :
  - Données INGS à jour
  - VOCAB reconstruit depuis les vraies valeurs du tree
  - Création de nouvelles clés d'axe (champ libre)
  - Saisie de nouvelles valeurs libres pour axes existants
"""
import json, re
from pathlib import Path
from collections import defaultdict, OrderedDict

BASE      = Path(__file__).resolve().parent.parent
TREE_FILE = BASE / 'ingredients_tree.json'
OUT_FILE  = BASE / 'audit_names_v2.html'
OLD_FILE  = BASE / 'audit_names_v2.html'

tree = json.load(open(TREE_FILE, encoding='utf-8'))

# ── 1. Construire la liste INGS ───────────────────────────────────────────
ings = []
for cat1 in tree['categories']:
    for cat2 in cat1['subcategories']:
        for ing in cat2.get('ingredient_groups', []):
            variants = []
            for v in ing.get('variants', []):
                variants.append({
                    'id':            v.get('id',''),
                    'source':        v.get('source',''),
                    'source_id':     v.get('source_id',''),
                    'source_name_fr': v.get('source_name_fr') or '',
                    'source_name_en': v.get('source_name_en') or '',
                    'name_fr':       v.get('name_fr',''),
                    'name_en':       v.get('name_en',''),
                    'axes_fr':       v.get('axes_fr', {}),
                })
            ings.append({
                'cat1_id':    cat1.get('id',''),
                'cat1_label': cat1.get('label',''),
                'cat2_id':    cat2.get('id',''),
                'cat2_label': cat2.get('label',''),
                'id':                   ing.get('id',''),
                'canonical_name_fr':    ing.get('canonical_name_fr',''),
                'canonical_name_en':    ing.get('canonical_name_en',''),
                'axes_fr':              ing.get('axes_fr', {}),
                'variants':             variants,
            })

# Tri alphabétique par canonical_name_fr à l'intérieur de chaque cat2
import unicodedata, re
def sort_key(ing):
    s = ing.get('canonical_name_fr','').lower().strip()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return (ing['cat1_id'], ing['cat2_id'], s)

ings.sort(key=sort_key)
print(f'INGS: {len(ings)} ingredients, {sum(len(i["variants"]) for i in ings)} variants')

# ── 2. Construire VOCAB depuis les vraies valeurs du tree ─────────────────
vocab_sets = defaultdict(set)
for cat1 in tree['categories']:
    for cat2 in cat1['subcategories']:
        for ing in cat2.get('ingredient_groups', []):
            for obj in [ing] + ing.get('variants', []):
                axes = obj.get('axes_fr', {})
                if not isinstance(axes, dict): continue
                for k, v in axes.items():
                    if not v: continue
                    vals = v if isinstance(v, list) else [v]
                    for val in vals:
                        vocab_sets[k].add(str(val))

# Ordre préférentiel des axes
AXES_ORDER = [
    "etat_cuisson","etat_thermique","forme","partie",
    "conditionnement","egouttage","milieu_conservation",
    "assaisonnement","traitement","maturite","teneur_MG",
    "sodium","origine","procede_cuisson"
]
# Compléments fixes utiles qui peuvent ne pas apparaître dans le tree
VOCAB_EXTRA = {
    "etat_cuisson":     ["cru","bouilli","cuit","grillé","rôti","sauté","vapeur","étouffée","à cuire","grillé à sec","précuit","frit","au four","dur","au plat","à la coque","brouillé","poché"],
    "etat_thermique":   ["frais","séché","déshydraté","réhydraté","UHT","surgelé","congelé","pasteurisé","mature"],
    "forme":            ["farine","épice","huile","pâte","jus","entier","poudre","confiture","yaourt","herbe fraîche","beurre","purée","liquide","lait","grain long","concentré","tranché","râpé","bloc","extrait","grain moyen","compote","herbe séchée","crémeux","flocons","gelée","concassé","grain court","crème de fruit","croquant","pastilles","petits morceaux","comprimé","paillettes","broyé","crème","eau végétale","fouetté","granulé","confit","émietté","moulu","steel cut","roulé"],
    "partie":           ["graine","feuille","pelé","pelure","fleur","racine","dénoyauté","graine entière","chair","gousse","pousse","tige","tubercule","pépins","avec peau","sans peau","avec graines","sans graines","chair+peau","chair sans peau"],
    "conditionnement":  ["conserve","préemballé","appertisé","UHT","rayon frais","commercial","pasteurisé","sous pression","sous vide","tablette"],
    "assaisonnement":   ["salé","sans sel","sans sucre","sucré","aromatisé","épicé","nature"],
    "traitement":       ["végétal","nature","allégé en gras","germé","brut","non enrichi","non blanchi","enrichi","écrémé","blanchi","fermenté","sans gluten","étuvé","demi-écrémé","instantané","iodé","confit","décortiqué","réduit en sodium","gras ajouté","faible en sodium","fumé","affiné","décaféiné","distillé","fluoré","texturé","raffiné","vierge","élevé en gras","préparé","réduit en lactose","extra vierge","non enrichi chimiquement","grill é à l'huile","grillé à sec"],
    "maturite":         ["bébé","mature","trop mûr","mûr","pas mûr"],
    "teneur_MG":        ["entier","allégé","écrémé","demi-écrémé","0%","allégé en gras","élevé en gras","1","2-3","12-20","30"],
    "origine":          ["vache","brebis","chèvre","bufflonne","végétal"],
    "egouttage":        ["égoutté","à l'huile"],
    "milieu_conservation": ["au vinaigre","à l'huile","dans l'eau","dans sirop"],
    "procede_cuisson":  ["à sec","à l'huile"],
}

vocab = {}
for key in AXES_ORDER:
    merged = set(VOCAB_EXTRA.get(key, []))
    merged |= vocab_sets.get(key, set())
    vocab[key] = sorted(merged)

# Axes supplémentaires trouvés dans le tree mais pas dans AXES_ORDER
for key in sorted(vocab_sets.keys()):
    if key not in AXES_ORDER:
        merged = set(VOCAB_EXTRA.get(key, []))
        merged |= vocab_sets[key]
        vocab[key] = sorted(merged)

print(f'VOCAB: {len(vocab)} axes')

# ── 3. Lire le template HTML existant ────────────────────────────────────
with open(OLD_FILE, encoding='utf-8') as f:
    old = f.read()

pre_ings   = old[:old.find('const INGS = [')]
vocab_start = old.find('const VOCAB = {')
axes_order_end = old.find('];', old.find('const AXES_ORDER = [')) + 2
# JS restant après AXES_ORDER
js_rest = old[axes_order_end : old.rfind('</script>')]
html_footer = old[old.rfind('</script>'):]

# ── 4. Patcher le JS : ajouter support nouvelle clé / nouvelle valeur ─────
# On modifie :
# a) Le handler 'change' sur ax-new-key → afficher champ texte si __new__
# b) Le handler 'click' sur ax-new-confirm → lire champ texte si __new__
# c) buildCard : ajouter option "➕ Nouvelle clé..." dans ax-new-key select
#                ajouter option "✏️ Saisir..." dans ax-new-val select

# Patch a : changer le handler change pour ax-new-key
OLD_CHANGE = """  const nk = e.target.closest('.ax-new-key');
  if (nk) {
    const key = nk.value;
    const form = nk.closest('.ax-new-inline');
    const valSel = form.querySelector('.ax-new-val');
    valSel.innerHTML = (VOCAB[key]||[]).map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join('');
    return;
  }"""
NEW_CHANGE = """  const nk = e.target.closest('.ax-new-key');
  if (nk) {
    const key = nk.value;
    const form = nk.closest('.ax-new-inline');
    const valSel = form.querySelector('.ax-new-val');
    const newKeyInput = form.querySelector('.ax-new-key-text');
    // Afficher/masquer champ texte libre pour nouvelle clé
    if (newKeyInput) newKeyInput.style.display = key === '__new__' ? 'inline-block' : 'none';
    if (key === '__new__') {
      valSel.innerHTML = '<option value="__free__">✏️ Saisir valeur...</option>';
    } else {
      valSel.innerHTML = (VOCAB[key]||[]).map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join('')
        + '<option value="__free__">✏️ Saisir valeur libre...</option>';
    }
    const newValInput = form.querySelector('.ax-new-val-text');
    if (newValInput) newValInput.style.display = 'none';
    return;
  }
  // Afficher/masquer champ valeur libre
  const nv = e.target.closest('.ax-new-val');
  if (nv) {
    const form = nv.closest('.ax-new-inline');
    const newValInput = form.querySelector('.ax-new-val-text');
    if (newValInput) newValInput.style.display = nv.value === '__free__' ? 'inline-block' : 'none';
    return;
  }"""

js_rest = js_rest.replace(OLD_CHANGE, NEW_CHANGE, 1)

# Patch b : changer le handler click sur ax-new-confirm pour lire les champs libres
OLD_CONFIRM = """  const nc = e.target.closest('.ax-new-confirm');
  if (nc) {
    const ingId = nc.dataset.ing;
    const form  = nc.closest('.ax-new-inline');
    const key   = form.querySelector('.ax-new-key').value;
    const val   = form.querySelector('.ax-new-val').value;
    if (!key || !val) return;"""
NEW_CONFIRM = """  const nc = e.target.closest('.ax-new-confirm');
  if (nc) {
    const ingId = nc.dataset.ing;
    const form  = nc.closest('.ax-new-inline');
    const rawKey = form.querySelector('.ax-new-key').value;
    const rawVal = form.querySelector('.ax-new-val').value;
    // Résoudre clé libre
    const keyInput = form.querySelector('.ax-new-key-text');
    const key = rawKey === '__new__' ? (keyInput ? keyInput.value.trim() : '') : rawKey;
    // Résoudre valeur libre
    const valInput = form.querySelector('.ax-new-val-text');
    const val = rawVal === '__free__' ? (valInput ? valInput.value.trim() : '') : rawVal;
    if (!key || !val) return;"""

js_rest = js_rest.replace(OLD_CONFIRM, NEW_CONFIRM, 1)

# Patch c : dans buildCard, ajouter l'option __new__ dans newKeyOpts et le champ texte
OLD_KEYOPTS = """  const availAxes = [...AXES_ORDER, ...Object.keys(VOCAB).filter(k=>!AXES_ORDER.includes(k))]
    .filter(k => !usedAxes.has(k));"""
NEW_KEYOPTS = """  const availAxes = [...AXES_ORDER, ...Object.keys(VOCAB).filter(k=>!AXES_ORDER.includes(k))]
    .filter(k => !usedAxes.has(k));
  // Ajouter option nouvelle clé libre
  availAxes.push('__new__');"""

js_rest = js_rest.replace(OLD_KEYOPTS, NEW_KEYOPTS, 1)

# Trouver où newKeyOpts est construit et la ligne du select ax-new-key
OLD_NEWOPTS = """  const newKeyOpts = availAxes.map(k => `<option value="${esc(k)}">${esc(k)}</option>`).join('');"""
NEW_NEWOPTS = """  const newKeyOpts = availAxes.map(k =>
    k === '__new__'
      ? `<option value="__new__">➕ Nouvelle clé...</option>`
      : `<option value="${esc(k)}">${esc(k)}</option>`
  ).join('');"""

js_rest = js_rest.replace(OLD_NEWOPTS, NEW_NEWOPTS, 1)

# Ajouter le champ texte libre dans le HTML de la zone ax-new-inline
OLD_AX_FORM = """<select class="ax-new-key" data-ing="${ing.id}">${newKeyOpts}</select>
        <select class="ax-new-val" data-ing="${ing.id}"></select>
        <button class="ax-new-confirm" data-ing="${ing.id}">OK</button>"""
NEW_AX_FORM = """<select class="ax-new-key" data-ing="${ing.id}">${newKeyOpts}</select>
        <input type="text" class="ax-new-key-text" placeholder="nom clé..." style="display:none;width:110px;font-size:11px;padding:2px 5px;border:1px solid #fcd34d;border-radius:3px;background:#fffbeb">
        <select class="ax-new-val" data-ing="${ing.id}"></select>
        <input type="text" class="ax-new-val-text" placeholder="valeur libre..." style="display:none;width:120px;font-size:11px;padding:2px 5px;border:1px solid #fcd34d;border-radius:3px;background:#fffbeb">
        <button class="ax-new-confirm" data-ing="${ing.id}">OK</button>"""

js_rest = js_rest.replace(OLD_AX_FORM, NEW_AX_FORM, 1)

# ── 5. Assembler le nouveau fichier ──────────────────────────────────────
ings_json  = json.dumps(ings, ensure_ascii=False)
vocab_json = json.dumps(vocab, ensure_ascii=False)
axes_order_json = json.dumps(AXES_ORDER, ensure_ascii=False)

new_html = (
    pre_ings
    + 'const INGS = ' + ings_json + ';\n'
    + 'const VOCAB = ' + vocab_json + ';\n'
    + 'const AXES_ORDER = ' + axes_order_json + ';\n'
    + js_rest
    + html_footer
)

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    f.write(new_html)

print(f'Fichier généré : {OUT_FILE}')
print(f'Taille : {len(new_html)//1024} KB')
