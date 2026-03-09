import { renderHook, act } from '@testing-library/react';
import { useSearchJob } from '@/app/hooks/useSearchJob';

// Mock fetch globally
global.fetch = jest.fn();

const mockTrackEvent = jest.fn();

const mockSearchParams = {
  ufs: ['SC'],
  dataInicial: '2024-01-01',
  dataFinal: '2024-01-07',
  searchMode: 'setor' as const,
  setorId: 'vestuario',
  termosArray: [],
};

const mockResultData = {
  resumo: {
    total_oportunidades: 10,
    valor_total: 50000,
    resumo_executivo: 'Test summary',
    destaques: [],
    distribuicao_uf: {},
    alerta_urgencia: null,
  },
  download_id: 'dl-1',
  total_raw: 20,
  total_filtrado: 10,
  total_atas: 0,
  total_licitacoes: 10,
  filter_stats: null,
  sources_used: [],
  source_stats: {},
  dedup_removed: 0,
  truncated_combos: 0,
};

function mockStatusResponse(status: string, phase?: string) {
  return {
    ok: true,
    json: async () => ({
      status,
      progress: {
        phase: phase || status,
        ufs_completed: status === 'completed' ? 1 : 0,
        ufs_total: 1,
        items_fetched: status === 'completed' ? 20 : 0,
        items_filtered: status === 'completed' ? 10 : 0,
      },
      elapsed_seconds: 5,
    }),
  };
}

function mockResultResponse() {
  return {
    ok: true,
    json: async () => mockResultData,
  };
}

function mockJobCreation(jobId = 'test-job-123') {
  return {
    ok: true,
    json: async () => ({ job_id: jobId }),
  };
}

async function startSearch(result: { current: ReturnType<typeof useSearchJob> }) {
  (global.fetch as jest.Mock).mockResolvedValueOnce(mockJobCreation());
  await act(async () => {
    result.current.buscar(mockSearchParams);
  });
}

describe('useSearchJob — Exponential Backoff Polling', () => {
  let setTimeoutSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    setTimeoutSpy = jest.spyOn(global, 'setTimeout');
  });

  afterEach(() => {
    jest.useRealTimers();
    setTimeoutSpy.mockRestore();
  });

  describe('Backoff timing', () => {
    it('should schedule the first poll at ~1000ms (initial interval)', async () => {
      const { result } = renderHook(() => useSearchJob(mockTrackEvent));
      await startSearch(result);

      // Find the setTimeout call for polling (not React internals)
      const pollTimeoutCalls = setTimeoutSpy.mock.calls.filter(
        ([, delay]) => delay === 1000
      );
      expect(pollTimeoutCalls.length).toBeGreaterThanOrEqual(1);
    });

    it('should grow delays by factor of 1.5', async () => {
      const { result } = renderHook(() => useSearchJob(mockTrackEvent));
      await startSearch(result);

      // First poll at 1000ms — returns "running"
      (global.fetch as jest.Mock).mockResolvedValueOnce(mockStatusResponse('running'));
      await act(async () => {
        jest.advanceTimersByTime(1000);
      });

      // After first poll, next should be scheduled at 1500ms
      const callsAt1500 = setTimeoutSpy.mock.calls.filter(
        ([, delay]) => delay === 1500
      );
      expect(callsAt1500.length).toBeGreaterThanOrEqual(1);

      // Second poll at 1500ms — returns "running"
      (global.fetch as jest.Mock).mockResolvedValueOnce(mockStatusResponse('running'));
      await act(async () => {
        jest.advanceTimersByTime(1500);
      });

      // After second poll, next should be scheduled at 2250ms
      const callsAt2250 = setTimeoutSpy.mock.calls.filter(
        ([, delay]) => delay === 2250
      );
      expect(callsAt2250.length).toBeGreaterThanOrEqual(1);
    });

    it('should cap delays at 15000ms', async () => {
      const { result } = renderHook(() => useSearchJob(mockTrackEvent));
      await startSearch(result);

      // Backoff sequence: 1000, 1500, 2250, 3375, 5062.5, 7593.75, 11390.625, 15000
      const delays = [1000, 1500, 2250, 3375, 5062.5, 7593.75, 11390.625, 15000, 15000];

      for (let i = 0; i < delays.length; i++) {
        (global.fetch as jest.Mock).mockResolvedValueOnce(mockStatusResponse('running'));
        await act(async () => {
          jest.advanceTimersByTime(delays[i]);
        });
      }

      // After 8+ polls, delays should be capped at 15000
      const callsAt15000 = setTimeoutSpy.mock.calls.filter(
        ([, delay]) => delay === 15000
      );
      expect(callsAt15000.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('Polling stops on terminal states', () => {
    it('should stop polling when status is "completed"', async () => {
      const { result } = renderHook(() => useSearchJob(mockTrackEvent));
      await startSearch(result);

      // First poll returns completed
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce(mockStatusResponse('completed'))
        .mockResolvedValueOnce(mockResultResponse());

      await act(async () => {
        jest.advanceTimersByTime(1000);
      });

      expect(result.current.loading).toBe(false);
      expect(result.current.result).not.toBeNull();
      expect(result.current.result?.resumo.total_oportunidades).toBe(10);
    });

    it('should stop polling when status is "failed"', async () => {
      const { result } = renderHook(() => useSearchJob(mockTrackEvent));
      await startSearch(result);

      // First poll returns failed, then fetchResult throws
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce(mockStatusResponse('failed'))
        .mockResolvedValueOnce({
          ok: false,
          json: async () => ({ message: 'Job failed' }),
        });

      await act(async () => {
        jest.advanceTimersByTime(1000);
      });

      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBeTruthy();
    });
  });

  describe('Poll count tracking', () => {
    it('should include poll_count in search_completed event', async () => {
      const { result } = renderHook(() => useSearchJob(mockTrackEvent));
      await startSearch(result);

      // First poll: running
      (global.fetch as jest.Mock).mockResolvedValueOnce(mockStatusResponse('running'));
      await act(async () => {
        jest.advanceTimersByTime(1000);
      });

      // Second poll: running
      (global.fetch as jest.Mock).mockResolvedValueOnce(mockStatusResponse('running'));
      await act(async () => {
        jest.advanceTimersByTime(1500);
      });

      // Third poll: completed
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce(mockStatusResponse('completed'))
        .mockResolvedValueOnce(mockResultResponse());

      await act(async () => {
        jest.advanceTimersByTime(2250);
      });

      expect(mockTrackEvent).toHaveBeenCalledWith(
        'search_completed',
        expect.objectContaining({
          poll_count: 3,
        })
      );
    });

    it('should include poll_count in search_failed event', async () => {
      const { result } = renderHook(() => useSearchJob(mockTrackEvent));
      await startSearch(result);

      // First poll: running
      (global.fetch as jest.Mock).mockResolvedValueOnce(mockStatusResponse('running'));
      await act(async () => {
        jest.advanceTimersByTime(1000);
      });

      // Second poll: completed but fetchResult fails
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce(mockStatusResponse('completed'))
        .mockResolvedValueOnce({
          ok: false,
          json: async () => ({ message: 'Result fetch error' }),
        });

      await act(async () => {
        jest.advanceTimersByTime(1500);
      });

      expect(mockTrackEvent).toHaveBeenCalledWith(
        'search_failed',
        expect.objectContaining({
          poll_count: 2,
        })
      );
    });
  });

  describe('Timeout behavior', () => {
    it('should error after 10 minute timeout', async () => {
      const { result } = renderHook(() => useSearchJob(mockTrackEvent));
      await startSearch(result);

      // Advance past the 10-minute deadline
      // We need to mock Date.now to simulate time passing beyond the deadline
      const originalDateNow = Date.now;
      const startTime = originalDateNow();

      // First poll is normal
      (global.fetch as jest.Mock).mockResolvedValueOnce(mockStatusResponse('running'));
      await act(async () => {
        jest.advanceTimersByTime(1000);
      });

      // Now make Date.now return a time past the 10 minute deadline
      Date.now = jest.fn(() => startTime + 11 * 60 * 1000);

      // Trigger the next poll
      (global.fetch as jest.Mock).mockResolvedValueOnce(mockStatusResponse('running'));
      await act(async () => {
        jest.advanceTimersByTime(1500);
      });

      expect(result.current.loading).toBe(false);
      expect(result.current.error).toContain('tempo limite');

      // Restore
      Date.now = originalDateNow;
    });
  });

  describe('Error resilience', () => {
    it('should continue polling with backoff on non-ok status response', async () => {
      const { result } = renderHook(() => useSearchJob(mockTrackEvent));
      await startSearch(result);

      // First poll: HTTP error (non-ok)
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ message: 'Server error' }),
      });

      await act(async () => {
        jest.advanceTimersByTime(1000);
      });

      // Should still be loading (not stopped)
      expect(result.current.loading).toBe(true);

      // Next poll should be scheduled at 1500ms (backoff applied)
      const callsAt1500 = setTimeoutSpy.mock.calls.filter(
        ([, delay]) => delay === 1500
      );
      expect(callsAt1500.length).toBeGreaterThanOrEqual(1);
    });

    it('should continue polling with backoff on network error', async () => {
      const { result } = renderHook(() => useSearchJob(mockTrackEvent));
      await startSearch(result);

      // First poll: network error (fetch throws)
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network failure'));

      await act(async () => {
        jest.advanceTimersByTime(1000);
      });

      // Should still be loading
      expect(result.current.loading).toBe(true);

      // Should schedule next poll with backoff
      const callsAt1500 = setTimeoutSpy.mock.calls.filter(
        ([, delay]) => delay === 1500
      );
      expect(callsAt1500.length).toBeGreaterThanOrEqual(1);
    });
  });
});
