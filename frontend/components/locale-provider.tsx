"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import { canonicalizeLocale, supportedLocales, type Locale } from "@/lib/i18n";

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  toggleLocale: () => void;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

// Researcher (admin) and participant (survey runner) locales are persisted
// under SEPARATE storage keys so a participant changing language on the
// survey page no longer flips the researcher dashboard's language. Other
// surfaces (auth, landing) keep the legacy "locale" key for back-compat.
// See issue #59.
export function localeStorageKeyForPath(pathname: string | null | undefined): string {
  if (!pathname) return "locale";
  if (pathname.startsWith("/admin")) return "admin_locale";
  if (pathname.startsWith("/survey/")) return "participant_locale";
  return "locale";
}

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const storageKey = localeStorageKeyForPath(pathname);

  const [locale, setLocaleState] = useState<Locale>("en");
  // Tracks whether we've finished reading localStorage on mount. Without
  // this gate the persistence effect would run with the initial "en" state
  // before the hydration effect had a chance to swap in the saved locale,
  // clobbering whatever value the bootstrap script restored on first paint.
  const [hydrated, setHydrated] = useState(false);

  // Re-runs when storageKey changes (i.e. when the user navigates between
  // /admin and /survey segments), so the live locale snaps to whichever
  // key owns that segment.
  useEffect(() => {
    setHydrated(false);
    let saved = window.localStorage.getItem(storageKey);
    // Back-compat: if the namespaced key hasn't been written yet, fall back
    // to the legacy shared "locale" so existing users don't reset on the
    // first post-deploy load.
    if (!saved && storageKey !== "locale") {
      saved = window.localStorage.getItem("locale");
    }
    // canonicalizeLocale migrates the legacy "zh" / case variants to canonical
    // forms. Crucially, we only call setLocaleState when we
    // have a real value to set — otherwise a fresh load with no saved
    // locale would clobber a setLocale() call that a child component just
    // issued from the URL ?lang= query (React runs child effects BEFORE
    // parent effects, so without this guard the parent would always win).
    const canonical = canonicalizeLocale(saved);
    if (canonical) {
      setLocaleState(canonical);
    }
    setHydrated(true);
  }, [storageKey]);

  useEffect(() => {
    if (!hydrated) return;
    window.localStorage.setItem(storageKey, locale);
    document.documentElement.lang = locale;
  }, [locale, hydrated, storageKey]);

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      setLocale: setLocaleState,
      // Cycles through every supported locale so the toggle keeps working
      // when more locales are added.
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
