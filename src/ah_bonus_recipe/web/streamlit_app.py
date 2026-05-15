from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from ah_bonus_recipe.models import BonusProduct, RecipePreferences
from ah_bonus_recipe.recipes.generator import generate_recipes


st.set_page_config(page_title="AH Bonus Recipe Finder", layout="wide")

st.title("AH Bonus Recipe Finder")

dataset_path = st.sidebar.text_input("Bonus products JSON", "data/processed/latest_products.json")
recipe_count = st.sidebar.number_input("Recipes", min_value=1, max_value=10, value=3)
minimum_bonus_products = st.sidebar.number_input("Minimum Bonus products", min_value=1, max_value=10, value=2)

with st.form("preferences"):
    servings = st.number_input("People", min_value=1, max_value=20, value=2)
    allergies = st.multiselect(
        "Allergies",
        ["gluten", "lactose", "milk", "eggs", "fish", "shellfish", "nuts", "peanuts", "soy"],
    )
    disliked = st.text_input("Disliked ingredients", placeholder="coriander, mushrooms")
    cuisine = st.selectbox(
        "Cuisine",
        ["No preference", "Asian", "Spanish", "Italian", "Dutch", "Mexican", "Middle Eastern"],
    )
    diet = st.selectbox("Diet", ["No preference", "vegetarian", "vegan", "halal", "high protein"])
    meal_type = st.selectbox("Meal type", ["dinner", "lunch", "breakfast", "snack"])
    max_minutes = st.slider("Max cooking minutes", 10, 120, 35)
    submitted = st.form_submit_button("Generate recipes")

if submitted:
    path = Path(dataset_path)
    if not path.exists():
        st.error(f"Dataset not found: {path}")
        st.stop()

    products = [BonusProduct.model_validate(item) for item in json.loads(path.read_text())]
    prefs = RecipePreferences(
        servings=servings,
        allergies=list(allergies),
        disliked_ingredients=[item.strip() for item in disliked.split(",") if item.strip()],
        cuisine=None if cuisine == "No preference" else cuisine,
        diet=None if diet == "No preference" else diet,
        meal_type=meal_type,
        max_cooking_minutes=max_minutes,
        recipe_count=recipe_count,
        minimum_bonus_products=minimum_bonus_products,
    )

    with st.spinner("Generating recipes"):
        result = generate_recipes(prefs, products)

    for recipe in result["recipes"]:
        with st.expander(recipe["title"], expanded=True):
            st.write(f"{recipe['cuisine']} | {recipe['servings']} servings")
            st.write("Bonus products:", ", ".join(map(str, recipe["bonus_product_ids"])))
            st.subheader("Ingredients")
            st.table(recipe["ingredients"])
            st.subheader("Prep")
            st.write("\n".join(f"- {item}" for item in recipe["prep"]))
            st.subheader("Steps")
            for idx, step in enumerate(recipe["steps"], start=1):
                st.write(f"{idx}. {step}")
