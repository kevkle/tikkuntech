import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

// Must match backend/app/schemas.py Language.
const LANGUAGES = ["en", "ar", "fr", "de"];

const load = (language) =>
  JSON.parse(readFileSync(new URL(`../messages/${language}.json`, import.meta.url), "utf-8"));

// "a.b.c" for every string leaf, so a missing or extra key shows up by name.
const leaves = (value, prefix = "") =>
  Object.entries(value).flatMap(([key, child]) =>
    typeof child === "object" && child !== null
      ? leaves(child, `${prefix}${key}.`)
      : [[`${prefix}${key}`, child]],
  );

// {name}-style placeholders inside a message, sorted so the order can differ per language.
const placeholders = (text) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

const english = new Map(leaves(load("en")));

for (const language of LANGUAGES.filter((l) => l !== "en")) {
  const translated = new Map(leaves(load(language)));

  test(`${language} has exactly the English keys`, () => {
    assert.deepEqual([...translated.keys()].sort(), [...english.keys()].sort());
  });

  test(`${language} has no empty message`, () => {
    for (const [key, text] of translated) {
      assert.ok(typeof text === "string" && text.trim() !== "", `${language}: ${key} is empty`);
    }
  });

  test(`${language} keeps the English placeholders`, () => {
    for (const [key, text] of translated) {
      assert.deepEqual(placeholders(text), placeholders(english.get(key) ?? ""), `${language}: ${key}`);
    }
  });
}

test("english has no empty message", () => {
  for (const [key, text] of english) {
    assert.ok(typeof text === "string" && text.trim() !== "", `en: ${key} is empty`);
  }
});
