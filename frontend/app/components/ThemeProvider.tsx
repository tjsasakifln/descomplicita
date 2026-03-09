"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";

export type ThemeId = "light" | "paperwhite" | "sepia" | "dim" | "dark";

interface ThemeConfig {
  id: ThemeId;
  label: string;
  isDark: boolean;
  canvas: string;
  ink: string;
  preview: string;
}

export const THEMES: ThemeConfig[] = [
  { id: "light", label: "Light", isDark: false, canvas: "#ffffff", ink: "#1e2d3b", preview: "#ffffff" },
  { id: "paperwhite", label: "Paperwhite", isDark: false, canvas: "#F5F0E8", ink: "#1e2d3b", preview: "#F5F0E8" },
  { id: "sepia", label: "Sépia", isDark: false, canvas: "#EDE0CC", ink: "#2c1810", preview: "#EDE0CC" },
  { id: "dim", label: "Dim", isDark: true, canvas: "#2A2A2E", ink: "#e0e0e0", preview: "#2A2A2E" },
  { id: "dark", label: "Dark", isDark: true, canvas: "#121212", ink: "#e0e0e0", preview: "#121212" },
];

interface ThemeContextType {
  theme: ThemeId;
  setTheme: (t: ThemeId) => void;
  config: ThemeConfig;
}

const ThemeContext = createContext<ThemeContextType>({
  theme: "light",
  setTheme: () => {},
  config: THEMES[0],
});

export function useTheme() {
  return useContext(ThemeContext);
}

function applyTheme(themeId: ThemeId) {
  const config = THEMES.find(t => t.id === themeId) || THEMES[0];
  const root = document.documentElement;

  // CSS cascade handles all variables via data-theme selectors in globals.css (UXD-010)
  root.setAttribute("data-theme", themeId);

  if (config.isDark) {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeId>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("descomplicita-theme") as ThemeId | null;
    const initial = stored && THEMES.some(t => t.id === stored) ? stored : "light";
    setThemeState(initial);
    applyTheme(initial);
    setMounted(true);
  }, []);

  const setTheme = useCallback((t: ThemeId) => {
    setThemeState(t);
    applyTheme(t);
    localStorage.setItem("descomplicita-theme", t);
  }, []);

  const config = THEMES.find(t => t.id === theme) || THEMES[0];

  if (!mounted) {
    return <>{children}</>;
  }

  return (
    <ThemeContext.Provider value={{ theme, setTheme, config }}>
      {children}
    </ThemeContext.Provider>
  );
}
