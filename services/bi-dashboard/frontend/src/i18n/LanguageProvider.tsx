// services/bi-dashboard/frontend/src/i18n/LanguageProvider.tsx
import { createContext, useContext, useState, ReactNode } from "react";
import tr, { TranslationKey } from "./tr";
import en from "./en";

type Language = "tr" | "en";

const translations = { tr, en };

interface LanguageContextValue {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextValue>({
  language: "tr",
  setLanguage: () => {},
  t: (key) => tr[key] ?? en[key] ?? key,
});

function getInitialLanguage(): Language {
  try {
    const saved = localStorage.getItem("subop_language");
    if (saved === "tr" || saved === "en") return saved;
  } catch {}
  return "tr";
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(getInitialLanguage);

  function setLanguage(lang: Language) {
    setLanguageState(lang);
    try { localStorage.setItem("subop_language", lang); } catch {}
  }

  function t(key: TranslationKey): string {
    return translations[language][key] ?? translations["tr"][key] ?? key;
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useT() {
  return useContext(LanguageContext);
}
