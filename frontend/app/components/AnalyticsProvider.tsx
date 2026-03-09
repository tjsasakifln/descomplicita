"use client";

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';

/**
 * Analytics Provider - Initializes Mixpanel lazily and tracks page views
 * UXD-008: Mixpanel loaded via dynamic import (~40KB savings from initial bundle)
 */
export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  useEffect(() => {
    const token = process.env.NEXT_PUBLIC_MIXPANEL_TOKEN;
    if (!token) {
      console.warn('[Analytics] NEXT_PUBLIC_MIXPANEL_TOKEN not found. Analytics disabled.');
      return;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let mp: any = null;

    import('mixpanel-browser').then(mod => {
      mp = mod.default || mod;
      try {
        mp.init(token, {
          debug: process.env.NODE_ENV === 'development',
          track_pageview: false,
          persistence: 'localStorage',
        });

        mp.track('page_load', {
          path: pathname,
          timestamp: new Date().toISOString(),
          environment: process.env.NODE_ENV || 'development',
          referrer: document.referrer || 'direct',
          user_agent: navigator.userAgent,
        });

        console.log('[Analytics] Mixpanel initialized successfully');
      } catch (error) {
        console.warn('[Analytics] Mixpanel initialization failed:', error);
      }
    }).catch(error => {
      console.warn('[Analytics] Failed to load Mixpanel:', error);
    });

    const handleBeforeUnload = () => {
      if (mp) {
        try {
          const sessionDuration = Date.now() - performance.timeOrigin;
          mp.track('page_exit', {
            path: pathname,
            session_duration_ms: sessionDuration,
            session_duration_readable: `${Math.floor(sessionDuration / 1000)}s`,
            timestamp: new Date().toISOString(),
          });
        } catch {
          // Silently fail
        }
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [pathname]);

  return <>{children}</>;
}
