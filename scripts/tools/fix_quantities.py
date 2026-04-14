import json
import re

with open(r'c:\Users\Samijo\Downloads\quantites_incoherentes.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixes_map = {}
for line in lines:
    line = line.strip()
    if not line: continue
    parts = [p.strip() for p in line.split('|')]
    if len(parts) == 3:
        rid, ing, val = parts
        
        # parse val (e.g. '40g', '220g', '1g')
        m = re.match(r'^(\d+)(.*)$', val)
        if m:
            q = int(m.group(1))
            u = m.group(2).strip()
            
            # Heuristics for conversion
            new_q = q
            new_u = 'piece' # default replacement unit
            
            if ing == 'garlic':
                if u == 'g':
                    if q >= 40:
                        new_q = q // 10  # 40g -> 4 pieces
                        new_u = 'gousse'
                    elif q <= 10:
                        new_q = q
                        new_u = 'gousse'
            elif ing == 'egg':
                if u == 'g' and q >= 55:
                    new_q = round(q / 55)
                    new_u = 'piece'
                elif u == 'g' and q < 10:
                    new_q = q
                    new_u = 'piece'
            elif ing == 'potato':
                if u == 'g':
                    if q >= 600:
                        new_q = round(q / 150)
                    new_u = 'piece'
            elif ing == 'tomato':
                if u == 'g':
                    if q >= 600:
                        new_q = round(q / 120)
                    new_u = 'piece'
            elif ing == 'onion':
                if u == 'g':
                    if q < 10:
                        new_q = q
                    else:
                        new_q = round(q / 150)
                    new_u = 'piece'
            elif ing == 'carrot':
                if u == 'g':
                    if q < 10:
                        new_q = q
                    else:
                        new_q = round(q / 100)
                    new_u = 'piece'
            
            fixes_map.setdefault(rid, {})[ing] = {
                'old_q': q, 'old_u': u,
                'new_q': new_q, 'new_u': new_u
            }

with open('backend/data/recipes/recipes.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

updated_recipes = 0
for r in db['recipes']:
    rid = str(r['id'])
    if rid in fixes_map:
        modified = False
        for c in r.get('composition', []):
            ing = c.get('ingredient', '')
            if ing in fixes_map[rid]:
                fix = fixes_map[rid][ing]
                # verify it matches the bug
                if c.get('quantity') == fix['old_q'] and c.get('unit') == fix['old_u']:
                    c['quantity'] = fix['new_q']
                    c['unit'] = fix['new_u']
                    modified = True
        
        if modified:
            updated_recipes += 1

with open('backend/data/recipes/recipes.json', 'w', encoding='utf-8') as f:
    json.dump(db, f, indent=2, ensure_ascii=False)

print(f'Fixed {updated_recipes} recipes containing incoherent quantities.')
