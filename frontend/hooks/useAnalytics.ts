// eslint-disable-next-line @typescript-eslint/no-explicit-any
let mixpanelInstance: any = null;
let mixpanelLoading: Promise<void> | null = null;

function loadMixpanel(): Promise<void> {
  if (mixpanelLoading) return mixpanelLoading;
  if (!process.env.NEXT_PUBLIC_MIXPANEL_TOKEN) return Promise.resolve();

  mixpanelLoading = import('mixpanel-browser').then(mod => {
    mixpanelInstance = mod.default || mod;
  }).catch(() => {
    // Analytics import failure must never break the app
    void 0;
  });
  return mixpanelLoading;
}

export const useAnalytics = () => {
  const trackEvent = (eventName: string, properties?: Record<string, unknown>) => {
    if (!process.env.NEXT_PUBLIC_MIXPANEL_TOKEN) return;
    loadMixpanel().then(() => {
      try {
        mixpanelInstance?.track(eventName, {
          ...properties,
          timestamp: new Date().toISOString(),
          environment: process.env.NODE_ENV || 'development',
        });
      } catch {
        // Analytics must never break the app
        void 0;
      }
    });
  };

  const identifyUser = (userId: string, properties?: Record<string, unknown>) => {
    if (!process.env.NEXT_PUBLIC_MIXPANEL_TOKEN) return;
    loadMixpanel().then(() => {
      try {
        mixpanelInstance?.identify(userId);
        if (properties) {
          mixpanelInstance?.people.set(properties);
        }
      } catch {
        // Analytics must never break the app
        void 0;
      }
    });
  };

  const trackPageView = (pageName: string) => {
    trackEvent('page_view', { page: pageName });
  };

  return {
    trackEvent,
    identifyUser,
    trackPageView,
  };
};
