import json
import streamlit as st

st.set_page_config(page_title="Recipe Audit Tool", layout="wide")

st.title("Recipe Audit & Validation Tool")

uploaded_file = st.file_uploader("Upload recipes.json", type=["json"])

# ----------------------------
# Validation Functions
# ----------------------------

def check_language(recipe):
    issues = []
    if recipe.get("origin", {}).get("country", "") in ["france", "liban", "maroc", "inde"]:
        issues.append("Non-EN country detected")
    return issues


def check_ingredients_vs_instructions(recipe):
    issues = []
    ingredients = [c["ingredient"] for c in recipe.get("composition", [])]
    instructions = " ".join(recipe.get("instructions", [])).lower()

    for ing in ["garlic", "sesame_oil", "butter"]:
        if ing in instructions and ing not in ingredients:
            issues.append(f"Ingredient used but not declared: {ing}")
    return issues


def check_units(recipe):
    issues = []
    for c in recipe.get("composition", []):
        unit = c.get("unit")
        if unit not in ["g", "ml"]:
            issues.append(f"Non standard unit: {unit}")
    return issues


def check_preparation_enum(recipe):
    allowed = [
        "raw", "boiled", "fried", "seared", "blanched",
        "simmered", "steamed", "toasted"
    ]
    issues = []

    for c in recipe.get("composition", []):
        prep = c.get("meta", {}).get("preparation")
        if prep and prep not in allowed:
            issues.append(f"Invalid preparation: {prep}")
    return issues


def audit_recipe(recipe):
    issues = []
    issues += check_language(recipe)
    issues += check_ingredients_vs_instructions(recipe)
    issues += check_units(recipe)
    issues += check_preparation_enum(recipe)
    return issues


# ----------------------------
# App Logic
# ----------------------------

if uploaded_file:
    data = json.load(uploaded_file)
    recipes = data.get("recipes", [])

    st.success(f"Loaded {len(recipes)} recipes")

    selected_id = st.selectbox(
        "Select recipe",
        [r["id"] for r in recipes]
    )

    recipe = next(r for r in recipes if r["id"] == selected_id)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Recipe Data")
        st.json(recipe)

    with col2:
        st.subheader("Audit Results")
        issues = audit_recipe(recipe)

        if not issues:
            st.success("No issues detected")
        else:
            for issue in issues:
                st.error(issue)

    st.divider()

    # Global audit
    st.subheader("Global Audit")

    total_issues = 0
    problem_recipes = []

    for r in recipes:
        issues = audit_recipe(r)
        if issues:
            total_issues += len(issues)
            problem_recipes.append((r["id"], len(issues)))

    st.write(f"Total issues detected: {total_issues}")

    if problem_recipes:
        st.write("Recipes with issues:")
        st.dataframe(problem_recipes)

    # Export issues
    if st.button("Export issues report"):
        report = []
        for r in recipes:
            issues = audit_recipe(r)
            if issues:
                report.append({
                    "id": r["id"],
                    "issues": issues
                })

        st.download_button(
            label="Download JSON report",
            data=json.dumps(report, indent=2),
            file_name="audit_report.json",
            mime="application/json"
        )

else:
    st.info("Upload a recipes.json file to start auditing")
