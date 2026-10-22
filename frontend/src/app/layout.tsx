import type { Metadata, Viewport } from "next";

import { AuthProvider } from "@/components/auth/auth-provider";
import { InterfacePreferencesBridge } from "@/components/settings/interface-preferences";
import { THEME_INIT_SCRIPT } from "@/lib/settings/theme-init";

import "@fontsource-variable/inter";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "HealthLink | Connected care, centered on people",
    template: "%s | HealthLink",
  },
  description:
    "A secure healthcare information platform designed to keep every citizen's care story connected.",
};

export const viewport: Viewport = {
  colorScheme: "light dark",
  themeColor: "#0f766e",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html data-scroll-behavior="smooth" data-theme="light" lang="en" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} /></head>
      <body>
        <InterfacePreferencesBridge />
        <a
          className="fixed left-4 top-4 z-50 -translate-y-24 rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition focus:translate-y-0"
          href="#main-content"
        >
          Skip to content
        </a>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
