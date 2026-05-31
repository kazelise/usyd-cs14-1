import "./globals.css";
import type { Metadata } from "next";
import { LocaleProvider } from "@/components/locale-provider";

export const metadata: Metadata = {
  title: "CS14 Survey Platform",
  description: "Social media survey platform with gaze tracking",
};

// Runs synchronously in <head> before React hydrates. Reads the cached
// locale from localStorage (or a ?lang= query override, useful for
// link-shareable previews and translator screenshots) and applies <html lang>
// so the very first paint is already in the correct locale. Without this the
// page flashes English for one frame before LocaleProvider's effect swaps in
// the saved locale.
// Picks the same admin/participant/default storage key that LocaleProvider
// computes, so first paint reflects the right locale even before React
// hydrates. Keep the key logic mirrored across both places.
// Locales kept in sync with frontend/lib/i18n.ts supportedLocales. The
// canonicalizer (case-insensitive, shared by the URL query and saved storage)
// migrates the legacy "zh" to zh-CN so ?lang=zh / ZH-CN / zh-tw all resolve
// instead of getting silently dropped. Mirror the alias map in
// frontend/lib/i18n.ts so the React provider applies the same rules.
const localeBootstrapScript = `(function () {
  try {
    var SUPPORTED = ['en','zh-CN','zh-TW','ja','ko','es'];
    function canonicalize(v) {
      if (!v) return null;
      // Already canonical (case-sensitive)?
      if (SUPPORTED.indexOf(v) !== -1) return v;
      var lower = ('' + v).toLowerCase();
      // Legacy aliases / lowercase variants.
      if (lower === 'zh' || lower === 'zh-cn') return 'zh-CN';
      if (lower === 'zh-tw') return 'zh-TW';
      // Case-insensitive match against canonical list (handles ZH-CN, JA, KO, EN, ES).
      for (var i = 0; i < SUPPORTED.length; i++) {
        if (SUPPORTED[i].toLowerCase() === lower) return SUPPORTED[i];
      }
      return null;
    }
    var path = window.location.pathname;
    var key = path.indexOf('/admin') === 0 ? 'admin_locale'
            : path.indexOf('/survey/') === 0 ? 'participant_locale'
            : 'locale';
    var rawQ = new URLSearchParams(window.location.search).get('lang');
    var l = canonicalize(rawQ) || canonicalize(window.localStorage.getItem(key));
    if (!l && key !== 'locale') {
      // Back-compat: migrate from the legacy shared key on first load.
      l = canonicalize(window.localStorage.getItem('locale'));
    }
    if (l) {
      window.localStorage.setItem(key, l);
      document.documentElement.lang = l;
    }
  } catch (e) {}
})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: localeBootstrapScript }} />
      </head>
      <body className="bg-gray-50 text-gray-900 min-h-screen">
        <LocaleProvider>
          <svg
            aria-hidden="true"
            className="pointer-events-none absolute h-0 w-0 overflow-hidden"
          >
            <defs>
              <filter
                id="liquid-glass-button-filter"
                x="-20%"
                y="-20%"
                width="140%"
                height="160%"
                colorInterpolationFilters="sRGB"
              >
                <feTurbulence
                  type="fractalNoise"
                  baseFrequency="0.012 0.028"
                  numOctaves="1"
                  seed="7"
                  result="noise"
                />
                <feGaussianBlur in="noise" stdDeviation="0.8" result="softNoise" />
                <feColorMatrix
                  in="softNoise"
                  type="matrix"
                  values="
                    1 0 0 0 0
                    0 1 0 0 0
                    0 0 1 0 0
                    0 0 0 16 -7
                  "
                  result="displacementMap"
                />
                <feDisplacementMap
                  in="SourceGraphic"
                  in2="displacementMap"
                  scale="26"
                  xChannelSelector="R"
                  yChannelSelector="G"
                  result="refracted"
                />
                <feGaussianBlur in="SourceAlpha" stdDeviation="5" result="buttonAlpha" />
                <feSpecularLighting
                  in="buttonAlpha"
                  surfaceScale="5"
                  specularConstant="1.05"
                  specularExponent="24"
                  lightingColor="white"
                  result="specular"
                >
                  <fePointLight x="-120" y="-160" z="220" />
                </feSpecularLighting>
                <feComposite in="specular" in2="SourceAlpha" operator="in" result="specularClipped" />
                <feBlend in="refracted" in2="specularClipped" mode="screen" />
              </filter>
            </defs>
          </svg>
          {children}
        </LocaleProvider>
      </body>
    </html>
  );
}
