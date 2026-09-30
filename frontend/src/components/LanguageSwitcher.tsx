"use client";

import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { LANGUAGE_NAMES, LOCALE_COOKIE } from "@/i18n/config";

const ONE_YEAR = 60 * 60 * 24 * 365;

/* Picks the language for the whole app: the page text, the text direction and the
   language the chat replies in. The choice is a cookie the server reads on each request. */
export function LanguageSwitcher() {
  const locale = useLocale();
  const t = useTranslations("language");
  const router = useRouter();

  const change = (next: string) => {
    document.cookie = `${LOCALE_COOKIE}=${next}; path=/; max-age=${ONE_YEAR}; samesite=lax`;
    router.refresh();
  };

  return (
    <select
      value={locale}
      onChange={(e) => change(e.target.value)}
      aria-label={t("label")}
      className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400"
    >
      {Object.entries(LANGUAGE_NAMES).map(([code, name]) => (
        <option key={code} value={code} lang={code}>
          {name}
        </option>
      ))}
    </select>
  );
}
