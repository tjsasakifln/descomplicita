import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { ItemsList } from "@/app/components/ItemsList";

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe("ItemsList", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders nothing when totalFiltered is 0", () => {
    const { container } = render(
      <ItemsList jobId="test-job" totalFiltered={0} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders heading when totalFiltered > 0", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [{ objeto: "Test item", uf: "SP" }],
        total_items: 1,
        total_pages: 1,
        page: 1,
        page_size: 20,
      }),
    });

    render(<ItemsList jobId="test-job" totalFiltered={5} />);
    expect(
      screen.getByText("Licitacoes Encontradas")
    ).toBeInTheDocument();
  });

  it("fetches and displays items", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [
          { objeto: "Uniformes escolares", orgao: "Prefeitura", uf: "SP" },
          { objeto: "Material escolar", orgao: "Governo", uf: "RJ" },
        ],
        total_items: 2,
        total_pages: 1,
        page: 1,
        page_size: 20,
      }),
    });

    render(<ItemsList jobId="job-123" totalFiltered={2} />);

    await waitFor(() => {
      expect(screen.getByText("Uniformes escolares")).toBeInTheDocument();
      expect(screen.getByText("Material escolar")).toBeInTheDocument();
    });
  });

  it("shows loading state", () => {
    // Never resolve the fetch to keep loading state
    mockFetch.mockReturnValueOnce(new Promise(() => {}));

    render(<ItemsList jobId="job-loading" totalFiltered={5} />);
    expect(screen.getByText("Carregando...")).toBeInTheDocument();
  });

  it("fetches correct URL with job_id", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [],
        total_items: 0,
        total_pages: 0,
        page: 1,
        page_size: 20,
      }),
    });

    render(<ItemsList jobId="my-job-id" totalFiltered={10} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/buscar/items?job_id=my-job-id&page=1&page_size=20",
        expect.objectContaining({ signal: expect.any(AbortSignal) })
      );
    });
  });

  it("displays item value when present", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [
          {
            objeto: "Test",
            valorTotalEstimado: 50000,
          },
        ],
        total_items: 1,
        total_pages: 1,
        page: 1,
        page_size: 20,
      }),
    });

    render(<ItemsList jobId="job-val" totalFiltered={1} />);

    await waitFor(() => {
      expect(screen.getByText(/50\.000/)).toBeInTheDocument();
    });
  });

  it("shows link button when item has link", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [
          {
            objeto: "Test item",
            link: "https://example.com/lic",
          },
        ],
        total_items: 1,
        total_pages: 1,
        page: 1,
        page_size: 20,
      }),
    });

    render(<ItemsList jobId="job-link" totalFiltered={1} />);

    await waitFor(() => {
      const link = screen.getByText("Ver");
      expect(link).toHaveAttribute("href", "https://example.com/lic");
      expect(link).toHaveAttribute("target", "_blank");
    });
  });

  it("handles fetch error gracefully", async () => {
    mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    render(<ItemsList jobId="job-err" totalFiltered={5} />);

    // Should not crash, heading should still be there
    expect(
      screen.getByText("Licitacoes Encontradas")
    ).toBeInTheDocument();

    // Should show error message with retry
    await waitFor(() => {
      expect(screen.getByText(/Erro de conexão/)).toBeInTheDocument();
      expect(screen.getByText("Tentar novamente")).toBeInTheDocument();
    });
  });

  it("shows fallback text for items without objeto", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [{ uf: "MG" }],
        total_items: 1,
        total_pages: 1,
        page: 1,
        page_size: 20,
      }),
    });

    render(<ItemsList jobId="job-noobj" totalFiltered={1} />);

    await waitFor(() => {
      expect(screen.getByText("Sem descricao")).toBeInTheDocument();
    });
  });

  it("displays tipo badge as Licitação for licitacao type", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [{ objeto: "Uniformes", tipo: "licitacao" }],
        total_items: 1,
        total_pages: 1,
        page: 1,
        page_size: 20,
      }),
    });

    render(<ItemsList jobId="job-tipo" totalFiltered={1} />);

    await waitFor(() => {
      expect(screen.getByText("Licitação")).toBeInTheDocument();
    });
  });

  it("displays tipo badge as Ata for ata_registro_preco type", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [{ objeto: "Uniformes", tipo: "ata_registro_preco" }],
        total_items: 1,
        total_pages: 1,
        page: 1,
        page_size: 20,
      }),
    });

    render(<ItemsList jobId="job-ata" totalFiltered={1} />);

    await waitFor(() => {
      expect(screen.getByText("Ata")).toBeInTheDocument();
    });
  });

  it("does not render tipo badge when tipo is missing", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [{ objeto: "Test item" }],
        total_items: 1,
        total_pages: 1,
        page: 1,
        page_size: 20,
      }),
    });

    render(<ItemsList jobId="job-notipo" totalFiltered={1} />);

    await waitFor(() => {
      expect(screen.getByText("Test item")).toBeInTheDocument();
    });
    expect(screen.queryByText("Licitação")).not.toBeInTheDocument();
    expect(screen.queryByText("Ata")).not.toBeInTheDocument();
  });
});
