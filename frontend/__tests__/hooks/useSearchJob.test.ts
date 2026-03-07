import { renderHook, act } from '@testing-library/react';
import { useSearchJob } from '@/app/hooks/useSearchJob';

// Mock fetch
global.fetch = jest.fn();

const mockTrackEvent = jest.fn();

const mockSearchParams = {
  ufs: ['SC', 'PR', 'RS'],
  dataInicial: '2024-01-01',
  dataFinal: '2024-01-07',
  searchMode: 'setor' as const,
  setorId: 'vestuario',
  termosArray: [],
};

describe('useSearchJob', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Initial state', () => {
    it('should have idle state', () => {
      const { result } = renderHook(() => useSearchJob(mockTrackEvent));
      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.result).toBeNull();
      expect(result.current.searchPhase).toBe('idle');
    });
  });

  describe('buscar', () => {
    it('should set loading state when called', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: 'test-123' }),
      });

      const { result } = renderHook(() => useSearchJob(mockTrackEvent));

      await act(async () => {
        result.current.buscar(mockSearchParams);
      });

      expect(result.current.loading).toBe(true);
      expect(result.current.searchPhase).toBe('queued');
    });

    it('should track search_started event', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: 'test-123' }),
      });

      const { result } = renderHook(() => useSearchJob(mockTrackEvent));

      await act(async () => {
        result.current.buscar(mockSearchParams);
      });

      expect(mockTrackEvent).toHaveBeenCalledWith('search_started', expect.objectContaining({
        ufs: ['SC', 'PR', 'RS'],
        uf_count: 3,
        search_mode: 'setor',
      }));
    });

    it('should handle API error', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        json: async () => ({ message: 'Server error' }),
      });

      const { result } = renderHook(() => useSearchJob(mockTrackEvent));

      await act(async () => {
        await result.current.buscar(mockSearchParams);
      });

      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBe('Server error');
    });

    it('should handle missing job_id', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      const { result } = renderHook(() => useSearchJob(mockTrackEvent));

      await act(async () => {
        await result.current.buscar(mockSearchParams);
      });

      expect(result.current.error).toContain('job_id');
    });
  });

  describe('handleCancel', () => {
    it('should reset loading state', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: 'test-123' }),
      });

      const { result } = renderHook(() => useSearchJob(mockTrackEvent));

      await act(async () => {
        result.current.buscar(mockSearchParams);
      });

      expect(result.current.loading).toBe(true);

      act(() => result.current.handleCancel());

      expect(result.current.loading).toBe(false);
      expect(result.current.searchPhase).toBe('idle');
    });

    it('should track search_cancelled event', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: 'test-123' }),
      });

      const { result } = renderHook(() => useSearchJob(mockTrackEvent));

      await act(async () => {
        result.current.buscar(mockSearchParams);
      });

      mockTrackEvent.mockClear();
      act(() => result.current.handleCancel());

      expect(mockTrackEvent).toHaveBeenCalledWith('search_cancelled', expect.any(Object));
    });
  });

  describe('clearResult', () => {
    it('should clear result and rawCount', () => {
      const { result } = renderHook(() => useSearchJob(mockTrackEvent));
      act(() => result.current.clearResult());
      expect(result.current.result).toBeNull();
      expect(result.current.rawCount).toBe(0);
    });
  });

  describe('Polling lifecycle', () => {
    it('should start polling after successful job creation', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: 'poll-test' }),
      });

      const { result } = renderHook(() => useSearchJob(mockTrackEvent));

      await act(async () => {
        result.current.buscar(mockSearchParams);
      });

      expect(result.current.loading).toBe(true);

      // Mock the status poll response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'completed',
          progress: { phase: 'completed', ufs_completed: 3, ufs_total: 3, items_fetched: 100, items_filtered: 50 },
          elapsed_seconds: 5,
        }),
      }).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          resumo: { total_oportunidades: 50, valor_total: 100000, resumo_executivo: 'Test', destaques: [], distribuicao_uf: {}, alerta_urgencia: null },
          download_id: 'dl-1',
          total_raw: 100,
          total_filtrado: 50,
          total_atas: 0,
          total_licitacoes: 50,
          filter_stats: null,
          sources_used: [],
          source_stats: {},
          dedup_removed: 0,
          truncated_combos: 0,
        }),
      });

      await act(async () => {
        jest.advanceTimersByTime(2100);
      });

      expect(result.current.loading).toBe(false);
      expect(result.current.result).not.toBeNull();
      expect(result.current.result?.resumo.total_oportunidades).toBe(50);
    });
  });
});
