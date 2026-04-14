import os

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    
    # 1. title_fr
    content = content.replace('r.get("title_fr", "")', 'r.get("titles", {}).get("fr", "")')
    content = content.replace('r.get("title_fr")', 'r.get("titles", {}).get("fr")')
    content = content.replace('recipe.get("title_fr", "")', 'recipe.get("titles", {}).get("fr", "")')
    content = content.replace('recipe.get("title_fr")', 'recipe.get("titles", {}).get("fr")')
    content = content.replace('r1.get("title_fr", "")', 'r1.get("titles", {}).get("fr", "")')
    content = content.replace('r2.get("title_fr", "")', 'r2.get("titles", {}).get("fr", "")')
    content = content.replace('r1.get("title_fr")', 'r1.get("titles", {}).get("fr")')
    content = content.replace('r2.get("title_fr")', 'r2.get("titles", {}).get("fr")')
    content = content.replace('chosen.get("title_fr", "")', 'chosen.get("titles", {}).get("fr", "")')
    content = content.replace('new_rec.get("title_fr")', 'new_rec.get("titles", {}).get("fr")')
    
    # original title
    content = content.replace('r.get("title_original", "")', 'r.get("titles", {}).get("original", "")')
    content = content.replace('r.get("title_original")', 'r.get("titles", {}).get("original")')
    content = content.replace('recipe.get("title_original", "")', 'recipe.get("titles", {}).get("original", "")')
    content = content.replace('recipe.get("title_original")', 'recipe.get("titles", {}).get("original")')
    content = content.replace('r1.get("title_original", "")', 'r1.get("titles", {}).get("original", "")')
    content = content.replace('r2.get("title_original", "")', 'r2.get("titles", {}).get("original", "")')
    content = content.replace('new_rec.get("title_original")', 'new_rec.get("titles", {}).get("original")')

    # 2. total_time_min
    content = content.replace('r.get("total_time_min")', 'r.get("timing", {}).get("total_min")')
    content = content.replace('recipe.get("total_time_min")', 'recipe.get("timing", {}).get("total_min")')

    # 3. iconic_score
    content = content.replace('r.get("iconic_score"', 'r.get("scoring", {}).get("iconic", {}).get("score"')
    content = content.replace('recipe.get("iconic_score"', 'recipe.get("scoring", {}).get("iconic", {}).get("score"')

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

for root, dirs, files in os.walk('backend'):
    for f in files:
        if f.endswith('.py'):
             process_file(os.path.join(root, f))
print('Done!')
