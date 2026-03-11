import { renderHook, act } from "@testing-library/react";
import { useSaveDialog } from "../../app/hooks/useSaveDialog";

function makeForm(overrides: any = {}) {
  return {
    searchMode: "setor" as const,
    setores: [{ id: "vestuario", name: "Vestuário", description: "" }],
    setorId: "vestuario",
    termosArray: [] as string[],
    ufsSelecionadas: new Set(["SC", "PR"]),
    dataInicial: "2026-01-01",
    dataFinal: "2026-01-07",
    ...overrides,
  };
}

describe("useSaveDialog", () => {
  const trackEvent = jest.fn();

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("initializes with dialog hidden", () => {
    const { result } = renderHook(() =>
      useSaveDialog({
        form: makeForm() as any,
        saveNewSearch: jest.fn(),
        trackEvent,
        hasResult: false,
      }),
    );
    expect(result.current.showSaveDialog).toBe(false);
    expect(result.current.saveSearchName).toBe("");
    expect(result.current.saveError).toBeNull();
  });

  it("does nothing when handleSaveSearch called without result", () => {
    const { result } = renderHook(() =>
      useSaveDialog({
        form: makeForm() as any,
        saveNewSearch: jest.fn(),
        trackEvent,
        hasResult: false,
      }),
    );
    act(() => {
      result.current.handleSaveSearch();
    });
    expect(result.current.showSaveDialog).toBe(false);
  });

  it("opens dialog with setor name as default for setor mode", () => {
    const { result } = renderHook(() =>
      useSaveDialog({
        form: makeForm() as any,
        saveNewSearch: jest.fn(),
        trackEvent,
        hasResult: true,
      }),
    );
    act(() => {
      result.current.handleSaveSearch();
    });
    expect(result.current.showSaveDialog).toBe(true);
    expect(result.current.saveSearchName).toBe("Vestuário");
  });

  it("uses fallback name when setor not found", () => {
    const { result } = renderHook(() =>
      useSaveDialog({
        form: makeForm({ setorId: "unknown", setores: [] }) as any,
        saveNewSearch: jest.fn(),
        trackEvent,
        hasResult: true,
      }),
    );
    act(() => {
      result.current.handleSaveSearch();
    });
    expect(result.current.saveSearchName).toBe("Busca personalizada");
  });

  it("uses termos as default name for termos mode", () => {
    const { result } = renderHook(() =>
      useSaveDialog({
        form: makeForm({
          searchMode: "termos",
          termosArray: ["camisa", "polo"],
        }) as any,
        saveNewSearch: jest.fn(),
        trackEvent,
        hasResult: true,
      }),
    );
    act(() => {
      result.current.handleSaveSearch();
    });
    expect(result.current.saveSearchName).toBe('Busca: "camisa, polo"');
  });

  it("uses fallback name for termos mode with empty array", () => {
    const { result } = renderHook(() =>
      useSaveDialog({
        form: makeForm({
          searchMode: "termos",
          termosArray: [],
        }) as any,
        saveNewSearch: jest.fn(),
        trackEvent,
        hasResult: true,
      }),
    );
    act(() => {
      result.current.handleSaveSearch();
    });
    expect(result.current.saveSearchName).toBe("Busca personalizada");
  });

  it("confirmSaveSearch saves and closes dialog", async () => {
    const saveNewSearch = jest.fn().mockResolvedValue({ id: "1" });
    const { result } = renderHook(() =>
      useSaveDialog({
        form: makeForm() as any,
        saveNewSearch,
        trackEvent,
        hasResult: true,
      }),
    );

    act(() => {
      result.current.handleSaveSearch();
    });
    expect(result.current.showSaveDialog).toBe(true);

    await act(async () => {
      result.current.confirmSaveSearch();
      // Wait for async callback
      await new Promise(r => setTimeout(r, 10));
    });

    expect(saveNewSearch).toHaveBeenCalled();
    expect(trackEvent).toHaveBeenCalledWith("saved_search_created", expect.any(Object));
    expect(result.current.showSaveDialog).toBe(false);
    expect(result.current.saveSearchName).toBe("");
  });

  it("confirmSaveSearch uses fallback name when empty", async () => {
    const saveNewSearch = jest.fn().mockResolvedValue({ id: "1" });
    const { result } = renderHook(() =>
      useSaveDialog({
        form: makeForm() as any,
        saveNewSearch,
        trackEvent,
        hasResult: true,
      }),
    );

    act(() => {
      result.current.handleSaveSearch();
      result.current.setSaveSearchName("");
    });

    await act(async () => {
      result.current.confirmSaveSearch();
      await new Promise(r => setTimeout(r, 10));
    });

    expect(saveNewSearch).toHaveBeenCalledWith("Busca sem nome", expect.any(Object));
  });

  it("confirmSaveSearch handles save error", async () => {
    const saveNewSearch = jest.fn().mockRejectedValue(new Error("DB error"));
    const { result } = renderHook(() =>
      useSaveDialog({
        form: makeForm() as any,
        saveNewSearch,
        trackEvent,
        hasResult: true,
      }),
    );

    act(() => {
      result.current.handleSaveSearch();
    });

    await act(async () => {
      result.current.confirmSaveSearch();
      await new Promise(r => setTimeout(r, 10));
    });

    expect(result.current.saveError).toBe("DB error");
    expect(result.current.showSaveDialog).toBe(true);
  });

  it("confirmSaveSearch handles non-Error throw", async () => {
    const saveNewSearch = jest.fn().mockRejectedValue("string error");
    const { result } = renderHook(() =>
      useSaveDialog({
        form: makeForm() as any,
        saveNewSearch,
        trackEvent,
        hasResult: true,
      }),
    );

    act(() => {
      result.current.handleSaveSearch();
    });

    await act(async () => {
      result.current.confirmSaveSearch();
      await new Promise(r => setTimeout(r, 10));
    });

    expect(result.current.saveError).toBe("Erro ao salvar busca");
  });

  it("cancelSaveDialog resets state", () => {
    const { result } = renderHook(() =>
      useSaveDialog({
        form: makeForm() as any,
        saveNewSearch: jest.fn(),
        trackEvent,
        hasResult: true,
      }),
    );

    act(() => {
      result.current.handleSaveSearch();
    });
    expect(result.current.showSaveDialog).toBe(true);

    act(() => {
      result.current.cancelSaveDialog();
    });
    expect(result.current.showSaveDialog).toBe(false);
    expect(result.current.saveSearchName).toBe("");
    expect(result.current.saveError).toBeNull();
  });

  it("passes correct search params for termos mode", async () => {
    const saveNewSearch = jest.fn().mockResolvedValue({ id: "1" });
    const { result } = renderHook(() =>
      useSaveDialog({
        form: makeForm({
          searchMode: "termos",
          termosArray: ["uniforme"],
        }) as any,
        saveNewSearch,
        trackEvent,
        hasResult: true,
      }),
    );

    act(() => {
      result.current.handleSaveSearch();
    });

    await act(async () => {
      result.current.confirmSaveSearch();
      await new Promise(r => setTimeout(r, 10));
    });

    const callArgs = saveNewSearch.mock.calls[0][1];
    expect(callArgs.termosBusca).toBe("uniforme");
    expect(callArgs.setorId).toBeUndefined();
  });
});
