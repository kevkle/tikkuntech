import type { Language } from "@/lib/types";

export const DEFAULT_LANGUAGE: Language = "en";

// The picker stores the person's choice here; the server reads it on every request.
export const LOCALE_COOKIE = "NEXT_LOCALE";

// Each language written in itself, so a person can find theirs whatever the page language is.
export const LANGUAGE_NAMES: Record<Language, string> = {
  en: "English",
  ar: "العربية",
  fr: "Français",
  de: "Deutsch",
};

const RTL_LANGUAGES: readonly Language[] = ["ar"];

export function isLanguage(value: unknown): value is Language {
  return typeof value === "string" && Object.keys(LANGUAGE_NAMES).includes(value);
}

export function dirOf(language: Language): "rtl" | "ltr" {
  return RTL_LANGUAGES.includes(language) ? "rtl" : "ltr";
}
