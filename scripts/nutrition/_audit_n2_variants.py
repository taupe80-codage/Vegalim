import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
n2 = json.loads(Path('backend/data/nutrition/processed/nutrition_v2.json').read_text(encoding='utf-8'))
bases = n2.get('ingredients', {})
total_variants = sum(len(b.get('variants', {})) for b in bases.values())
print(f'Bases n2       : {len(bases)}')
print(f'Total variants : {total_variants}')
with_axes, no_axes = 0, 0
examples = []
for bk, b in bases.items():
    for vk, vr in b.get('variants', {}).items():
        if not isinstance(vr, dict): continue
        axes = vr.get('axes') or {}
        if axes: with_axes += 1
        else: no_axes += 1
        if len(examples) < 5 and axes:
            examples.append((bk, vk, vr.get('_source'), vr.get('_source_id'),
                             axes, vr.get('_v32_ing_id'), vr.get('_v32_var_id')))
print(f'Avec axes      : {with_axes}')
print(f'Sans axes      : {no_axes}')
print()
for bk, vk, src, sid, axes, iid, vid in examples:
    print(f'  {bk}/{vk}')
    print(f'    src={src}#{sid}  axes={axes}')
    print(f'    v32_ing={iid}  v32_var={vid}')
