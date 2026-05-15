import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import {
  AlertCircle,
  ChefHat,
  Clock,
  Leaf,
  Loader2,
  RefreshCw,
  Search,
  ShoppingBasket,
  Sparkles,
  Users
} from "lucide-react";
import { generateRecipes, getLatestRecipes, getStatus } from "./api";
import type {
  BonusProductUse,
  DatasetStatus,
  EnrichedRecipe,
  NutritionEstimate,
  RecipeGenerationResult,
  RecipeIngredient,
  RecipePreferences
} from "./types";
import "./styles.css";

const allergyOptions = ["gluten", "lactose", "milk", "eggs", "fish", "shellfish", "nuts", "peanuts", "soy"];
const cuisines = ["Any", "Asian", "Spanish", "Italian", "Dutch", "Mexican", "Middle Eastern"];
const diets = ["Any", "vegetarian", "vegan", "halal", "high protein"];
const mealTypes = ["dinner", "lunch", "breakfast", "snack"];
const spiceLevels = ["Any", "mild", "medium", "spicy"];
const skillLevels = ["Any", "beginner", "intermediate", "advanced"];
const budgets = ["Any", "low", "medium", "flexible"];

const defaultForm = {
  servings: 2,
  recipeCount: 3,
  minimumBonusProducts: 2,
  candidateLimit: 90,
  allergies: [] as string[],
  dislikedIngredients: "",
  mainIngredients: "",
  cuisine: "Any",
  diet: "Any",
  mealType: "dinner",
  spiceLevel: "Any",
  skillLevel: "Any",
  budget: "Any",
  equipment: "oven, blender",
  maxCookingMinutes: 35
};

function App() {
  const [status, setStatus] = useState<DatasetStatus | null>(null);
  const [result, setResult] = useState<RecipeGenerationResult | null>(null);
  const [form, setForm] = useState(defaultForm);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadInitialData();
  }, []);

  async function loadInitialData() {
    setStatusLoading(true);
    setError(null);
    try {
      const nextStatus = await getStatus();
      setStatus(nextStatus);
      if (nextStatus.latest_recipes_exists) {
        const latest = await getLatestRecipes();
        setResult(latest);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load app data.");
    } finally {
      setStatusLoading(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const preferences = buildPreferences(form);
      const generated = await generateRecipes(preferences, form.candidateLimit);
      setResult(generated);
      setStatus(await getStatus());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate recipes.");
    } finally {
      setLoading(false);
    }
  }

  const totalSavings = useMemo(() => {
    return result?.recipes.reduce((sum, recipe) => sum + recipe.savings.savings, 0) ?? 0;
  }, [result]);

  return (
    <main className="app-shell">
      <section className="workspace">
        <aside className="control-panel">
          <div className="brand-row">
            <div className="brand-mark">
              <ChefHat size={22} />
            </div>
            <div>
              <h1>AH Bonus Recipe Finder</h1>
              <p>Build meals around this week's discounted products.</p>
            </div>
          </div>

          <StatusPanel status={status} loading={statusLoading} onRefresh={loadInitialData} />

          <form className="preference-form" onSubmit={handleSubmit}>
            <div className="form-grid two">
              <NumberField
                label="People"
                icon={<Users size={16} />}
                min={1}
                max={20}
                value={form.servings}
                onChange={(servings) => setForm({ ...form, servings })}
              />
              <NumberField
                label="Recipes"
                icon={<Sparkles size={16} />}
                min={1}
                max={10}
                value={form.recipeCount}
                onChange={(recipeCount) => setForm({ ...form, recipeCount })}
              />
            </div>

            <NumberField
              label="Minimum bonus products"
              icon={<ShoppingBasket size={16} />}
              min={1}
              max={10}
              value={form.minimumBonusProducts}
              onChange={(minimumBonusProducts) => setForm({ ...form, minimumBonusProducts })}
            />

            <label className="field-label">
              Candidate products
              <span>{form.candidateLimit}</span>
            </label>
            <input
              className="range"
              type="range"
              min={30}
              max={160}
              step={10}
              value={form.candidateLimit}
              onChange={(event) => setForm({ ...form, candidateLimit: Number(event.target.value) })}
            />

            <SegmentedControl
              label="Cuisine"
              value={form.cuisine}
              options={cuisines}
              onChange={(cuisine) => setForm({ ...form, cuisine })}
            />
            <SegmentedControl
              label="Diet"
              value={form.diet}
              options={diets}
              onChange={(diet) => setForm({ ...form, diet })}
            />
            <SegmentedControl
              label="Meal"
              value={form.mealType}
              options={mealTypes}
              onChange={(mealType) => setForm({ ...form, mealType })}
            />

            <div className="form-grid two">
              <SelectField
                label="Spice"
                value={form.spiceLevel}
                options={spiceLevels}
                onChange={(spiceLevel) => setForm({ ...form, spiceLevel })}
              />
              <SelectField
                label="Skill"
                value={form.skillLevel}
                options={skillLevels}
                onChange={(skillLevel) => setForm({ ...form, skillLevel })}
              />
            </div>

            <div className="form-grid two">
              <SelectField
                label="Budget"
                value={form.budget}
                options={budgets}
                onChange={(budget) => setForm({ ...form, budget })}
              />
              <NumberField
                label="Minutes"
                icon={<Clock size={16} />}
                min={5}
                max={240}
                value={form.maxCookingMinutes}
                onChange={(maxCookingMinutes) => setForm({ ...form, maxCookingMinutes })}
              />
            </div>

            <div>
              <label className="field-label">Allergies</label>
              <div className="chip-grid">
                {allergyOptions.map((allergy) => (
                  <button
                    type="button"
                    className={form.allergies.includes(allergy) ? "chip selected" : "chip"}
                    key={allergy}
                    onClick={() => toggleAllergy(allergy)}
                  >
                    {allergy}
                  </button>
                ))}
              </div>
            </div>

            <TextField
              label="Main ingredients"
              value={form.mainIngredients}
              placeholder="salmon, chicken, rice"
              onChange={(mainIngredients) => setForm({ ...form, mainIngredients })}
            />
            <TextField
              label="Disliked ingredients"
              value={form.dislikedIngredients}
              placeholder="coriander, mushrooms"
              onChange={(dislikedIngredients) => setForm({ ...form, dislikedIngredients })}
            />
            <TextField
              label="Equipment"
              value={form.equipment}
              placeholder="oven, blender, air fryer"
              onChange={(equipment) => setForm({ ...form, equipment })}
            />

            <button
              className="primary-action"
              type="submit"
              disabled={loading || !status?.dataset_exists || !status?.openai_configured}
            >
              {loading ? <Loader2 className="spin" size={18} /> : <Search size={18} />}
              Generate recipes
            </button>
          </form>
        </aside>

        <section className="results-panel">
          <header className="results-header">
            <div>
              <p className="eyebrow">Weekly Bonus Menu</p>
              <h2>{result ? `${result.recipes.length} recipe ideas` : "Ready when you are"}</h2>
            </div>
            <div className="summary-strip">
              <Metric label="Bonus products" value={String(result?.candidate_product_count ?? status?.candidate_product_count ?? 0)} />
              <Metric label="Potential saved" value={`EUR ${totalSavings.toFixed(2)}`} accent />
            </div>
          </header>

          {error && <Alert message={error} />}

          {!result && !error && (
            <div className="empty-state">
              <ShoppingBasket size={42} />
              <h3>No recipes loaded yet</h3>
              <p>Choose preferences and generate recipes from the latest AH Bonus dataset.</p>
            </div>
          )}

          {result?.warnings.length ? (
            <div className="warning-list">
              {result.warnings.map((warning) => (
                <span key={warning}>{warning}</span>
              ))}
            </div>
          ) : null}

          <div className="recipe-list">
            {result?.recipes.map((recipe) => (
              <RecipeCard recipe={recipe} key={recipe.title} />
            ))}
          </div>
        </section>
      </section>
    </main>
  );

  function toggleAllergy(allergy: string) {
    const allergies = form.allergies.includes(allergy)
      ? form.allergies.filter((item) => item !== allergy)
      : [...form.allergies, allergy];
    setForm({ ...form, allergies });
  }
}

function buildPreferences(form: typeof defaultForm): RecipePreferences {
  return {
    servings: form.servings,
    allergies: form.allergies,
    disliked_ingredients: parseCsv(form.dislikedIngredients),
    cuisine: nullableChoice(form.cuisine),
    main_ingredients: parseCsv(form.mainIngredients),
    diet: nullableChoice(form.diet),
    max_cooking_minutes: form.maxCookingMinutes || null,
    skill_level: nullableChoice(form.skillLevel),
    budget: nullableChoice(form.budget),
    meal_type: nullableChoice(form.mealType),
    spice_level: nullableChoice(form.spiceLevel),
    equipment: parseCsv(form.equipment),
    recipe_count: form.recipeCount,
    minimum_bonus_products: form.minimumBonusProducts
  };
}

function StatusPanel({
  status,
  loading,
  onRefresh
}: {
  status: DatasetStatus | null;
  loading: boolean;
  onRefresh: () => Promise<void>;
}) {
  return (
    <div className="status-panel">
      <div>
        <span className="status-dot" data-ready={status?.dataset_exists ? "true" : "false"} />
        <strong>{status?.dataset_exists ? `Week ${status.week_start} to ${status.week_end}` : "Dataset missing"}</strong>
        <p>
          {status?.dataset_exists
            ? `${status.product_count} products, ${status.promotion_count} promotions. ${
                status.openai_configured ? "OpenAI key ready." : "OpenAI key missing."
              }`
            : "Run the weekly scraper before generating recipes."}
        </p>
      </div>
      <button className="icon-button" type="button" onClick={onRefresh} aria-label="Refresh status">
        <RefreshCw className={loading ? "spin" : ""} size={17} />
      </button>
    </div>
  );
}

function RecipeCard({ recipe }: { recipe: EnrichedRecipe }) {
  return (
    <article className="recipe-card">
      <div className="recipe-main">
        <div className="recipe-title-row">
          <div>
            <p className="eyebrow">{recipe.cuisine}</p>
            <h3>{recipe.title}</h3>
            <div className="meta-row">
              <span>
                <Users size={15} />
                {recipe.servings}
              </span>
              <span>
                <Clock size={15} />
                {recipe.total_time_minutes} min
              </span>
              <span>
                <Leaf size={15} />
                {recipe.bonus_product_uses.length} bonus items
              </span>
            </div>
          </div>
          <div className="savings-badge">
            <span>{recipe.savings.savings_label}</span>
            <strong>EUR {recipe.savings.savings.toFixed(2)}</strong>
          </div>
        </div>

        <div className="price-captions">
          <span>{recipe.savings.baseline_total_label}: EUR {recipe.savings.baseline_total.toFixed(2)}</span>
          <span>{recipe.savings.promo_total_label}: EUR {recipe.savings.promo_total.toFixed(2)}</span>
        </div>
        <p className="fine-print">{recipe.savings.description}</p>
        {recipe.savings.notes.map((note) => (
          <p className="note" key={note}>{note}</p>
        ))}

        <BonusProductStrip products={recipe.bonus_product_uses} />

        <div className="recipe-columns">
          <IngredientTable ingredients={recipe.ingredients} />
          <NutritionPanel nutrition={recipe.nutrition_report.estimated_per_serving} />
        </div>

        <div className="steps-section">
          <h4>Prep</h4>
          <ul className="compact-list">
            {recipe.prep.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <h4>Steps</h4>
          <ol>
            {recipe.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>

        {recipe.validation_warnings.length ? (
          <div className="warning-list">
            {recipe.validation_warnings.map((warning) => (
              <span key={warning}>{warning}</span>
            ))}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function BonusProductStrip({ products }: { products: BonusProductUse[] }) {
  if (!products.length) {
    return null;
  }
  return (
    <div className="bonus-strip">
      {products.map((product) => (
        <a className="bonus-product" href={product.url ?? undefined} target="_blank" rel="noreferrer" key={`${product.product_id}-${product.title}`}>
          <div className="product-image">
            {product.image_url ? <img src={product.image_url} alt="" loading="lazy" /> : <ShoppingBasket size={22} />}
          </div>
          <div>
            <strong>{product.title}</strong>
            <span>{product.bonus_mechanism ?? "Bonus"}</span>
            <small>{product.packages_to_buy} pack(s)</small>
          </div>
        </a>
      ))}
    </div>
  );
}

function IngredientTable({ ingredients }: { ingredients: RecipeIngredient[] }) {
  return (
    <section className="table-section">
      <h4>Ingredients</h4>
      <div className="ingredient-table">
        {ingredients.map((ingredient, index) => (
          <div className={ingredient.bonus_product_id ? "ingredient-row bonus" : "ingredient-row"} key={`${ingredient.name}-${index}`}>
            <span>{ingredient.name}</span>
            <span>{formatQuantity(ingredient.quantity)} {ingredient.unit}</span>
            <span>{ingredient.packages_to_buy}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function NutritionPanel({ nutrition }: { nutrition: NutritionEstimate }) {
  const nutrients = [
    ["Energy", nutrition.energy_kcal, "kcal", 700],
    ["Protein", nutrition.protein_g, "g", 45],
    ["Carbs", nutrition.carbs_g, "g", 90],
    ["Fat", nutrition.fat_g, "g", 40],
    ["Fiber", nutrition.fiber_g, "g", 15],
    ["Salt", nutrition.salt_g, "g", 6]
  ] as const;
  return (
    <section className="nutrition-panel">
      <h4>Nutrition per serving</h4>
      {nutrients.map(([label, value, unit, max]) => (
        <div className="nutrient" key={label}>
          <div>
            <span>{label}</span>
            <strong>{value == null ? "-" : `${round(value)} ${unit}`}</strong>
          </div>
          <div className="nutrient-bar">
            <span style={{ width: `${Math.min(100, ((value ?? 0) / max) * 100)}%` }} />
          </div>
        </div>
      ))}
    </section>
  );
}

function Alert({ message }: { message: string }) {
  return (
    <div className="alert">
      <AlertCircle size={18} />
      <span>{message}</span>
    </div>
  );
}

function Metric({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={accent ? "metric accent" : "metric"}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function NumberField({
  label,
  icon,
  value,
  min,
  max,
  onChange
}: {
  label: string;
  icon: ReactNode;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="input-field">
      <span>
        {icon}
        {label}
      </span>
      <input type="number" min={min} max={max} value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </label>
  );
}

function TextField({
  label,
  value,
  placeholder,
  onChange
}: {
  label: string;
  value: string;
  placeholder: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="input-field">
      <span>{label}</span>
      <input value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="input-field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option value={option} key={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function SegmentedControl({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label className="field-label">{label}</label>
      <div className="segmented">
        {options.map((option) => (
          <button
            type="button"
            className={value === option ? "selected" : ""}
            onClick={() => onChange(option)}
            key={option}
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  );
}

function parseCsv(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function nullableChoice(value: string): string | null {
  return value === "Any" ? null : value;
}

function formatQuantity(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function round(value: number): number {
  return Math.round(value * 10) / 10;
}

export default App;
