"""patch_auto_correct_v3.py — patch 2 avec bytes exacts NFD"""
from pathlib import Path

target = Path("scripts/nutrition/auto_correct_v4_2.py")
raw = target.read_bytes()

# Patch 2 : ajouter ingredients_out[output_id] = item avant la sauvegarde
# Note : "suffixe\xcc\x81e" est NFD pour "suffixée"
old2 = (
    b'            # Mode auto \xe2\x86\x92 correction (utilise la cl\xc3\xa9 suffixe\xcc\x81e)\n'
    b'            logs.append(log_entry)\n'
    b'            if not DRY_RUN:\n'
    b'                item[clean_key] = round(ref_val, 2)\n'
    b'            stats["corrected"] += 1\n'
    b'\n'
    b'    # --- Sauvegarde ---\n'
)
new2 = (
    b'            # Mode auto \xe2\x86\x92 correction\n'
    b'            logs.append(log_entry)\n'
    b'            if not DRY_RUN:\n'
    b'                item[clean_key] = round(ref_val, 2)\n'
    b'            stats["corrected"] += 1\n'
    b'\n'
    b'        ingredients_out[output_id] = item\n'
    b'\n'
    b'    # --- Sauvegarde ---\n'
)

if old2 in raw:
    raw = raw.replace(old2, new2, 1)
    print("Patch 2 OK: ingredients_out collection added")
else:
    print("Patch 2 NOT FOUND")
    idx = raw.find(b"Mode auto")
    print(repr(raw[max(0,idx-5):idx+250]))

target.write_bytes(raw)
print(f"File written ({len(raw)} bytes)")
