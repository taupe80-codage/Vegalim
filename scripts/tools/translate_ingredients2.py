import json

file_path = 'c:/Users/Samijo/Downloads/project_final_v6_migrated/project_final_v6_migrated/frontend/src/translations.json'

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

translations = {
    "white_miso": "Miso blanc",
    "celeriac": "Céleri-rave",
    "espelette_pepper": "Piment d'Espelette",
    "dragon_fruit": "Fruit du dragon",
    "canele": "Cannelé",
    "gruyere": "Gruyère",
    "quatre_epices": "Quatre-épices",
    "endive": "Endive",
    "agave": "Agave",
    "aquafaba": "Aquafaba",
    "za_atar": "Zaatar",
    "chanterelle": "Chanterelle",
    "laitue": "Laitue",
    "kiwi": "Kiwi",
    "ricotta": "Ricotta",
    "fromage_blanc": "Fromage blanc",
    "orange": "Orange",
    "olive": "Olive"
}

for key, value in translations.items():
    if key in data:
        data[key] = value

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Translations applied successfully.")
