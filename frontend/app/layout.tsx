import type { Metadata } from "next";
import { DM_Sans, Fahkwang, DM_Mono } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { ThemeProvider } from "./components/ThemeProvider";
import { AnalyticsProvider } from "./components/AnalyticsProvider";
import { NetworkIndicator } from "./components/NetworkIndicator";

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

const fahkwang = Fahkwang({
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const dmMono = DM_Mono({
  weight: ["400", "500"],
  subsets: ["latin"],
  variable: "--font-data",
  display: "swap",
});

export const metadata: Metadata = {
  title: "DescompLicita",
  description: "Licitações e Contratos de Forma Descomplicada — Busca inteligente em fontes oficiais",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning className={`${dmSans.variable} ${fahkwang.variable} ${dmMono.variable}`}>
      <head>
        <Script src="/theme-init.js" strategy="beforeInteractive" />
      </head>
      <body>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50
                     focus:px-4 focus:py-2 focus:bg-brand-navy focus:text-white focus:rounded-button
                     focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        >
          Pular para o conteúdo principal
        </a>
        <AnalyticsProvider>
          <ThemeProvider>
            <NetworkIndicator />
            {children}
          </ThemeProvider>
        </AnalyticsProvider>
      </body>
    </html>
  );
}
