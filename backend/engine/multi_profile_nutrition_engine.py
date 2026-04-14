# Multi-profile adaptive nutrition

BASE_PROFILES = {
    "vegan": {"vitamin_b12": 2.0, "iron": 1.2},
    "athlete": {"protein": 1.5, "magnesium": 1.2},
    "pregnancy": {"iron": 1.5, "folate": 1.5, "calcium": 1.3},
    "diabetic": {"sugar": 0.5, "fiber": 1.5}
}

def merge_profiles(profiles):
    merged = {}
    for profile in profiles:
        rules = BASE_PROFILES.get(profile, {})
        for k, v in rules.items():
            if k in merged:
                merged[k] *= v
            else:
                merged[k] = v
    return merged

def adapt_ajr_multi(ajr_base, profiles):
    multipliers = merge_profiles(profiles)
    adapted = {}

    for k, v in ajr_base.items():
        factor = multipliers.get(k, 1.0)
        adapted[k] = v * factor

    return adapted

def compute_multi_profile_score(nutrition, ajr_base, profiles):
    ajr = adapt_ajr_multi(ajr_base, profiles)

    score = 0
    count = 0

    for k, ref in ajr.items():
        val = nutrition.get(k, 0)
        ratio = min(val / ref, 1.0)
        score += ratio
        count += 1

    return (score / count) * 10 if count else 0
