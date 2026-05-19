import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import {
  AlertCircle,
  ChefHat,
  Clock,
  Loader2,
  RefreshCw,
  Search,
  ShoppingBasket,
  Sparkles,
  Users
} from "lucide-react";
import { generateRecipes, getLatestRecipes, getStatus } from "./api";
import { Alert, AlertDescription } from "./components/ui/alert";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { Select } from "./components/ui/select";
import { Separator } from "./components/ui/separator";
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

export default function App() {
  const [status, setStatus] = useState<DatasetStatus | null>(null);
  const [result, setResult] = useState<RecipeGenerationResult | null>(null);
  const [form, setForm] = useState(defaultForm);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadInitialData();
  }, []);

  const totalSavings = useMemo(
    () => result?.recipes.reduce((sum, recipe) => sum + recipe.savings.savings, 0) ?? 0,
    [result]
  );

  async function loadInitialData() {
    setStatusLoading(true);
    setError(null);
    try {
      const nextStatus = await getStatus();
      setStatus(nextStatus);
      if (nextStatus.latest_recipes_exists) {
        setResult(await getLatestRecipes());
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
      const generated = await generateRecipes(buildPreferences(form), form.candidateLimit);
      setResult(generated);
      setStatus(await getStatus());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate recipes.");
    } finally {
      setLoading(false);
    }
  }

  function toggleAllergy(allergy: string) {
    const allergies = form.allergies.includes(allergy)
      ? form.allergies.filter((item) => item !== allergy)
      : [...form.allergies, allergy];
    setForm({ ...form, allergies });
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto grid max-w-[1440px] gap-8 px-5 py-6 lg:grid-cols-[380px_minmax(0,1fr)] lg:px-8">
        <aside className="lg:sticky lg:top-6 lg:h-[calc(100vh-3rem)] lg:overflow-y-auto">
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <ChefHat size={21} />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-normal">AH Bonus Recipe Finder</h1>
              <p className="text-sm text-muted-foreground">Weekly deals, calmer meal planning.</p>
            </div>
          </div>

          <StatusCard status={status} loading={statusLoading} onRefresh={loadInitialData} />

          <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
            <section className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <NumberField
                  label="People"
                  icon={<Users size={15} />}
                  min={1}
                  max={20}
                  value={form.servings}
                  onChange={(servings) => setForm({ ...form, servings })}
                />
                <NumberField
                  label="Recipes"
                  icon={<Sparkles size={15} />}
                  min={1}
                  max={10}
                  value={form.recipeCount}
                  onChange={(recipeCount) => setForm({ ...form, recipeCount })}
                />
              </div>

              <NumberField
                label="Minimum bonus products"
                icon={<ShoppingBasket size={15} />}
                min={1}
                max={10}
                value={form.minimumBonusProducts}
                onChange={(minimumBonusProducts) => setForm({ ...form, minimumBonusProducts })}
              />

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="candidate-limit">Candidate products</Label>
                  <span className="text-sm text-muted-foreground">{form.candidateLimit}</span>
                </div>
                <input
                  id="candidate-limit"
                  className="w-full accent-primary"
                  type="range"
                  min={30}
                  max={160}
                  step={10}
                  value={form.candidateLimit}
                  onChange={(event) => setForm({ ...form, candidateLimit: Number(event.target.value) })}
                />
              </div>
            </section>

            <Separator />

            <section className="space-y-4">
              <SegmentedControl
                label="Meal"
                value={form.mealType}
                options={mealTypes}
                onChange={(mealType) => setForm({ ...form, mealType })}
              />
              <SelectField
                label="Cuisine"
                value={form.cuisine}
                options={cuisines}
                onChange={(cuisine) => setForm({ ...form, cuisine })}
              />
              <SelectField
                label="Diet"
                value={form.diet}
                options={diets}
                onChange={(diet) => setForm({ ...form, diet })}
              />
            </section>

            <details className="group rounded-lg border bg-card">
              <summary className="cursor-pointer list-none px-4 py-3 text-sm font-medium">
                Fine tune preferences
                <span className="float-right text-muted-foreground group-open:hidden">+</span>
                <span className="float-right text-muted-foreground hidden group-open:inline">-</span>
              </summary>
              <div className="space-y-4 border-t px-4 py-4">
                <div className="grid grid-cols-2 gap-3">
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
                  <SelectField
                    label="Budget"
                    value={form.budget}
                    options={budgets}
                    onChange={(budget) => setForm({ ...form, budget })}
                  />
                  <NumberField
                    label="Minutes"
                    icon={<Clock size={15} />}
                    min={5}
                    max={240}
                    value={form.maxCookingMinutes}
                    onChange={(maxCookingMinutes) => setForm({ ...form, maxCookingMinutes })}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Allergies</Label>
                  <div className="flex flex-wrap gap-2">
                    {allergyOptions.map((allergy) => (
                      <Button
                        type="button"
                        size="sm"
                        variant={form.allergies.includes(allergy) ? "default" : "outline"}
                        key={allergy}
                        onClick={() => toggleAllergy(allergy)}
                      >
                        {allergy}
                      </Button>
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
              </div>
            </details>

            <Button
              className="h-11 w-full"
              type="submit"
              disabled={loading || !status?.dataset_exists || !status?.openai_configured}
            >
              {loading ? <Loader2 className="animate-spin" size={17} /> : <Search size={17} />}
              Generate recipes
            </Button>
          </form>
        </aside>

        <section className="min-w-0">
          <header className="mb-8 flex flex-col justify-between gap-4 border-b pb-6 sm:flex-row sm:items-end">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Weekly Bonus Menu</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-normal">
                {result ? `${result.recipes.length} quiet recipe ideas` : "Choose preferences"}
              </h2>
            </div>
            <div className="grid grid-cols-2 gap-6 text-sm">
              <Metric label="Candidates" value={String(result?.candidate_product_count ?? status?.candidate_product_count ?? 0)} />
              <Metric label="Saved" value={`EUR ${totalSavings.toFixed(2)}`} strong />
            </div>
          </header>

          {error ? <ErrorMessage message={error} /> : null}

          {!result && !error ? (
            <div className="flex min-h-[420px] flex-col items-center justify-center rounded-lg border border-dashed text-center text-muted-foreground">
              <ShoppingBasket size={38} />
              <h3 className="mt-4 text-lg font-medium text-foreground">No recipes loaded yet</h3>
              <p className="mt-1 max-w-sm text-sm">Generate recipes from the latest AH Bonus dataset.</p>
            </div>
          ) : null}

          {result?.warnings.length ? (
            <Alert className="mb-6 border-amber-200 bg-amber-50 text-amber-900">
              <AlertDescription>{result.warnings.join(" ")}</AlertDescription>
            </Alert>
          ) : null}

          <div className="space-y-5">
            {result?.recipes.map((recipe) => (
              <RecipeCard recipe={recipe} key={recipe.title} />
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

function StatusCard({
  status,
  loading,
  onRefresh
}: {
  status: DatasetStatus | null;
  loading: boolean;
  onRefresh: () => Promise<void>;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-3 p-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className={status?.dataset_exists ? "h-2 w-2 rounded-full bg-emerald-600" : "h-2 w-2 rounded-full bg-destructive"} />
            <p className="truncate text-sm font-medium">
              {status?.dataset_exists ? `${status.week_start} to ${status.week_end}` : "Dataset missing"}
            </p>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {status?.dataset_exists
              ? `${status.product_count} products. ${status.openai_configured ? "OpenAI ready." : "OpenAI key missing."}`
              : "Run the weekly scraper first."}
          </p>
        </div>
        <Button variant="ghost" size="icon" type="button" onClick={onRefresh} aria-label="Refresh status">
          <RefreshCw className={loading ? "animate-spin" : ""} size={16} />
        </Button>
      </CardContent>
    </Card>
  );
}

function RecipeCard({ recipe }: { recipe: EnrichedRecipe }) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="gap-4 pb-4">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">{recipe.cuisine}</Badge>
              <Badge variant="outline">{recipe.servings} people</Badge>
              <Badge variant="outline">{recipe.total_time_minutes} min</Badge>
            </div>
            <div>
              <CardTitle className="text-2xl leading-tight">{recipe.title}</CardTitle>
              <CardDescription className="mt-2">
                {recipe.bonus_product_uses.length} bonus products. {recipe.savings.description}
              </CardDescription>
            </div>
          </div>
          <div className="min-w-[168px] rounded-lg border bg-muted p-4 text-right">
            <p className="text-sm text-muted-foreground">{recipe.savings.savings_label}</p>
            <p className="mt-1 text-2xl font-semibold">EUR {recipe.savings.savings.toFixed(2)}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
          <span>{recipe.savings.baseline_total_label}: EUR {recipe.savings.baseline_total.toFixed(2)}</span>
          <span>{recipe.savings.promo_total_label}: EUR {recipe.savings.promo_total.toFixed(2)}</span>
        </div>
        {recipe.savings.notes.map((note) => (
          <p className="text-sm text-muted-foreground" key={note}>{note}</p>
        ))}
      </CardHeader>

      <CardContent className="space-y-6">
        <BonusProducts products={recipe.bonus_product_uses} />

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(240px,0.85fr)]">
          <IngredientList ingredients={recipe.ingredients} />
          <NutritionPanel nutrition={recipe.nutrition_report.estimated_per_serving} />
        </div>

        <Separator />

        <div className="grid gap-6 md:grid-cols-[0.8fr_1.2fr]">
          <StepsList title="Prep" items={recipe.prep} />
          <StepsList title="Steps" items={recipe.steps} ordered />
        </div>

        {recipe.validation_warnings.length ? (
          <Alert className="border-amber-200 bg-amber-50 text-amber-900">
            <AlertDescription>{recipe.validation_warnings.join(" ")}</AlertDescription>
          </Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}

function BonusProducts({ products }: { products: BonusProductUse[] }) {
  if (!products.length) return null;
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {products.map((product) => (
        <a
          className="grid grid-cols-[52px_minmax(0,1fr)] gap-3 rounded-lg border p-3 text-sm no-underline transition-colors hover:bg-muted"
          href={product.url ?? undefined}
          target="_blank"
          rel="noreferrer"
          key={`${product.product_id}-${product.title}`}
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-md bg-muted">
            {product.image_url ? <img className="h-12 w-12 object-contain" src={product.image_url} alt="" loading="lazy" /> : <ShoppingBasket size={20} />}
          </div>
          <div className="min-w-0">
            <p className="truncate font-medium text-foreground">{product.title}</p>
            <p className="truncate text-muted-foreground">{product.bonus_mechanism ?? "Bonus"}</p>
            <p className="text-xs text-muted-foreground">{product.packages_to_buy} pack(s)</p>
          </div>
        </a>
      ))}
    </div>
  );
}

function IngredientList({ ingredients }: { ingredients: RecipeIngredient[] }) {
  return (
    <section>
      <h4 className="mb-3 text-sm font-medium">Ingredients</h4>
      <div className="divide-y rounded-lg border">
        {ingredients.map((ingredient, index) => (
          <div className="grid grid-cols-[minmax(0,1fr)_auto_auto] gap-4 px-3 py-2 text-sm" key={`${ingredient.name}-${index}`}>
            <span className={ingredient.bonus_product_id ? "font-medium" : ""}>{ingredient.name}</span>
            <span className="text-muted-foreground">{formatQuantity(ingredient.quantity)} {ingredient.unit}</span>
            <span className="min-w-8 text-right text-muted-foreground">{ingredient.packages_to_buy}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function NutritionPanel({ nutrition }: { nutrition: NutritionEstimate }) {
  const nutrients = [
    ["Energy", nutrition.energy_kcal, "kcal"],
    ["Protein", nutrition.protein_g, "g"],
    ["Carbs", nutrition.carbs_g, "g"],
    ["Fat", nutrition.fat_g, "g"],
    ["Fiber", nutrition.fiber_g, "g"],
    ["Salt", nutrition.salt_g, "g"]
  ] as const;
  return (
    <section>
      <h4 className="mb-3 text-sm font-medium">Nutrition per serving</h4>
      <div className="grid grid-cols-2 gap-2">
        {nutrients.map(([label, value, unit]) => (
          <div className="rounded-lg border p-3" key={label}>
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="mt-1 font-medium">{value == null ? "-" : `${round(value)} ${unit}`}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function StepsList({ title, items, ordered = false }: { title: string; items: string[]; ordered?: boolean }) {
  const List = ordered ? "ol" : "ul";
  return (
    <section>
      <h4 className="mb-3 text-sm font-medium">{title}</h4>
      <List className={ordered ? "list-decimal space-y-2 pl-5 text-sm leading-6" : "list-disc space-y-2 pl-5 text-sm leading-6"}>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </List>
    </section>
  );
}

function ErrorMessage({ message }: { message: string }) {
  return (
    <Alert className="mb-6 border-destructive/30 bg-destructive/5 text-destructive">
      <AlertCircle size={16} />
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}

function Metric({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="text-right">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className={strong ? "text-lg font-semibold" : "text-lg font-medium"}>{value}</p>
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
    <div className="space-y-2">
      <Label className="flex items-center gap-2">{icon}{label}</Label>
      <Input type="number" min={min} max={max} value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </div>
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
    <div className="space-y-2">
      <Label>{label}</Label>
      <Input value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </div>
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
    <div className="space-y-2">
      <Label>{label}</Label>
      <Select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option value={option} key={option}>{option}</option>
        ))}
      </Select>
    </div>
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
    <div className="space-y-2">
      <Label>{label}</Label>
      <div className="grid grid-cols-4 rounded-lg border bg-muted p-1">
        {options.map((option) => (
          <button
            type="button"
            className={value === option ? "rounded-md bg-background px-2 py-1.5 text-sm font-medium shadow-sm" : "px-2 py-1.5 text-sm text-muted-foreground"}
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

function parseCsv(value: string): string[] {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
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
