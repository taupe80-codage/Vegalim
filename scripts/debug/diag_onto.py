import json

with open("backend/data/nutrition/reference/ontology_v6.json", encoding="utf-8") as f:
    onto = json.load(f)

bases = onto["ingredients"]
print(f"Total bases : {len(bases)}\n")

TARGETS = [
    "flaxseed_oil","oil","egg","mushroom","mushroom_shiitake",
    "flaxseed","flaxseeds","flax_seeds","butter","butter_almond",
    "seitan","tempeh","dark_chocolate","chocolate","mirin",
    "milk_plant","flour","flax_egg","hard_boiled_egg","cashew",
    "almond","lin","oat","avoine",
]

print(f"{'Base':<45} Variants")
print("─"*75)
for t in TARGETS:
    if t in bases:
        item = bases[t]
        variants = list(item.keys()) if isinstance(item, dict) else ["(non-dict)"]
        print(f"  ✅ {t:<43} {variants}")
    else:
        print(f"  ❌ {t:<43}")

print("\n=== Recherche fuzzy ===")
for term in ["flax","egg","seitan","tempeh","choc","mirin","cashew","oat","butter","mushroom","shiitake","lin","milk"]:
    hits = sorted([k for k in bases if term in k.lower()])[:6]
    if hits:
        print(f"  '{term}' → {hits}")
