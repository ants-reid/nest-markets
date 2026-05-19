import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { LearningModeProvider } from "../lib/learningMode";
import { AppShell } from "../components/shell/AppShell";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Market Hunter MVP",
  description: "Minimal frontend shell for the Market Hunter MVP workflow.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function () {
                try {
                  var root = document.documentElement;
                  var saved = window.localStorage.getItem("mh-theme");
                  var nextTheme = saved === "light" || saved === "dark"
                    ? saved
                    : (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
                  root.setAttribute("data-theme", nextTheme);
                } catch (_) {}
              })();
            `,
          }}
        />
      </head>
      <body>
        <LearningModeProvider>
          <AppShell>{children}</AppShell>
        </LearningModeProvider>
      </body>
    </html>
  );
}