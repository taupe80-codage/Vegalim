import json
import logging
import sys
from pathlib import Path

# Setup paths
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.core.data_io import load_recipes
from backend.engine.rule_engine.variants import vegan_variant
from backend.engine.rule_engine.diet import compute_diet_flags

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def main():
    recipes = load_recipes()
    logging.info(f"Loaded {len(recipes)} recipes for variant generation.")

    index_path = ROOT / "backend" / "data" / "config" / "vegan_variants_index.json"
    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)

    o_to_v = index.get('original_to_vegan', {})
    
    generated_count = 0
    rejected_count = 0
    max_vegan_id = 2000  # Start IDs from 2000 for safely isolated space
    
    for r in recipes:
        rid = str(r['id'])
        
        # 1. Skip if already tracked
        if rid in o_to_v:
            continue
            
        # 2. Skip if naturally vegan
        flags = r.get('diet_flags', {})
        if flags.get('vegan') or 'vegan' in r.get('tags', {}).get('diet', []):
            continue
            
        # 3. Generate variant candidate
        var_result = vegan_variant(r)
        
        if len(var_result['substitutions']) > 0:
            # 4. Strict Coherence validation
            # We mock a recipe structure with the new composition to pass it to the diet engine
            mock_recipe_for_eval = {"composition": var_result['recipe']['composition']}
            
            new_flags = compute_diet_flags(mock_recipe_for_eval)
            
            if new_flags.get("vegan") is True:
                # SUCCESS: Variant is fully vegan compliant
                vegan_id = f"vegan_var_{rid}"
                
                subs = {s['original']: s['substitute'] for s in var_result['substitutions']}
                title_fr = r.get('title_fr', '')
                if not title_fr and 'titles' in r:
                    title_fr = r['titles'].get('fr', '')
                v_title = title_fr + ' (Vegan)' if title_fr else f'{rid} (Vegan)'
                
                o_to_v[rid] = {
                    'vegan_id': vegan_id,
                    'subs': subs,
                    'vegan_title': v_title,
                    'confidence': 0.95  # Assured coherence
                }
                
                index.setdefault('vegan_to_original', {})[vegan_id] = {
                    'original_id': rid,
                    'original_title': title_fr
                }
                generated_count += 1
            else:
                # FAILURE: Substitution incomplete (e.g. real meat left over)
                rejected_count += 1
                
    index['total'] = len(o_to_v)
    index['original_to_vegan'] = o_to_v

    if generated_count > 0:
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    logging.info(f"Generation complete: {generated_count} coherent variants created.")
    logging.info(f"Rejections: {rejected_count} variants discarded due to non-vegan residual ingredients (incoherent).")

if __name__ == "__main__":
    main()
