import type { Metadata, Viewport } from "next";

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
  colorScheme: "light",
  themeColor: "#0f766e",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <a
          className="fixed left-4 top-4 z-50 -translate-y-24 rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition focus:translate-y-0"
          href="#main-content"
        >
          Skip to content
        </a>
        {children}
      </body>
    </html>
  );
}
