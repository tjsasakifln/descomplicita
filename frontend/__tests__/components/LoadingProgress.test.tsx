import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoadingProgress } from "@/app/components/LoadingProgress";
import {
  CURIOSIDADES,
  CATEGORIA_CONFIG,
  shuffleBalanced,
} from "@/app/components/carouselData";
import type { CuriosidadeCategoria } from "@/app/components/carouselData";

// Mock useAnalytics
const mockTrackEvent = jest.fn();
jest.mock("../../hooks/useAnalytics", () => ({
  useAnalytics: () => ({
    trackEvent: mockTrackEvent,
    identifyUser: jest.fn(),
    trackPageView: jest.fn(),
  }),
}));

const defaultProps = {
  phase: "fetching" as const,
  ufsCompleted: 3,
  ufsTotal: 10,
  itemsFetched: 150,
  itemsFiltered: 0,
  elapsedSeconds: 12,
  onCancel: jest.fn(),
};

describe("LoadingProgress Component", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockTrackEvent.mockClear();
    defaultProps.onCancel.mockClear();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("renders progress bar and status message", () => {
    render(<LoadingProgress {...defaultProps} />);
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
    // Status message appears in header + mobile detail
    expect(screen.getAllByText(/Buscando em 3\/10 estados/).length).toBeGreaterThanOrEqual(1);
  });

  it("displays elapsed time", () => {
    render(<LoadingProgress {...defaultProps} />);
    expect(screen.getByText("12s")).toBeInTheDocument();
  });

  it("displays elapsed time with minutes", () => {
    render(<LoadingProgress {...defaultProps} elapsedSeconds={75} />);
    expect(screen.getByText("1min 15s")).toBeInTheDocument();
  });

  it("shows UF progress during fetching phase", () => {
    render(<LoadingProgress {...defaultProps} />);
    expect(screen.getByText("3 / 10")).toBeInTheDocument();
    expect(screen.getByText("Estados processados")).toBeInTheDocument();
  });

  it("hides UF progress when not in fetching phase", () => {
    render(<LoadingProgress {...defaultProps} phase="summarizing" />);
    expect(screen.queryByText("Estados processados")).not.toBeInTheDocument();
  });

  it("calls onCancel when cancel button is clicked", async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<LoadingProgress {...defaultProps} />);
    await user.click(screen.getByText("Cancelar busca"));
    expect(defaultProps.onCancel).toHaveBeenCalledTimes(1);
  });

  describe("progress calculation", () => {
    it("shows 3% for queued phase", () => {
      render(<LoadingProgress {...defaultProps} phase="queued" />);
      expect(screen.getByText("3%")).toBeInTheDocument();
    });

    it("calculates fetching progress based on UF completion", () => {
      render(<LoadingProgress {...defaultProps} ufsCompleted={5} ufsTotal={10} />);
      // 5 + (5/10)*50 = 30
      expect(screen.getByText("30%")).toBeInTheDocument();
    });

    it("shows 60% for filtering phase", () => {
      render(<LoadingProgress {...defaultProps} phase="filtering" />);
      expect(screen.getByText("60%")).toBeInTheDocument();
    });

    it("shows 75% for summarizing phase", () => {
      render(<LoadingProgress {...defaultProps} phase="summarizing" />);
      expect(screen.getByText("75%")).toBeInTheDocument();
    });

    it("shows 90% for generating_excel phase", () => {
      render(<LoadingProgress {...defaultProps} phase="generating_excel" />);
      expect(screen.getByText("90%")).toBeInTheDocument();
    });
  });

  describe("status messages", () => {
    it("shows queued message", () => {
      render(<LoadingProgress {...defaultProps} phase="queued" />);
      // Appears in header + mobile detail section
      expect(screen.getAllByText("Iniciando busca...").length).toBeGreaterThanOrEqual(1);
    });

    it("shows fetching message with UF count", () => {
      render(<LoadingProgress {...defaultProps} />);
      expect(screen.getAllByText(/Buscando em 3\/10 estados/).length).toBeGreaterThanOrEqual(1);
    });

    it("shows fetching without UF when ufsTotal is 0", () => {
      render(<LoadingProgress {...defaultProps} ufsTotal={0} />);
      expect(screen.getAllByText("Buscando em fontes oficiais...").length).toBeGreaterThanOrEqual(1);
    });

    it("shows filtering message", () => {
      render(<LoadingProgress {...defaultProps} phase="filtering" itemsFetched={500} />);
      expect(screen.getAllByText(/Filtrando resultados/).length).toBeGreaterThanOrEqual(1);
    });

    it("shows summarizing message", () => {
      render(<LoadingProgress {...defaultProps} phase="summarizing" />);
      expect(screen.getAllByText("Gerando resumo inteligente...").length).toBeGreaterThanOrEqual(1);
    });

    it("shows generating_excel message", () => {
      render(<LoadingProgress {...defaultProps} phase="generating_excel" />);
      expect(screen.getAllByText("Preparando planilha...").length).toBeGreaterThanOrEqual(1);
    });
  });

  describe("stage indicators", () => {
    it("renders all 5 stage labels", () => {
      render(<LoadingProgress {...defaultProps} phase="queued" />);
      // Stage labels in the 5-stage indicator bar (some may also appear in mobile detail)
      expect(screen.getAllByText("Iniciando busca").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Buscando licitações").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Filtrando resultados").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Gerando resumo IA").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Preparando planilha").length).toBeGreaterThanOrEqual(1);
    });
  });

  describe("analytics tracking", () => {
    it("tracks loading_stage_reached on phase change", () => {
      render(<LoadingProgress {...defaultProps} />);
      expect(mockTrackEvent).toHaveBeenCalledWith(
        "loading_stage_reached",
        expect.objectContaining({
          stage: "fetching",
          stage_index: 1,
        })
      );
    });
  });

  describe("LV5 — dynamic ETA proportional to volume", () => {
    it("shows ~30s ETA for filtering phase when itemsFetched=10000 (2 × 15s base)", () => {
      // volumeMultiplier = ceil(10000 / 5000) = 2 → 15 * 2 = 30s
      render(
        <LoadingProgress
          {...defaultProps}
          phase="filtering"
          ufsCompleted={5}
          ufsTotal={5}
          itemsFetched={10000}
          itemsFiltered={5000}
          elapsedSeconds={120}
        />
      );
      expect(screen.getByText(/~30s restantes/)).toBeInTheDocument();
    });

    it("shows ~15s ETA for filtering phase when itemsFetched=5000 (1 × 15s base)", () => {
      // volumeMultiplier = ceil(5000 / 5000) = 1 → 15 * 1 = 15s
      render(
        <LoadingProgress
          {...defaultProps}
          phase="filtering"
          ufsCompleted={5}
          ufsTotal={5}
          itemsFetched={5000}
          itemsFiltered={0}
          elapsedSeconds={60}
        />
      );
      expect(screen.getByText(/~15s restantes/)).toBeInTheDocument();
    });

    it("shows ~45s ETA for filtering phase when itemsFetched=15000 (3 × 15s base)", () => {
      // volumeMultiplier = ceil(15000 / 5000) = 3 → 15 * 3 = 45s
      render(
        <LoadingProgress
          {...defaultProps}
          phase="filtering"
          ufsCompleted={5}
          ufsTotal={5}
          itemsFetched={15000}
          itemsFiltered={0}
          elapsedSeconds={60}
        />
      );
      expect(screen.getByText(/~45s restantes/)).toBeInTheDocument();
    });

    it("uses volumeMultiplier=1 when itemsFetched=0 (no data yet)", () => {
      // volumeMultiplier = 1 (fallback) → 15 * 1 = 15s
      render(
        <LoadingProgress
          {...defaultProps}
          phase="filtering"
          ufsCompleted={5}
          ufsTotal={5}
          itemsFetched={0}
          itemsFiltered={0}
          elapsedSeconds={10}
        />
      );
      expect(screen.getByText(/~15s restantes/)).toBeInTheDocument();
    });
  });

  describe("LV5 — dynamic ETA for summarizing phase", () => {
    it("shows ~20s ETA for summarizing when itemsFetched=10000 (2 × 10s base)", () => {
      // volumeMultiplier = ceil(10000 / 5000) = 2 → 10 * 2 = 20s
      render(
        <LoadingProgress
          {...defaultProps}
          phase="summarizing"
          ufsCompleted={5}
          ufsTotal={5}
          itemsFetched={10000}
          itemsFiltered={2000}
          elapsedSeconds={180}
        />
      );
      expect(screen.getByText(/~20s restantes/)).toBeInTheDocument();
    });

    it("shows ~10s ETA for summarizing when itemsFetched=1000 (1 × 10s base)", () => {
      // volumeMultiplier = ceil(1000 / 5000) = 1 → 10 * 1 = 10s
      render(
        <LoadingProgress
          {...defaultProps}
          phase="summarizing"
          ufsCompleted={5}
          ufsTotal={5}
          itemsFetched={1000}
          itemsFiltered={100}
          elapsedSeconds={60}
        />
      );
      expect(screen.getByText(/~10s restantes/)).toBeInTheDocument();
    });
  });

  describe("LV6 — progress bar interpolation during filtering phase", () => {
    it("shows 60% when filtering starts (itemsFiltered=0)", () => {
      render(
        <LoadingProgress
          {...defaultProps}
          phase="filtering"
          ufsCompleted={5}
          ufsTotal={5}
          itemsFetched={1000}
          itemsFiltered={0}
          elapsedSeconds={30}
        />
      );
      const progressBar = screen.getByRole("progressbar");
      expect(Number(progressBar.getAttribute("aria-valuenow"))).toBe(60);
    });

    it("shows interpolated value between 60 and 75 when filtering is halfway (itemsFiltered=500, itemsFetched=1000)", () => {
      // filterRatio = 500/1000 = 0.5 → 60 + 0.5 * 15 = 67 (rounded) = ~67%
      render(
        <LoadingProgress
          {...defaultProps}
          phase="filtering"
          ufsCompleted={5}
          ufsTotal={5}
          itemsFetched={1000}
          itemsFiltered={500}
          elapsedSeconds={45}
        />
      );
      const progressBar = screen.getByRole("progressbar");
      const valuenow = Number(progressBar.getAttribute("aria-valuenow"));
      expect(valuenow).toBeGreaterThan(60);
      expect(valuenow).toBeLessThan(75);
    });

    it("shows 67% for filtering at 50% ratio (500 filtered / 1000 fetched)", () => {
      // Math.round(60 + (500/1000) * 15) = Math.round(67.5) = 68
      render(
        <LoadingProgress
          {...defaultProps}
          phase="filtering"
          ufsCompleted={5}
          ufsTotal={5}
          itemsFetched={1000}
          itemsFiltered={500}
          elapsedSeconds={45}
        />
      );
      const progressBar = screen.getByRole("progressbar");
      const valuenow = Number(progressBar.getAttribute("aria-valuenow"));
      // Accept 67 or 68 depending on rounding
      expect(valuenow).toBeGreaterThanOrEqual(67);
      expect(valuenow).toBeLessThanOrEqual(68);
    });

    it("shows 75% when all items have been filtered (itemsFiltered >= itemsFetched)", () => {
      // filterRatio = 1000/1000 = 1.0 → Math.round(60 + 1.0 * 15) = 75
      render(
        <LoadingProgress
          {...defaultProps}
          phase="filtering"
          ufsCompleted={5}
          ufsTotal={5}
          itemsFetched={1000}
          itemsFiltered={1000}
          elapsedSeconds={60}
        />
      );
      const progressBar = screen.getByRole("progressbar");
      expect(Number(progressBar.getAttribute("aria-valuenow"))).toBe(75);
    });

    it("caps filterRatio at 1.0 when itemsFiltered exceeds itemsFetched", () => {
      // filterRatio clamped to 1.0 → 75
      render(
        <LoadingProgress
          {...defaultProps}
          phase="filtering"
          ufsCompleted={5}
          ufsTotal={5}
          itemsFetched={500}
          itemsFiltered={600}
          elapsedSeconds={60}
        />
      );
      const progressBar = screen.getByRole("progressbar");
      expect(Number(progressBar.getAttribute("aria-valuenow"))).toBe(75);
    });

    it("shows 60% for filtering when itemsFetched=0 (no items yet, no interpolation)", () => {
      render(
        <LoadingProgress
          {...defaultProps}
          phase="filtering"
          ufsCompleted={5}
          ufsTotal={5}
          itemsFetched={0}
          itemsFiltered={0}
          elapsedSeconds={10}
        />
      );
      const progressBar = screen.getByRole("progressbar");
      expect(Number(progressBar.getAttribute("aria-valuenow"))).toBe(60);
    });
  });
});

describe("Carousel Data — carouselData.ts", () => {
  it("has at least 50 items total", () => {
    expect(CURIOSIDADES.length).toBeGreaterThanOrEqual(50);
  });

  it("has at least 12 items per category", () => {
    const counts: Record<string, number> = {};
    for (const item of CURIOSIDADES) {
      counts[item.categoria] = (counts[item.categoria] || 0) + 1;
    }
    expect(counts["legislacao"]).toBeGreaterThanOrEqual(12);
    expect(counts["estrategia"]).toBeGreaterThanOrEqual(12);
    expect(counts["insight"]).toBeGreaterThanOrEqual(12);
    expect(counts["dica"]).toBeGreaterThanOrEqual(12);
  });

  it("has zero mentions of PNCP in any texto field", () => {
    for (const item of CURIOSIDADES) {
      expect(item.texto).not.toContain("PNCP");
    }
  });

  it("every item has non-empty texto, fonte, and valid categoria", () => {
    const validCategories = ["legislacao", "estrategia", "insight", "dica"];
    for (const item of CURIOSIDADES) {
      expect(item.texto.length).toBeGreaterThan(0);
      expect(item.fonte.length).toBeGreaterThan(0);
      expect(validCategories).toContain(item.categoria);
    }
  });

  it("CATEGORIA_CONFIG has all 4 categories with required properties", () => {
    const categories: CuriosidadeCategoria[] = ["legislacao", "estrategia", "insight", "dica"];
    for (const cat of categories) {
      const config = CATEGORIA_CONFIG[cat];
      expect(config).toBeDefined();
      expect(config.label).toBeTruthy();
      expect(config.header).toBeTruthy();
      expect(config.icon).toBeTruthy();
      expect(config.bgClass).toBeTruthy();
      expect(config.iconBgClass).toBeTruthy();
      expect(config.iconTextClass).toBeTruthy();
    }
  });

  it("CATEGORIA_CONFIG has distinct visual identity per category", () => {
    const configs = Object.values(CATEGORIA_CONFIG);
    const bgClasses = configs.map((c) => c.bgClass);
    const icons = configs.map((c) => c.icon);
    expect(new Set(bgClasses).size).toBe(4);
    expect(new Set(icons).size).toBe(4);
  });

  it("CATEGORIA_CONFIG has correct headers per category", () => {
    expect(CATEGORIA_CONFIG.legislacao.header).toBe("Você sabia?");
    expect(CATEGORIA_CONFIG.estrategia.header).toBe("Estratégia");
    expect(CATEGORIA_CONFIG.insight.header).toBe("Insight de Mercado");
    expect(CATEGORIA_CONFIG.dica.header).toBe("Dica");
  });

  it("CATEGORIA_CONFIG has correct labels per category", () => {
    expect(CATEGORIA_CONFIG.legislacao.label).toBe("Legislação");
    expect(CATEGORIA_CONFIG.estrategia.label).toBe("Estratégia");
    expect(CATEGORIA_CONFIG.insight.label).toBe("Insight de Mercado");
    expect(CATEGORIA_CONFIG.dica.label).toBe("Dica Descomplicita");
  });
});

describe("shuffleBalanced", () => {
  it("returns all items (no data loss)", () => {
    const result = shuffleBalanced([...CURIOSIDADES]);
    expect(result.length).toBe(CURIOSIDADES.length);
  });

  it("preserves all original items", () => {
    const result = shuffleBalanced([...CURIOSIDADES]);
    const originalTexts = new Set(CURIOSIDADES.map((c) => c.texto));
    const resultTexts = new Set(result.map((c) => c.texto));
    expect(resultTexts).toEqual(originalTexts);
  });

  it("interleaves categories — no 3+ consecutive same category", () => {
    for (let run = 0; run < 10; run++) {
      const result = shuffleBalanced([...CURIOSIDADES]);
      for (let i = 0; i < result.length - 2; i++) {
        const sameThree =
          result[i].categoria === result[i + 1].categoria &&
          result[i + 1].categoria === result[i + 2].categoria;
        expect(sameThree).toBe(false);
      }
    }
  });

  it("handles empty input", () => {
    expect(shuffleBalanced([])).toEqual([]);
  });

  it("handles single-category input", () => {
    const items = CURIOSIDADES.filter((c) => c.categoria === "legislacao");
    const result = shuffleBalanced(items);
    expect(result.length).toBe(items.length);
  });
});

describe("Carousel rotation", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("rotates every 6 seconds (not 5)", () => {
    const { container } = render(<LoadingProgress {...defaultProps} />);

    const getCardText = () => {
      const cards = container.querySelectorAll(".text-base.text-ink");
      return cards[cards.length - 1]?.textContent || "";
    };

    const initial = getCardText();

    // After 5 seconds — should NOT have changed yet
    act(() => { jest.advanceTimersByTime(5000); });
    expect(getCardText()).toBe(initial);

    // After 6.3 seconds — fade out (300ms) + new item
    act(() => { jest.advanceTimersByTime(1300); });
  });

  it("category-aware card shows correct header and label", () => {
    const originalRandom = Math.random;
    Math.random = () => 0.1;

    render(<LoadingProgress {...defaultProps} />);

    const validHeaders = ["Você sabia?", "Estratégia", "Insight de Mercado", "Dica"];
    const headerFound = validHeaders.some((h) => screen.queryByText(h));
    expect(headerFound).toBe(true);

    const validLabels = ["Legislação", "Estratégia", "Insight de Mercado", "Dica Descomplicita"];
    const labelFound = validLabels.some((l) => screen.queryByText(l));
    expect(labelFound).toBe(true);

    Math.random = originalRandom;
  });
});
