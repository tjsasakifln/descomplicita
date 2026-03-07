import { renderHook, act } from '@testing-library/react';
import { useSearchForm } from '@/app/hooks/useSearchForm';

// Mock fetch
global.fetch = jest.fn();

describe('useSearchForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockRejectedValue(new Error('not found'));
  });

  describe('Initial state', () => {
    it('should have default UFs (SC, PR, RS)', () => {
      const { result } = renderHook(() => useSearchForm());
      expect(result.current.ufsSelecionadas.has('SC')).toBe(true);
      expect(result.current.ufsSelecionadas.has('PR')).toBe(true);
      expect(result.current.ufsSelecionadas.has('RS')).toBe(true);
      expect(result.current.ufsSelecionadas.size).toBe(3);
    });

    it('should have default search mode as setor', () => {
      const { result } = renderHook(() => useSearchForm());
      expect(result.current.searchMode).toBe('setor');
    });

    it('should have default setor as vestuario', () => {
      const { result } = renderHook(() => useSearchForm());
      expect(result.current.setorId).toBe('vestuario');
    });

    it('should have empty termos array', () => {
      const { result } = renderHook(() => useSearchForm());
      expect(result.current.termosArray).toEqual([]);
    });

    it('should have valid default dates (7 day range)', () => {
      const { result } = renderHook(() => useSearchForm());
      expect(result.current.dataInicial).toBeTruthy();
      expect(result.current.dataFinal).toBeTruthy();
      expect(result.current.dataFinal >= result.current.dataInicial).toBe(true);
    });
  });

  describe('Validation', () => {
    it('should be valid with default state', () => {
      const { result } = renderHook(() => useSearchForm());
      expect(result.current.canSearch).toBe(true);
      expect(Object.keys(result.current.validationErrors)).toHaveLength(0);
    });

    it('should be invalid when no UFs selected', () => {
      const { result } = renderHook(() => useSearchForm());
      act(() => result.current.limparSelecao());
      expect(result.current.validationErrors.ufs).toBe('Selecione pelo menos um estado');
      expect(result.current.canSearch).toBe(false);
    });

    it('should show date range error when final < initial', () => {
      const { result } = renderHook(() => useSearchForm());
      act(() => {
        result.current.setDataInicial('2024-02-01');
        result.current.setDataFinal('2024-01-15');
      });
      expect(result.current.validationErrors.date_range).toBeTruthy();
    });

    it('should require terms when in termos mode', () => {
      const { result } = renderHook(() => useSearchForm());
      act(() => result.current.setSearchMode('termos'));
      expect(result.current.canSearch).toBe(false);
    });
  });

  describe('UF toggling', () => {
    it('should toggle a UF on and off', () => {
      const { result } = renderHook(() => useSearchForm());
      act(() => result.current.toggleUf('SP'));
      expect(result.current.ufsSelecionadas.has('SP')).toBe(true);
      act(() => result.current.toggleUf('SP'));
      expect(result.current.ufsSelecionadas.has('SP')).toBe(false);
    });

    it('should select all UFs', () => {
      const { result } = renderHook(() => useSearchForm());
      act(() => result.current.selecionarTodos());
      expect(result.current.ufsSelecionadas.size).toBe(27);
    });

    it('should clear all UFs', () => {
      const { result } = renderHook(() => useSearchForm());
      act(() => result.current.limparSelecao());
      expect(result.current.ufsSelecionadas.size).toBe(0);
    });

    it('should toggle region', () => {
      const { result } = renderHook(() => useSearchForm());
      act(() => result.current.limparSelecao());
      act(() => result.current.toggleRegion(['SP', 'RJ', 'MG', 'ES']));
      expect(result.current.ufsSelecionadas.has('SP')).toBe(true);
      expect(result.current.ufsSelecionadas.has('RJ')).toBe(true);
      expect(result.current.ufsSelecionadas.size).toBe(4);
    });
  });

  describe('onFormChange callback', () => {
    it('should call onFormChange when toggling UF', () => {
      const onChange = jest.fn();
      const { result } = renderHook(() => useSearchForm(onChange));
      act(() => result.current.toggleUf('SP'));
      expect(onChange).toHaveBeenCalled();
    });

    it('should call onFormChange when changing dates', () => {
      const onChange = jest.fn();
      const { result } = renderHook(() => useSearchForm(onChange));
      act(() => result.current.setDataInicial('2024-01-01'));
      expect(onChange).toHaveBeenCalled();
    });
  });

  describe('Derived values', () => {
    it('should have correct searchLabel for setor mode', () => {
      const { result } = renderHook(() => useSearchForm());
      // Before setores load, falls back to "Licitações"
      expect(result.current.searchLabel).toBe('Licitações');
    });

    it('should have correct searchLabel for termos mode', () => {
      const { result } = renderHook(() => useSearchForm());
      act(() => {
        result.current.setSearchMode('termos');
        result.current.setTermosArray(['uniforme', 'escolar']);
      });
      expect(result.current.searchLabel).toBe('"uniforme", "escolar"');
    });
  });

  describe('loadSearchParams', () => {
    it('should load saved search params', () => {
      const { result } = renderHook(() => useSearchForm());
      act(() => {
        result.current.loadSearchParams({
          ufs: ['SP', 'RJ'],
          dataInicial: '2024-01-01',
          dataFinal: '2024-01-31',
          searchMode: 'setor',
          setorId: 'alimentos',
        });
      });
      expect(result.current.ufsSelecionadas.size).toBe(2);
      expect(result.current.ufsSelecionadas.has('SP')).toBe(true);
      expect(result.current.dataInicial).toBe('2024-01-01');
      expect(result.current.setorId).toBe('alimentos');
    });
  });
});
