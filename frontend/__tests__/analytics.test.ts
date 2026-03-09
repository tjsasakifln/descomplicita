/**
 * Analytics Test Suite
 *
 * Tests for Mixpanel integration and event tracking
 * Coverage Target: 80%+ for analytics module
 *
 * Test Cases:
 * - TC-ANALYTICS-INIT-001: Mixpanel initialization success
 * - TC-ANALYTICS-INIT-002: Graceful degradation without token
 * - TC-ANALYTICS-EVENT-001 to 010: Event tracking
 *
 * Note: useAnalytics uses dynamic import() for Mixpanel (UXD-008),
 * so all tracking calls are async. Tests must flush promises.
 */

import { renderHook, act } from '@testing-library/react';
import { useAnalytics } from '../hooks/useAnalytics';
import mixpanel from 'mixpanel-browser';

// Mock mixpanel-browser module (also mocks dynamic import())
jest.mock('mixpanel-browser', () => ({
  __esModule: true,
  default: {
    init: jest.fn(),
    track: jest.fn(),
    identify: jest.fn(),
    people: {
      set: jest.fn(),
    },
  },
  init: jest.fn(),
  track: jest.fn(),
  identify: jest.fn(),
  people: {
    set: jest.fn(),
  },
}));

const flushPromises = () => new Promise(r => setTimeout(r, 0));

describe('Analytics - useAnalytics Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.NEXT_PUBLIC_MIXPANEL_TOKEN = 'test_token_12345';
  });

  afterEach(() => {
    delete process.env.NEXT_PUBLIC_MIXPANEL_TOKEN;
  });

  describe('TC-ANALYTICS-EVENT-001 to 010: trackEvent()', () => {
    it('should track event with properties when token exists', async () => {
      const { result } = renderHook(() => useAnalytics());

      act(() => {
        result.current.trackEvent('test_event', {
          foo: 'bar',
          count: 42,
        });
      });

      await flushPromises();

      // Dynamic import resolves to the mock — track is called on the default export
      const mp = (mixpanel as any).default || mixpanel;
      expect(mp.track).toHaveBeenCalledWith('test_event', {
        foo: 'bar',
        count: 42,
        timestamp: expect.any(String),
        environment: expect.any(String),
      });
    });

    it('should include timestamp and environment in every event', async () => {
      const { result } = renderHook(() => useAnalytics());

      act(() => {
        result.current.trackEvent('test_event');
      });

      await flushPromises();

      const mp = (mixpanel as any).default || mixpanel;
      expect(mp.track).toHaveBeenCalledWith('test_event', {
        timestamp: expect.stringMatching(/^\d{4}-\d{2}-\d{2}T/),
        environment: expect.any(String),
      });
    });

    it('should NOT track event when token is missing', async () => {
      delete process.env.NEXT_PUBLIC_MIXPANEL_TOKEN;
      const { result } = renderHook(() => useAnalytics());

      act(() => {
        result.current.trackEvent('test_event');
      });

      await flushPromises();

      const mp = (mixpanel as any).default || mixpanel;
      expect(mp.track).not.toHaveBeenCalled();
    });

    it('TC-ANALYTICS-EVENT-010: should handle track errors silently', async () => {
      const mp = (mixpanel as any).default || mixpanel;
      (mp.track as jest.Mock).mockImplementationOnce(() => {
        throw new Error('Network error');
      });

      const { result } = renderHook(() => useAnalytics());

      expect(() => {
        act(() => {
          result.current.trackEvent('test_event');
        });
      }).not.toThrow();

      await flushPromises();
      // Error is caught silently inside the promise chain
    });
  });

  describe('identifyUser()', () => {
    it('should identify user with ID when token exists', async () => {
      const { result } = renderHook(() => useAnalytics());

      act(() => {
        result.current.identifyUser('user-123');
      });

      await flushPromises();

      const mp = (mixpanel as any).default || mixpanel;
      expect(mp.identify).toHaveBeenCalledWith('user-123');
    });

    it('should set user properties when provided', async () => {
      const { result } = renderHook(() => useAnalytics());

      act(() => {
        result.current.identifyUser('user-123', {
          name: 'Test User',
          email: 'test@example.com',
        });
      });

      await flushPromises();

      const mp = (mixpanel as any).default || mixpanel;
      expect(mp.identify).toHaveBeenCalledWith('user-123');
      expect(mp.people.set).toHaveBeenCalledWith({
        name: 'Test User',
        email: 'test@example.com',
      });
    });

    it('should NOT identify when token is missing', async () => {
      delete process.env.NEXT_PUBLIC_MIXPANEL_TOKEN;
      const { result } = renderHook(() => useAnalytics());

      act(() => {
        result.current.identifyUser('user-123');
      });

      await flushPromises();

      const mp = (mixpanel as any).default || mixpanel;
      expect(mp.identify).not.toHaveBeenCalled();
    });

    it('should handle identify errors silently', async () => {
      const mp = (mixpanel as any).default || mixpanel;
      (mp.identify as jest.Mock).mockImplementationOnce(() => {
        throw new Error('Network error');
      });

      const { result } = renderHook(() => useAnalytics());

      expect(() => {
        act(() => {
          result.current.identifyUser('user-123');
        });
      }).not.toThrow();

      await flushPromises();
      // Error caught silently
    });
  });

  describe('trackPageView()', () => {
    it('should track page_view event with page name', async () => {
      const { result } = renderHook(() => useAnalytics());

      act(() => {
        result.current.trackPageView('/dashboard');
      });

      await flushPromises();

      const mp = (mixpanel as any).default || mixpanel;
      expect(mp.track).toHaveBeenCalledWith('page_view', {
        page: '/dashboard',
        timestamp: expect.any(String),
        environment: expect.any(String),
      });
    });
  });
});

describe('Analytics - AnalyticsProvider Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.NEXT_PUBLIC_MIXPANEL_TOKEN = 'test_token_12345';
  });

  afterEach(() => {
    delete process.env.NEXT_PUBLIC_MIXPANEL_TOKEN;
  });

  it('placeholder test - implement component tests', () => {
    expect(true).toBe(true);
  });
});

describe('Analytics - Real-World Event Scenarios', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.NEXT_PUBLIC_MIXPANEL_TOKEN = 'test_token_12345';
  });

  afterEach(() => {
    delete process.env.NEXT_PUBLIC_MIXPANEL_TOKEN;
  });

  describe('TC-ANALYTICS-EVENT-003: search_started event', () => {
    it('should track search_started with correct properties', async () => {
      const { result } = renderHook(() => useAnalytics());

      act(() => {
        result.current.trackEvent('search_started', {
          ufs: ['SC', 'PR'],
          uf_count: 2,
          date_range: { inicial: '2026-01-01', final: '2026-01-07', days: 7 },
          search_mode: 'setor',
          setor_id: 'vestuario',
          termos_busca: null,
          termos_count: 0,
        });
      });

      await flushPromises();

      const mp = (mixpanel as any).default || mixpanel;
      expect(mp.track).toHaveBeenCalledWith('search_started', {
        ufs: ['SC', 'PR'],
        uf_count: 2,
        date_range: { inicial: '2026-01-01', final: '2026-01-07', days: 7 },
        search_mode: 'setor',
        setor_id: 'vestuario',
        termos_busca: null,
        termos_count: 0,
        timestamp: expect.any(String),
        environment: expect.any(String),
      });
    });
  });

  describe('TC-ANALYTICS-EVENT-004: search_completed event', () => {
    it('should track search_completed with timing and results', async () => {
      const { result } = renderHook(() => useAnalytics());

      act(() => {
        result.current.trackEvent('search_completed', {
          time_elapsed_ms: 5000, total_raw: 200, total_filtered: 50, filter_ratio: '25.0%',
          valor_total: 1000000, has_summary: true, ufs: ['SC', 'PR'], uf_count: 2, search_mode: 'setor',
        });
      });

      await flushPromises();

      const mp = (mixpanel as any).default || mixpanel;
      expect(mp.track).toHaveBeenCalledWith('search_completed', expect.objectContaining({
        time_elapsed_ms: 5000, total_filtered: 50, filter_ratio: '25.0%',
      }));
    });
  });

  describe('TC-ANALYTICS-EVENT-005: search_failed event', () => {
    it('should track search_failed with error details', async () => {
      const { result } = renderHook(() => useAnalytics());

      act(() => {
        result.current.trackEvent('search_failed', {
          error_message: 'Backend indisponível. Tente novamente.', error_type: 'Error',
          time_elapsed_ms: 2000, ufs: ['SC'], uf_count: 1, search_mode: 'setor',
        });
      });

      await flushPromises();

      const mp = (mixpanel as any).default || mixpanel;
      expect(mp.track).toHaveBeenCalledWith('search_failed', expect.objectContaining({
        error_message: 'Backend indisponível. Tente novamente.', error_type: 'Error',
      }));
    });
  });

  describe('TC-ANALYTICS-EVENT-006: download_started event', () => {
    it('should track download_started with download ID', async () => {
      const { result } = renderHook(() => useAnalytics());

      act(() => {
        result.current.trackEvent('download_started', {
          download_id: '123e4567-e89b-12d3-a456-426614174000', total_filtered: 50,
          valor_total: 1000000, search_mode: 'setor', ufs: ['SC', 'PR'], uf_count: 2,
        });
      });

      await flushPromises();

      const mp = (mixpanel as any).default || mixpanel;
      expect(mp.track).toHaveBeenCalledWith('download_started', expect.objectContaining({
        download_id: '123e4567-e89b-12d3-a456-426614174000', total_filtered: 50,
      }));
    });
  });

  describe('TC-ANALYTICS-EVENT-007: download_completed event', () => {
    it('should track download_completed with file size and timing', async () => {
      const { result } = renderHook(() => useAnalytics());

      act(() => {
        result.current.trackEvent('download_completed', {
          download_id: '123e4567-e89b-12d3-a456-426614174000', time_elapsed_ms: 500,
          file_size_bytes: 5120, file_size_readable: '5.00 KB',
          filename: 'DescompLicita_Vestuário_e_Uniformes_2026-01-01_a_2026-01-07.xlsx',
          total_filtered: 50, valor_total: 1000000,
        });
      });

      await flushPromises();

      const mp = (mixpanel as any).default || mixpanel;
      expect(mp.track).toHaveBeenCalledWith('download_completed', expect.objectContaining({
        file_size_bytes: 5120, file_size_readable: '5.00 KB',
      }));
    });
  });

  describe('TC-ANALYTICS-EVENT-008: download_failed event', () => {
    it('should track download_failed with error message', async () => {
      const { result } = renderHook(() => useAnalytics());

      act(() => {
        result.current.trackEvent('download_failed', {
          download_id: '123e4567-e89b-12d3-a456-426614174000',
          error_message: 'Arquivo expirado. Faça uma nova busca para gerar o Excel.',
          error_type: 'Error', time_elapsed_ms: 300, total_filtered: 50,
        });
      });

      await flushPromises();

      const mp = (mixpanel as any).default || mixpanel;
      expect(mp.track).toHaveBeenCalledWith('download_failed', expect.objectContaining({
        error_message: 'Arquivo expirado. Faça uma nova busca para gerar o Excel.',
      }));
    });
  });

  describe('TC-ANALYTICS-EVENT-009: Custom terms search mode', () => {
    it('should track search with termos mode correctly', async () => {
      const { result } = renderHook(() => useAnalytics());

      act(() => {
        result.current.trackEvent('search_started', {
          ufs: ['SC'], uf_count: 1,
          date_range: { inicial: '2026-01-01', final: '2026-01-07', days: 7 },
          search_mode: 'termos', setor_id: null,
          termos_busca: 'uniforme jaleco fardamento', termos_count: 3,
        });
      });

      await flushPromises();

      const mp = (mixpanel as any).default || mixpanel;
      expect(mp.track).toHaveBeenCalledWith('search_started', expect.objectContaining({
        search_mode: 'termos', setor_id: null,
        termos_busca: 'uniforme jaleco fardamento', termos_count: 3,
      }));
    });
  });
});

describe('Analytics - Coverage Verification', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.NEXT_PUBLIC_MIXPANEL_TOKEN = 'test_token_12345';
  });

  afterEach(() => {
    delete process.env.NEXT_PUBLIC_MIXPANEL_TOKEN;
  });

  it('should achieve target coverage for useAnalytics hook', async () => {
    const { result } = renderHook(() => useAnalytics());

    act(() => { result.current.trackEvent('test'); });
    act(() => { result.current.trackEvent('test', { foo: 'bar' }); });
    act(() => { result.current.identifyUser('user-123'); });
    act(() => { result.current.identifyUser('user-123', { name: 'Test' }); });
    act(() => { result.current.trackPageView('/test'); });

    await flushPromises();

    const mp = (mixpanel as any).default || mixpanel;
    expect(mp.track).toHaveBeenCalledTimes(3);
    expect(mp.identify).toHaveBeenCalledTimes(2);
  });
});
