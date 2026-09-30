import { cookies } from "next/headers";
import { getRequestConfig } from "next-intl/server";
import { DEFAULT_LANGUAGE, isLanguage, LOCALE_COOKIE } from "./config";

// The language is a cookie, not part of the URL, so the same page serves every language.
export default getRequestConfig(async () => {
  const stored = (await cookies()).get(LOCALE_COOKIE)?.value;
  const locale = isLanguage(stored) ? stored : DEFAULT_LANGUAGE;
  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
