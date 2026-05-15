export type DatasetStatus = {
  dataset_exists: boolean;
  week_start: string | null;
  week_end: string | null;
  product_count: number;
  promotion_count: number;
  candidate_product_count: number;
  latest_recipes_exists: boolean;
  openai_configured: boolean;
};

export type RecipePreferences = {
  servings: number;
  allergies: string[];
  disliked_ingredients: string[];
  cuisine: string | null;
  main_ingredients: string[];
  diet: string | null;
  max_cooking_minutes: number | null;
  skill_level: string | null;
  budget: string | null;
  meal_type: string | null;
  spice_level: string | null;
  equipment: string[];
  recipe_count: number;
  minimum_bonus_products: number;
};

export type NutritionEstimate = {
  energy_kcal: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  sugar_g: number | null;
  fat_g: number | null;
  saturated_fat_g: number | null;
  fiber_g: number | null;
  salt_g: number | null;
};

export type RecipeIngredient = {
  name: string;
  quantity: number;
  unit: string;
  bonus_product_id: number | null;
  packages_to_buy: number | "-";
};

export type BonusProductUse = {
  product_id: number;
  title: string;
  url: string | null;
  image_url: string | null;
  quantity: number;
  unit: string;
  packages_to_buy: number;
  promotion_id: string | null;
  promotion_title: string | null;
  bonus_mechanism: string | null;
  price_before_bonus: number | null;
  current_price: number | null;
};

export type SavingsSummary = {
  currency: string;
  scope: string;
  description: string;
  baseline_total: number;
  promo_total: number;
  savings: number;
  baseline_total_label: string;
  promo_total_label: string;
  savings_label: string;
  notes: string[];
  supported: boolean;
  unsupported_reasons: string[];
};

export type NutritionReport = {
  known_bonus_total: Record<string, number>;
  known_bonus_per_serving: Record<string, number>;
  estimated_total: NutritionEstimate;
  estimated_per_serving: NutritionEstimate;
  missing_bonus_nutrition_product_ids: number[];
  unconverted_bonus_nutrition_product_ids: number[];
};

export type EnrichedRecipe = {
  title: string;
  cuisine: string;
  servings: number;
  total_time_minutes: number;
  bonus_product_ids: number[];
  ingredients: RecipeIngredient[];
  prep: string[];
  steps: string[];
  notes: string[];
  estimated_nutrition_total: NutritionEstimate;
  estimated_nutrition_per_serving: NutritionEstimate;
  bonus_product_uses: BonusProductUse[];
  savings: SavingsSummary;
  nutrition_report: NutritionReport;
  validation_warnings: string[];
};

export type RecipeGenerationResult = {
  week_start: string;
  week_end: string;
  preferences: RecipePreferences;
  candidate_product_count: number;
  recipes: EnrichedRecipe[];
  warnings: string[];
};
