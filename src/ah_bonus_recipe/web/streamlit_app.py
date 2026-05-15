from __future__ import annotations

from pathlib import Path

import streamlit as st

from ah_bonus_recipe.models import RecipePreferences
from ah_bonus_recipe.recipes.generator import RecipeGenerationError, generate_recipe_plan


st.set_page_config(page_title="AH Bonus Recipe Finder", layout="wide")

st.title("AH Bonus Recipe Finder")

dataset_path = st.sidebar.text_input("Bonus week JSON", "data/processed/latest_bonus_week.json")
recipe_count = st.sidebar.number_input("Recipes", min_value=1, max_value=10, value=3)
minimum_bonus_products = st.sidebar.number_input("Minimum Bonus products", min_value=1, max_value=10, value=2)
candidate_limit = st.sidebar.slider("Candidate products", min_value=30, max_value=160, value=90, step=10)

with st.form("preferences"):
    servings = st.number_input("People", min_value=1, max_value=20, value=2)
    allergies = st.multiselect(
        "Allergies",
        ["gluten", "lactose", "milk", "eggs", "fish", "shellfish", "nuts", "peanuts", "soy"],
    )
    disliked = st.text_input("Disliked ingredients", placeholder="coriander, mushrooms")
    main_ingredients = st.text_input("Preferred main ingredients", placeholder="chicken, seafood")
    cuisine = st.selectbox(
        "Cuisine",
        ["No preference", "Asian", "Spanish", "Italian", "Dutch", "Mexican", "Middle Eastern"],
    )
    diet = st.selectbox("Diet", ["No preference", "vegetarian", "vegan", "halal", "high protein"])
    meal_type = st.selectbox("Meal type", ["dinner", "lunch", "breakfast", "snack"])
    spice_level = st.selectbox("Spice level", ["No preference", "mild", "medium", "spicy"])
    skill_level = st.selectbox("Skill level", ["No preference", "beginner", "intermediate", "advanced"])
    equipment = st.text_input("Available equipment", placeholder="oven, blender, air fryer")
    max_minutes = st.slider("Max cooking minutes", 10, 120, 35)
    submitted = st.form_submit_button("Generate recipes")

if submitted:
    path = Path(dataset_path)
    if not path.exists():
        st.error(f"Dataset not found: {path}")
        st.stop()

    prefs = RecipePreferences(
        servings=servings,
        allergies=list(allergies),
        disliked_ingredients=[item.strip() for item in disliked.split(",") if item.strip()],
        main_ingredients=[item.strip() for item in main_ingredients.split(",") if item.strip()],
        cuisine=None if cuisine == "No preference" else cuisine,
        diet=None if diet == "No preference" else diet,
        meal_type=meal_type,
        spice_level=None if spice_level == "No preference" else spice_level,
        skill_level=None if skill_level == "No preference" else skill_level,
        equipment=[item.strip() for item in equipment.split(",") if item.strip()],
        max_cooking_minutes=max_minutes,
        recipe_count=recipe_count,
        minimum_bonus_products=minimum_bonus_products,
    )

    with st.spinner("Generating recipes"):
        try:
            result = generate_recipe_plan(
                prefs,
                dataset_path=path,
                candidate_limit=candidate_limit,
            )
        except RecipeGenerationError as exc:
            st.error(str(exc))
            st.stop()

    st.caption(f"Week {result.week_start} to {result.week_end}")
    st.write(f"Candidate bonus products considered: {result.candidate_product_count}")
    if result.warnings:
        st.warning("\n".join(result.warnings))

    for recipe in result.recipes:
        with st.expander(recipe.title, expanded=True):
            st.write(f"{recipe.cuisine} | {recipe.servings} servings | {recipe.total_time_minutes} minutes")
            col1, col2, col3 = st.columns(3)
            col1.metric("Normal price", f"€{recipe.savings.baseline_total:.2f}")
            col2.metric("Bonus price", f"€{recipe.savings.promo_total:.2f}")
            col3.metric("Saved", f"€{recipe.savings.savings:.2f}")
            if recipe.validation_warnings:
                st.warning("\n".join(recipe.validation_warnings))

            st.subheader("Bonus products")
            st.table(
                [
                    {
                        "id": item.product_id,
                        "product": item.title,
                        "packs": item.packages_to_buy,
                        "bonus": item.bonus_mechanism,
                        "normal": item.price_before_bonus,
                        "current": item.current_price,
                    }
                    for item in recipe.bonus_product_uses
                ]
            )
            st.subheader("Ingredients")
            st.table([ingredient.model_dump() for ingredient in recipe.ingredients])
            st.subheader("Nutrition")
            st.write("Estimated whole meal")
            st.json(recipe.nutrition_report.estimated_total.model_dump(exclude_none=True))
            st.write("Known AH bonus-product nutrition")
            st.json(recipe.nutrition_report.known_bonus_total)
            st.subheader("Prep")
            st.write("\n".join(f"- {item}" for item in recipe.prep))
            st.subheader("Steps")
            for idx, step in enumerate(recipe.steps, start=1):
                st.write(f"{idx}. {step}")
            if recipe.notes:
                st.subheader("Notes")
                st.write("\n".join(f"- {item}" for item in recipe.notes))
