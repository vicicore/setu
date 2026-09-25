"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Language, TranslationKey, translations } from "./translations";

interface LanguageContextValue {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>("en");

  useEffect(() => {
    // Reading localStorage — an external system unavailable during SSR
    // — is the documented "synchronize with an external system" case,
    // not derived state.
    try {
      const stored = localStorage.getItem("setu-language");
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (stored === "en" || stored === "mr") setLanguageState(stored);
    } catch {
      // localStorage unavailable (private browsing, etc.) — default to English.
    }
  }, []);

  const setLanguage = useCallback((lang: Language) => {
    setLanguageState(lang);
    try {
      localStorage.setItem("setu-language", lang);
    } catch {
      // Best-effort only; language still applies for this session.
    }
  }, []);

  const t = useCallback(
    (key: TranslationKey) => translations[key][language],
    [language],
  );

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}
