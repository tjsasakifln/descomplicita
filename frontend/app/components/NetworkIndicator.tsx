"use client";

import { useState, useEffect } from "react";

export function NetworkIndicator() {
  const [isOffline, setIsOffline] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    setIsOffline(!navigator.onLine);

    const handleOffline = () => { setIsOffline(true); setDismissed(false); };
    const handleOnline = () => setIsOffline(false);

    window.addEventListener("offline", handleOffline);
    window.addEventListener("online", handleOnline);
    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online", handleOnline);
    };
  }, []);

  if (!isOffline || dismissed) return null;

  return (
    <div
      role="alert"
      className="fixed top-0 left-0 right-0 z-50 bg-warning-subtle border-b border-warning/30 px-4 py-2.5 flex items-center justify-between animate-fade-in"
    >
      <div className="flex items-center gap-2 text-sm font-medium" style={{ color: "var(--status-warning-text)" }}>
        <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round"
                d="M18.364 5.636a9 9 0 010 12.728M5.636 18.364a9 9 0 010-12.728M12 12h.01" />
        </svg>
        <span>Sem conexão com a internet. Algumas funcionalidades podem não estar disponíveis.</span>
      </div>
      <button
        type="button"
        onClick={() => setDismissed(true)}
        className="ml-4 p-1 rounded hover:bg-warning/10 transition-colors flex-shrink-0"
        aria-label="Fechar aviso"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}
