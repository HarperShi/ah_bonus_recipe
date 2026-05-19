import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import {
  AlertCircle,
  ArrowRight,
  ChefHat,
  Clock,
  Loader2,
  RefreshCw,
  Search,
  ShoppingBasket,
  Sparkles,
  Timer,
  Users,
  Utensils
} from "lucide-react";
import { generateRecipes, getLatestRecipes, getStatus } from "./api";
import { Alert, AlertDescription } from "./components/ui/alert";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./components/ui/collapsible";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { Select } from "./components/ui/select";
import { Separator } from "./components/ui/separator";
import { Slider } from "./components/ui/slider";
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

const howItWorks = [
  ["Choose what feels right", "Set servings, cuisine, allergies, and the level of effort you want tonight."],
  ["Use the weekly Bonus", "The app selects from current AH Bonus products and keeps the savings math local."],
  ["Cook with confidence", "Each recipe includes bonus products, prep, steps, nutrition, and estimated savings."]
];

const recipeMoods = [
  ["Slow weekend bowls", "Warm grains, roasted vegetables, herbs, and one simple sauce."],
  ["Fresh market dinners", "Seafood, chicken, or plant-forward mains with bright seasonal sides."],
  ["Low-effort comfort", "Traybakes, pasta, soups, and family meals that do not ask too much."]
];

const timeSavers = [
  "Filters products before sending recipe context to OpenAI.",
  "Shows only the Bonus-product savings, so the price story stays honest.",
  "Keeps allergies and disliked ingredients visible in the recipe request."
];

export default function App() {
  const [status, setStatus] = useState<DatasetStatus | null>(null);
  const [result, setResult] = useState<RecipeGenerationResult | null>(null);
  const [form, setForm] = useState(defaultForm);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);

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
      requestAnimationFrame(() => document.getElementById("recipes")?.scrollIntoView({ behavior: "smooth" }));
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
      <TopBar status={status} loading={statusLoading} onRefresh={loadInitialData} />

      <Hero />

      <section
        id="create"
        className="mx-auto grid max-w-6xl gap-8 overflow-hidden px-5 py-16 lg:grid-cols-[minmax(0,0.94fr)_minmax(420px,1.06fr)]"
      >
        <div className="flex min-w-0 flex-col justify-center">
          <p className="text-sm font-medium text-primary">Create a recipe that fits your evening</p>
          <h2 className="mt-3 max-w-[20rem] text-2xl font-semibold tracking-normal sm:max-w-xl sm:text-4xl">
            Start with a few preferences. Let the Bonus aisle do the rest.
          </h2>
          <p className="mt-5 max-w-[20rem] text-base leading-7 text-muted-foreground sm:max-w-xl">
            Choose the kind of meal you want, how many people are eating, and what should stay off the plate. The app turns this week's discounted products into practical recipes with clear savings.
          </p>
          <div className="mt-8 grid max-w-xl gap-4 sm:grid-cols-3">
            <SoftStat label="Products" value={status?.product_count ? String(status.product_count) : "-"} />
            <SoftStat label="Promotions" value={status?.promotion_count ? String(status.promotion_count) : "-"} />
            <SoftStat label="Candidates" value={String(status?.candidate_product_count ?? 0)} />
          </div>
        </div>

        <GeneratorCard
          advancedOpen={advancedOpen}
          error={error}
          form={form}
          loading={loading}
          status={status}
          onAdvancedOpenChange={setAdvancedOpen}
          onAllergyToggle={toggleAllergy}
          onFormChange={setForm}
          onSubmit={handleSubmit}
        />
      </section>

      <HowItWorksSection />
      <RecipeMoodSection />
      <TimeSavingsSection />

      <section id="recipes" className="mx-auto max-w-6xl px-5 py-16">
        <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="text-sm font-medium text-primary">Your generated menu</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-normal">
              {result ? `${result.recipes.length} calm recipe ideas` : "Recipes will appear here"}
            </h2>
          </div>
          <div className="grid grid-cols-2 gap-8 text-sm">
            <Metric label="Candidates" value={String(result?.candidate_product_count ?? status?.candidate_product_count ?? 0)} />
            <Metric label="Saved" value={`EUR ${totalSavings.toFixed(2)}`} strong />
          </div>
        </div>

        {result?.warnings.length ? (
          <Alert className="mb-6 border-accent/30 bg-accent/10 text-foreground">
            <AlertDescription>{result.warnings.join(" ")}</AlertDescription>
          </Alert>
        ) : null}

        {result ? (
          <div className="space-y-5">
            {result.recipes.map((recipe) => (
              <RecipeCard recipe={recipe} key={recipe.title} />
            ))}
          </div>
        ) : (
          <Card className="border-dashed">
            <CardContent className="flex min-h-[320px] flex-col items-center justify-center p-10 text-center text-muted-foreground">
              <ShoppingBasket size={36} />
              <h3 className="mt-4 text-lg font-medium text-foreground">No recipes loaded yet</h3>
              <p className="mt-2 max-w-sm text-sm">Generate recipes from the current AH Bonus dataset when you are ready.</p>
            </CardContent>
          </Card>
        )}
      </section>

      <FinalCallToAction />
    </main>
  );
}

function TopBar({
  status,
  loading,
  onRefresh
}: {
  status: DatasetStatus | null;
  loading: boolean;
  onRefresh: () => Promise<void>;
}) {
  return (
    <header className="sticky top-0 z-20 border-b bg-background/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-5">
        <a className="flex min-w-0 flex-1 items-center gap-3 text-foreground no-underline" href="#">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <ChefHat size={19} />
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold">AH Bonus Recipe Finder</span>
            <span className="hidden text-xs text-muted-foreground sm:block">Save more. Cook simply.</span>
          </span>
        </a>
        <div className="flex shrink-0 items-center gap-2">
          <Badge className="hidden sm:inline-flex" variant={status?.dataset_exists ? "secondary" : "accent"}>
            {status?.dataset_exists ? `Week ${status.week_start}` : "Dataset missing"}
          </Badge>
          <Button variant="ghost" size="icon" type="button" onClick={onRefresh} aria-label="Refresh status">
            <RefreshCw className={loading ? "animate-spin" : ""} size={16} />
          </Button>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section
      className="relative isolate min-h-[520px] overflow-hidden sm:min-h-[600px]"
      style={{
        backgroundImage: "url('https://images.unsplash.com/photo-1748819762573-757719316340?auto=format&fit=crop&w=1800&q=80')",
        backgroundPosition: "center",
        backgroundSize: "cover"
      }}
    >
      <div className="absolute inset-0 bg-[#2c241c]/55" />
      <div className="relative mx-auto flex min-h-[520px] max-w-6xl items-center px-5 py-20 sm:min-h-[600px] sm:py-24">
        <div className="w-full max-w-[20rem] text-white sm:max-w-2xl">
          <Badge className="bg-white/20 text-white backdrop-blur" variant="outline">
            Warm weekend cooking, guided by this week's deals
          </Badge>
          <h1 className="mt-6 text-3xl font-semibold leading-[1.08] tracking-normal sm:text-6xl">
            Simple recipes from the AH Bonus products you already want to use.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-8 text-white/88">
            Plan a personal meal in minutes, see the discounted products clearly, and keep cooking relaxed.
          </p>
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg">
              <a href="#create">
                Start creating
                <ArrowRight size={17} />
              </a>
            </Button>
            <Button asChild className="bg-white/15 text-white hover:bg-white/25" size="lg" variant="outline">
              <a href="#how-it-works">See how it works</a>
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}

function GeneratorCard({
  advancedOpen,
  error,
  form,
  loading,
  status,
  onAdvancedOpenChange,
  onAllergyToggle,
  onFormChange,
  onSubmit
}: {
  advancedOpen: boolean;
  error: string | null;
  form: typeof defaultForm;
  loading: boolean;
  status: DatasetStatus | null;
  onAdvancedOpenChange: (open: boolean) => void;
  onAllergyToggle: (allergy: string) => void;
  onFormChange: (form: typeof defaultForm) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Card className="bg-card/95">
      <CardHeader>
        <CardTitle>Create your recipe</CardTitle>
        <CardDescription>
          {status?.dataset_exists
            ? `${status.product_count} Bonus products are available for this week.`
            : "Run the weekly scraper before generating recipes."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {error ? <ErrorMessage message={error} /> : null}
        {!status?.openai_configured ? (
          <Alert className="mb-5 border-accent/30 bg-accent/10 text-foreground">
            <AlertDescription>Recipe generation needs the backend to run with OPENAI_API_KEY. Latest saved recipes can still be viewed below.</AlertDescription>
          </Alert>
        ) : null}

        <form className="space-y-6" onSubmit={onSubmit}>
          <div className="grid grid-cols-2 gap-3">
            <NumberField
              label="People"
              icon={<Users size={15} />}
              min={1}
              max={20}
              value={form.servings}
              onChange={(servings) => onFormChange({ ...form, servings })}
            />
            <NumberField
              label="Recipes"
              icon={<Sparkles size={15} />}
              min={1}
              max={10}
              value={form.recipeCount}
              onChange={(recipeCount) => onFormChange({ ...form, recipeCount })}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField
              label="Cuisine"
              value={form.cuisine}
              options={cuisines}
              onChange={(cuisine) => onFormChange({ ...form, cuisine })}
            />
            <SelectField
              label="Diet"
              value={form.diet}
              options={diets}
              onChange={(diet) => onFormChange({ ...form, diet })}
            />
          </div>

          <SegmentedControl
            label="Meal"
            value={form.mealType}
            options={mealTypes}
            onChange={(mealType) => onFormChange({ ...form, mealType })}
          />

          <NumberField
            label="Minimum bonus products"
            icon={<ShoppingBasket size={15} />}
            min={1}
            max={10}
            value={form.minimumBonusProducts}
            onChange={(minimumBonusProducts) => onFormChange({ ...form, minimumBonusProducts })}
          />

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="candidate-limit">Candidate products</Label>
              <span className="text-sm text-muted-foreground">{form.candidateLimit}</span>
            </div>
            <Slider
              id="candidate-limit"
              aria-label="Candidate products"
              min={30}
              max={160}
              step={10}
              value={[form.candidateLimit]}
              onValueChange={([candidateLimit]) =>
                onFormChange({ ...form, candidateLimit: candidateLimit ?? form.candidateLimit })
              }
            />
          </div>

          <Collapsible open={advancedOpen} onOpenChange={onAdvancedOpenChange}>
            <div className="rounded-lg border bg-background/70">
              <CollapsibleTrigger asChild>
                <Button className="h-auto w-full justify-between px-4 py-3" type="button" variant="ghost">
                  Fine tune preferences
                  <span className="text-muted-foreground">{advancedOpen ? "-" : "+"}</span>
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="space-y-4 border-t px-4 py-4">
                <div className="grid grid-cols-2 gap-3">
                  <SelectField
                    label="Spice"
                    value={form.spiceLevel}
                    options={spiceLevels}
                    onChange={(spiceLevel) => onFormChange({ ...form, spiceLevel })}
                  />
                  <SelectField
                    label="Skill"
                    value={form.skillLevel}
                    options={skillLevels}
                    onChange={(skillLevel) => onFormChange({ ...form, skillLevel })}
                  />
                  <SelectField
                    label="Budget"
                    value={form.budget}
                    options={budgets}
                    onChange={(budget) => onFormChange({ ...form, budget })}
                  />
                  <NumberField
                    label="Minutes"
                    icon={<Clock size={15} />}
                    min={5}
                    max={240}
                    value={form.maxCookingMinutes}
                    onChange={(maxCookingMinutes) => onFormChange({ ...form, maxCookingMinutes })}
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
                        onClick={() => onAllergyToggle(allergy)}
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
                  onChange={(mainIngredients) => onFormChange({ ...form, mainIngredients })}
                />
                <TextField
                  label="Disliked ingredients"
                  value={form.dislikedIngredients}
                  placeholder="coriander, mushrooms"
                  onChange={(dislikedIngredients) => onFormChange({ ...form, dislikedIngredients })}
                />
                <TextField
                  label="Equipment"
                  value={form.equipment}
                  placeholder="oven, blender, air fryer"
                  onChange={(equipment) => onFormChange({ ...form, equipment })}
                />
              </CollapsibleContent>
            </div>
          </Collapsible>

          <Button
            className="h-11 w-full"
            type="submit"
            disabled={loading || !status?.dataset_exists || !status?.openai_configured}
          >
            {loading ? <Loader2 className="animate-spin" size={17} /> : <Search size={17} />}
            Generate recipes
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function HowItWorksSection() {
  return (
    <section id="how-it-works" className="border-y bg-card/55">
      <div className="mx-auto max-w-6xl px-5 py-16">
        <SectionHeading
          eyebrow="How it works"
          title="A calm path from weekly deals to dinner."
          text="The experience is designed to make choices feel manageable, not mechanical."
        />
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {howItWorks.map(([title, text], index) => (
            <Card className="transition-colors hover:bg-secondary/40" key={title}>
              <CardHeader>
                <Badge className="w-fit" variant="secondary">0{index + 1}</Badge>
                <CardTitle className="text-xl">{title}</CardTitle>
                <CardDescription>{text}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

function RecipeMoodSection() {
  return (
    <section className="mx-auto max-w-6xl px-5 py-16">
      <SectionHeading
        eyebrow="Recipe styles"
        title="Fresh ideas without a complicated shopping list."
        text="Use Bonus products as the anchor, then let pantry staples and simple techniques fill in the rest."
      />
      <div className="mt-10 grid gap-4 md:grid-cols-3">
        {recipeMoods.map(([title, text]) => (
          <Card className="transition-transform duration-200 hover:-translate-y-0.5 hover:bg-secondary/35" key={title}>
            <CardContent className="p-5">
              <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-full bg-secondary text-primary">
                <Utensils size={19} />
              </div>
              <h3 className="text-lg font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{text}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

function TimeSavingsSection() {
  return (
    <section className="bg-secondary/35">
      <div className="mx-auto grid max-w-6xl gap-10 px-5 py-16 lg:grid-cols-[0.85fr_1.15fr]">
        <div>
          <p className="text-sm font-medium text-primary">Why it saves time</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-normal">Less browsing, fewer guesses, clearer cooking.</h2>
          <p className="mt-5 text-base leading-7 text-muted-foreground">
            The app narrows the weekly Bonus dataset before recipe generation, then shows the practical details that matter at the stove.
          </p>
        </div>
        <div className="grid gap-3">
          {timeSavers.map((item) => (
            <Card className="bg-card/80" key={item}>
              <CardContent className="flex items-start gap-3 p-4">
                <Timer className="mt-0.5 text-primary" size={18} />
                <p className="text-sm leading-6 text-muted-foreground">{item}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

function FinalCallToAction() {
  return (
    <section className="border-t bg-card">
      <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 px-5 py-14 sm:flex-row sm:items-center">
        <div>
          <p className="text-sm font-medium text-primary">Ready when you are</p>
          <h2 className="mt-2 max-w-2xl text-3xl font-semibold tracking-normal">
            Turn this week's Bonus into a meal that feels personal, simple, and worth cooking.
          </h2>
        </div>
        <Button asChild size="lg" variant="accent">
          <a href="#create">
            Create a recipe
            <ArrowRight size={17} />
          </a>
        </Button>
      </div>
    </section>
  );
}

function SectionHeading({ eyebrow, title, text }: { eyebrow: string; title: string; text: string }) {
  return (
    <div className="max-w-2xl">
      <p className="text-sm font-medium text-primary">{eyebrow}</p>
      <h2 className="mt-3 text-2xl font-semibold tracking-normal sm:text-4xl">{title}</h2>
      <p className="mt-4 text-base leading-7 text-muted-foreground">{text}</p>
    </div>
  );
}

function SoftStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-primary">{value}</p>
    </div>
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
          <div className="min-w-[168px] rounded-lg border bg-secondary p-4 text-right">
            <p className="text-sm text-muted-foreground">{recipe.savings.savings_label}</p>
            <p className="mt-1 text-2xl font-semibold text-accent">EUR {recipe.savings.savings.toFixed(2)}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
          <span>{recipe.savings.baseline_total_label}: EUR {recipe.savings.baseline_total.toFixed(2)}</span>
          <span>{recipe.savings.promo_total_label}: EUR {recipe.savings.promo_total.toFixed(2)}</span>
        </div>
        {recipe.savings.notes.map((note) => (
          <p className="text-sm text-muted-foreground" key={note}>
            {note}
          </p>
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
          <Alert className="border-accent/30 bg-accent/10 text-foreground">
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
          className="grid grid-cols-[52px_minmax(0,1fr)] gap-3 rounded-lg border p-3 text-sm no-underline transition-colors hover:bg-secondary/55"
          href={product.url ?? undefined}
          target="_blank"
          rel="noreferrer"
          key={`${product.product_id}-${product.title}`}
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-md bg-muted">
            {product.image_url ? (
              <img className="h-12 w-12 object-contain" src={product.image_url} alt="" loading="lazy" />
            ) : (
              <ShoppingBasket size={20} />
            )}
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
          <div
            className="grid grid-cols-[minmax(0,1fr)_auto_auto] gap-4 px-3 py-2 text-sm"
            key={`${ingredient.name}-${index}`}
          >
            <span className={ingredient.bonus_product_id ? "font-medium" : ""}>{ingredient.name}</span>
            <span className="text-muted-foreground">
              {formatQuantity(ingredient.quantity)} {ingredient.unit}
            </span>
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
    <Alert className="mb-6 border-accent/30 bg-accent/10 text-foreground">
      <AlertCircle size={16} />
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}

function Metric({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="text-right">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className={strong ? "text-lg font-semibold text-accent" : "text-lg font-medium"}>{value}</p>
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
      <Label className="flex items-center gap-2">
        {icon}
        {label}
      </Label>
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
          <option value={option} key={option}>
            {option}
          </option>
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
          <Button
            type="button"
            className="h-8 px-2"
            variant={value === option ? "secondary" : "ghost"}
            onClick={() => onChange(option)}
            key={option}
          >
            {option}
          </Button>
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
