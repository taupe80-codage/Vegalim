# Correction recommendation engine

NUTRIENT_TO_INGREDIENTS = {
    "vitamin_b12": ["fortified_cereal", "milk", "egg"],
    "iron": ["lentils", "spinach", "chickpeas"],
    "calcium": ["milk", "yogurt", "tofu"],
    "protein": ["lentils", "beans", "tofu"],
    "fiber": ["vegetables", "whole_grains"],
    "magnesium": ["nuts", "seeds"],
    "potassium": ["banana", "potato"],
}

def recommend_corrections(deficiencies):
    recommendations = []

    for d in deficiencies:
        nutrient = d["nutrient"]
        foods = NUTRIENT_TO_INGREDIENTS.get(nutrient, [])

        recommendations.append({
            "nutrient": nutrient,
            "severity": d["severity"],
            "recommendations": foods[:3]
        })

    return recommendations


def rank_corrections(recommendations):
    priority = {"high": 2, "medium": 1}

    return sorted(
        recommendations,
        key=lambda x: priority.get(x["severity"], 0),
        reverse=True
    )
