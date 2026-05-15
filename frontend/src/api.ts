import type { DatasetStatus, RecipeGenerationResult, RecipePreferences } from "./types";

export async function getStatus(): Promise<DatasetStatus> {
  return apiGet<DatasetStatus>("/api/status");
}

export async function getLatestRecipes(): Promise<RecipeGenerationResult> {
  return apiGet<RecipeGenerationResult>("/api/latest-recipes");
}

export async function generateRecipes(
  preferences: RecipePreferences,
  candidateLimit: number
): Promise<RecipeGenerationResult> {
  const response = await fetch("/api/recipes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      preferences,
      candidate_limit: candidateLimit
    })
  });
  return parseResponse<RecipeGenerationResult>(response);
}

async function apiGet<T>(url: string): Promise<T> {
  const response = await fetch(url);
  return parseResponse<T>(response);
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }
  return payload as T;
}
