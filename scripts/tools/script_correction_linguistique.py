import json, re, sys

def clean_recipes(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    unit_map = {
        r'\btsp\b': 'c.à.c', r'\btbsp\b': 'c.à.s', 
        r'\btablespoon\b': 'c.à.s', r'\bteaspoon\b': 'c.à.c',
        r'\bcup\b': '240 ml', r'\bpinch\b': 'pincée',
        r'\boz\b': '28 g', r'\blb\b': '450 g'
    }
    
    oe_map = {
        r'\bboeuf\b': 'bœuf', r'\bBoeuf\b': 'Bœuf', r'\bBOEUF\b': 'BŒUF',
        r'\boeuf\b': 'œuf', r'\bOeuf\b': 'Œuf', r'\bOEUF\b': 'ŒUF',
        r'\bcoeur\b': 'cœur', r'\bCoeur\b': 'Cœur', r'\bCOEUR\b': 'CŒUR'
    }
    
    def apply_replacements(text):
        if not isinstance(text, str): return text
        for pattern, repl in unit_map.items():
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
        for pattern, repl in oe_map.items():
            text = re.sub(pattern, repl, text)
        return text
    
    def recursive_clean(obj):
        if isinstance(obj, dict): return {k: recursive_clean(v) for k, v in obj.items()}
        elif isinstance(obj, list): return [recursive_clean(item) for item in obj]
        elif isinstance(obj, str): return apply_replacements(obj)
        else: return obj
    
    data_clean = recursive_clean(data)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data_clean, f, ensure_ascii=False, indent=2)
    print(f"Fichier nettoyé: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py input.json output.json")
    else:
        clean_recipes(sys.argv[1], sys.argv[2])
