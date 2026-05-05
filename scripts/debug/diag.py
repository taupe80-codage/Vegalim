import json
from collections import Counter

with open('backend/data/nutrition/outputs/ciqual_flat_v3.json') as f:
    data = json.load(f)

for sev_class in ('physical_error', 'major_quality', 'data_quality'):
    hits = [
        (food['id'], food['name_fr'], i['check'], i.get('message',''),
         food.get('state',{}).get('process',{}).get('level1'))
        for food in data['foods_flat']
        for i in (food.get('_audit_issues') or [])
        if i.get('severity_class') == sev_class
    ]
    by_check = Counter(h[2] for h in hits)
    print(f"=== {sev_class} : {len(hits)} issues ===")
    for check, n in by_check.most_common():
        print(f"  {n:3d}  {check}")
    print()
    for fid, name, check, msg, l1 in sorted(hits, key=lambda x: x[2]):
        print(f"  [{check}]  [{l1:<14}]  {name[:42]:<42}  {msg[:80]}")
    print()
