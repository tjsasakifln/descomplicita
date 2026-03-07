"use client";

import Image from "next/image";
import { SavedSearchesDropdown } from "./SavedSearchesDropdown";
import { ThemeToggle } from "./ThemeToggle";
import type { SavedSearch } from "../../lib/savedSearches";

interface SearchHeaderProps {
  onLoadSearch: (search: SavedSearch) => void;
  onAnalyticsEvent: (eventName: string, properties?: Record<string, any>) => void;
}

export function SearchHeader({ onLoadSearch, onAnalyticsEvent }: SearchHeaderProps) {
  return (
    <header className="border-b border-strong bg-surface-0 sticky top-0 z-40">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
        <div className="flex items-center gap-3">
          <Image
            src="/logo-descomplicita.png"
            alt="DescompLicita"
            width={140}
            height={67}
            className="h-10 w-auto"
            priority
          />
        </div>
        <div className="flex items-center gap-4">
          <span className="hidden sm:block text-xs text-ink-muted font-medium">
            Busca Inteligente de Licitações
          </span>
          <SavedSearchesDropdown
            onLoadSearch={onLoadSearch}
            onAnalyticsEvent={onAnalyticsEvent}
          />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
