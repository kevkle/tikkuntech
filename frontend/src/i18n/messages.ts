import type { AbstractIntlMessages } from "next-intl";
import type { Language } from "@/lib/types";
import ar from "../../messages/ar.json";
import de from "../../messages/de.json";
import en from "../../messages/en.json";
import fr from "../../messages/fr.json";

// Every language's messages, so a part of the UI can follow the post's language
// instead of the picker's. The provider in the layout only carries the picked one.
export const MESSAGES: Record<Language, AbstractIntlMessages> = { en, ar, fr, de };
