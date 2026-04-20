"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { Locale } from "@/lib/i18n";

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  toggleLocale: () => void;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    const saved = window.localStorage.getItem("locale");
    if (saved === "zh" || saved === "en") {
      setLocaleState(saved);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem("locale", locale);
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      setLocale: setLocaleState,
      toggleLocale: () => setLocaleState((prev) => (prev === "en" ? "zh" : "en")),
    }),
    [locale],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const value = useContext(LocaleContext);
  if (!value) {
    throw new Error("useLocale must be used within a LocaleProvider");
  }
  return value;
}
