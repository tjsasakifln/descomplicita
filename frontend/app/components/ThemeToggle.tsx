"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useTheme, THEMES } from "./ThemeProvider";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const closeDropdown = useCallback(() => {
    setOpen(false);
    triggerRef.current?.focus();
  }, []);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && open) {
        closeDropdown();
      }
    }
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, closeDropdown]);

  // Focus first menu item when menu opens
  useEffect(() => {
    if (open && menuRef.current) {
      const items = menuRef.current.querySelectorAll<HTMLElement>('[role="menuitem"]');
      // Focus the currently selected theme item
      const activeIndex = THEMES.findIndex(t => t.id === theme);
      (items[activeIndex] || items[0])?.focus();
    }
  }, [open, theme]);

  const handleMenuKeyDown = (e: React.KeyboardEvent) => {
    const items = menuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]');
    if (!items || items.length === 0) return;

    const currentIndex = Array.from(items).findIndex(item => item === document.activeElement);

    switch (e.key) {
      case "ArrowDown": {
        e.preventDefault();
        const next = (currentIndex + 1) % items.length;
        items[next]?.focus();
        break;
      }
      case "ArrowUp": {
        e.preventDefault();
        const prev = (currentIndex - 1 + items.length) % items.length;
        items[prev]?.focus();
        break;
      }
      case "Home": {
        e.preventDefault();
        items[0]?.focus();
        break;
      }
      case "End": {
        e.preventDefault();
        items[items.length - 1]?.focus();
        break;
      }
    }
  };

  return (
    <div ref={ref} className="relative">
      <button
        ref={triggerRef}
        onClick={() => setOpen(!open)}
        type="button"
        aria-label="Alternar tema"
        aria-expanded={open}
        aria-haspopup="true"
        className="flex items-center gap-2 px-3 py-2 rounded-button border border-strong
                   bg-surface-0 text-ink-secondary
                   hover:border-accent transition-colors text-sm"
      >
        <span
          className="w-4 h-4 rounded-full border"
          style={{ backgroundColor: THEMES.find(t => t.id === theme)?.preview, borderColor: "var(--border-strong)" }}
        />
        <span className="hidden sm:inline">{THEMES.find(t => t.id === theme)?.label}</span>
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div
          ref={menuRef}
          role="menu"
          aria-label="Selecionar tema"
          onKeyDown={handleMenuKeyDown}
          className="absolute right-0 mt-2 w-48 rounded-card border border-strong
                          bg-surface-elevated shadow-sm z-50 overflow-hidden animate-fade-in"
        >
          {THEMES.map(t => (
            <button
              key={t.id}
              onClick={() => { setTheme(t.id); closeDropdown(); }}
              type="button"
              role="menuitem"
              tabIndex={-1}
              className={`w-full flex items-center gap-3 px-4 py-3 text-sm text-left
                         hover:bg-surface-1 transition-colors
                         ${theme === t.id ? "bg-brand-blue-subtle font-semibold" : ""}`}
            >
              <span
                className="w-5 h-5 rounded-full border flex-shrink-0"
                style={{
                  backgroundColor: t.preview,
                  borderColor: theme === t.id ? "var(--brand-blue)" : "var(--border-strong)",
                }}
              />
              <span className="text-ink">{t.label}</span>
              {theme === t.id && (
                <svg className="w-4 h-4 ml-auto text-brand-blue" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
