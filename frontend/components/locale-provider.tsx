"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { isLocale, localeDir, supportedLocales, type Locale } from "@/lib/i18n";

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  toggleLocale: () => void;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");
  // Tracks whether we've finished reading localStorage on mount. Without
  // this gate the persistence effect would run with the initial "en" state
  // before the hydration effect had a chance to swap in the saved locale,
  // clobbering whatever value the bootstrap script restored on first paint.
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem("locale");
    if (isLocale(saved)) {
      setLocaleState(saved);
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    window.localStorage.setItem("locale", locale);
    document.documentElement.lang = locale;
    document.documentElement.dir = localeDir(locale);
  }, [locale, hydrated]);

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      setLocale: setLocaleState,
      // Cycles through every supported locale so the toggle keeps working
      // when more locales are added (and Arabic isn't skipped).
      toggleLocale: () =>
        setLocaleState((prev) => {
          const idx = supportedLocales.indexOf(prev);
          return supportedLocales[(idx + 1) % supportedLocales.length];
        }),
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
