/**
 * ItemsList — pagination, error & AbortController tests
 *
 * Story requirements covered:
 *   CP2 – Pagination shows retry button after error
 *   UX1 – Error state is displayed when fetch fails
 *   UX2 – Retry button re-fetches the page
 *   CP3 – AbortController cancels stale requests on page change
 *   UX6 – Verify AbortController cancels previous fetch
 */

import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import "@testing-library/jest-dom";
import { ItemsList } from "../../app/components/ItemsList";

// ---------------------------------------------------------------------------
// Pagination mock — exposes simple page-change buttons for testing
// ---------------------------------------------------------------------------
jest.mock("../../app/components/Pagination", () => ({
  Pagination: ({
    onPageChange,
  }: {
    currentPage: number;
    totalPages: number;
    totalItems: number;
    pageSize: number;
    onPageChange: (p: number) => void;
  }) => (
    <div data-testid="pagination">
      <button data-testid="page-2-btn" onClick={() => onPageChange(2)}>
        Page 2
      </button>
      <button data-testid="page-3-btn" onClick={() => onPageChange(3)}>
        Page 3
      </button>
    </div>
  ),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const emptySuccessResponse = () => ({
  ok: true,
  json: () =>
    Promise.resolve({ items: [], total_pages: 0, total_items: 0 }),
});

const itemsSuccessResponse = (
  items: Record<string, unknown>[] = [{ objeto: "Item 1" }]
) => ({
  ok: true,
  json: () =>
    Promise.resolve({ items, total_pages: 3, total_items: 50 }),
});

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  (global.fetch as jest.Mock) = jest.fn();
});

afterEach(() => {
  jest.useRealTimers();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ItemsList – error states, retry & AbortController", () => {
  // ─── Returns null ────────────────────────────────────────────────────────

  describe("renders nothing when totalFiltered is 0", () => {
    it("returns null and makes no fetch call", () => {
      const { container } = render(
        <ItemsList jobId="job-123" totalFiltered={0} />
      );
      expect(container.firstChild).toBeNull();
      expect(global.fetch).not.toHaveBeenCalled();
    });
  });

  // ─── UX1 – Error state on fetch failure ──────────────────────────────────

  describe("UX1 – Error state is displayed when fetch fails", () => {
    it("shows connection error for a network TypeError", async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(
        new TypeError("Failed to fetch")
      );

      render(<ItemsList jobId="job-123" totalFiltered={10} />);

      await waitFor(() => {
        expect(
          screen.getByText(/Erro de conexão/i)
        ).toBeInTheDocument();
      });
    });

    it("shows page-load error when server returns a non-ok status", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      render(<ItemsList jobId="job-123" totalFiltered={10} />);

      await waitFor(() => {
        expect(
          screen.getByText(/Erro ao carregar página/i)
        ).toBeInTheDocument();
      });
    });
  });

  // ─── Error differentiation – JSON parse error ────────────────────────────

  describe("Error differentiation – JSON parse error", () => {
    it("shows processing error when response JSON is malformed", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new SyntaxError("Unexpected token")),
      });

      render(<ItemsList jobId="job-123" totalFiltered={10} />);

      await waitFor(() => {
        expect(
          screen.getByText(/Erro ao processar dados/i)
        ).toBeInTheDocument();
      });
    });
  });

  // ─── CP2 – Retry button visible after error ───────────────────────────────

  describe("CP2 – Retry button shown after error", () => {
    it("shows 'Tentar novamente' after a server error", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      render(<ItemsList jobId="job-123" totalFiltered={10} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Tentar novamente/i })
        ).toBeInTheDocument();
      });
    });

    it("shows 'Tentar novamente' after a network error", async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(
        new TypeError("Network error")
      );

      render(<ItemsList jobId="job-123" totalFiltered={10} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Tentar novamente/i })
        ).toBeInTheDocument();
      });
    });
  });

  // ─── UX2 – Retry button re-fetches the page ──────────────────────────────

  describe("UX2 – Retry button re-fetches the page", () => {
    it("calls fetch again when the retry button is clicked", async () => {
      // First call → failure
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
      });
      // Second call (retry) → success
      (global.fetch as jest.Mock).mockResolvedValueOnce(
        itemsSuccessResponse()
      );

      render(<ItemsList jobId="job-123" totalFiltered={10} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Tentar novamente/i })
        ).toBeInTheDocument();
      });

      fireEvent.click(
        screen.getByRole("button", { name: /Tentar novamente/i })
      );

      await waitFor(() => {
        expect(global.fetch as jest.Mock).toHaveBeenCalledTimes(2);
      });
    });

    it("removes the error state after a successful retry", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
      });
      (global.fetch as jest.Mock).mockResolvedValueOnce(
        emptySuccessResponse()
      );

      render(<ItemsList jobId="job-123" totalFiltered={10} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Tentar novamente/i })
        ).toBeInTheDocument();
      });

      fireEvent.click(
        screen.getByRole("button", { name: /Tentar novamente/i })
      );

      await waitFor(() => {
        expect(
          screen.queryByRole("button", { name: /Tentar novamente/i })
        ).not.toBeInTheDocument();
      });
    });

    it("retries with the same page number (page=1 for initial failure)", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
      });
      (global.fetch as jest.Mock).mockResolvedValueOnce(
        emptySuccessResponse()
      );

      render(<ItemsList jobId="job-abc" totalFiltered={5} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Tentar novamente/i })
        ).toBeInTheDocument();
      });

      fireEvent.click(
        screen.getByRole("button", { name: /Tentar novamente/i })
      );

      await waitFor(() => {
        expect(global.fetch as jest.Mock).toHaveBeenCalledTimes(2);
      });

      const calls = (global.fetch as jest.Mock).mock.calls as [string][];
      expect(calls[0][0]).toContain("page=1");
      expect(calls[1][0]).toContain("page=1");
    });
  });

  // ─── Loading state ────────────────────────────────────────────────────────

  describe("Loading state", () => {
    it("shows a loading indicator while the fetch is in-flight", async () => {
      // Never resolves — keeps loading state indefinitely
      (global.fetch as jest.Mock).mockReturnValueOnce(new Promise(() => {}));

      render(<ItemsList jobId="job-123" totalFiltered={10} />);

      expect(screen.getByText(/Carregando/i)).toBeInTheDocument();
    });
  });

  // ─── CP3 – AbortController cancels stale requests on rapid page change ────

  describe("CP3 – AbortController cancels stale requests on page change", () => {
    it("aborts the first request's signal when a second page is requested", async () => {
      jest.useFakeTimers();

      const capturedSignals: AbortSignal[] = [];

      (global.fetch as jest.Mock).mockImplementation(
        (_url: string, opts?: { signal?: AbortSignal }) => {
          if (opts?.signal) capturedSignals.push(opts.signal);
          // Slow in-flight request that never resolves within the test window
          return new Promise((resolve) => {
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: () =>
                    Promise.resolve({
                      items: [],
                      total_pages: 0,
                      total_items: 0,
                    }),
                }),
              500
            );
          });
        }
      );

      render(<ItemsList jobId="job-123" totalFiltered={10} />);

      // Let the initial render kick off the first fetch
      act(() => {
        jest.advanceTimersByTime(0);
      });

      await waitFor(() => {
        expect(screen.getByTestId("pagination")).toBeInTheDocument();
      });

      // Request page 2 — should abort the in-flight page 1 request
      fireEvent.click(screen.getByTestId("page-2-btn"));

      act(() => {
        jest.advanceTimersByTime(0);
      });

      // Request page 3 — should abort the in-flight page 2 request
      fireEvent.click(screen.getByTestId("page-3-btn"));

      act(() => {
        jest.advanceTimersByTime(0);
      });

      await waitFor(() => {
        // At least 3 signals should have been captured (page 1, 2, 3)
        expect(capturedSignals.length).toBeGreaterThanOrEqual(3);
      });

      // Signals for page 1 and page 2 should both be aborted
      expect(capturedSignals[0].aborted).toBe(true);
      expect(capturedSignals[1].aborted).toBe(true);
    });

    it("aborts the previous request when navigating to a new page (two pages)", async () => {
      jest.useFakeTimers();

      let firstSignal: AbortSignal | undefined;

      (global.fetch as jest.Mock).mockImplementation(
        (_url: string, opts?: { signal?: AbortSignal }) => {
          const signal = opts?.signal;
          if (!firstSignal) firstSignal = signal;
          return new Promise((resolve) => {
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: () =>
                    Promise.resolve({
                      items: [],
                      total_pages: 1,
                      total_items: 0,
                    }),
                }),
              300
            );
          });
        }
      );

      render(<ItemsList jobId="job-123" totalFiltered={10} />);

      act(() => {
        jest.advanceTimersByTime(0);
      });

      await waitFor(() => {
        expect(screen.getByTestId("pagination")).toBeInTheDocument();
      });

      // Navigate to page 2 while page 1 is still in-flight
      fireEvent.click(screen.getByTestId("page-2-btn"));

      act(() => {
        jest.advanceTimersByTime(0);
      });

      expect(firstSignal).toBeDefined();
      expect(firstSignal!.aborted).toBe(true);
    });
  });

  // ─── UX6 – AbortController abort does NOT cause an error state ────────────

  describe("UX6 – AbortController cancels previous fetch without showing error", () => {
    it("does not show an error message when a request is aborted by page change", async () => {
      jest.useFakeTimers();

      (global.fetch as jest.Mock).mockImplementation(
        (_url: string, opts?: { signal?: AbortSignal }) => {
          const signal = opts?.signal;
          return new Promise((resolve, reject) => {
            const timer = setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: () =>
                    Promise.resolve({
                      items: [],
                      total_pages: 1,
                      total_items: 0,
                    }),
                }),
              200
            );

            if (signal) {
              signal.addEventListener("abort", () => {
                clearTimeout(timer);
                reject(new DOMException("Aborted", "AbortError"));
              });
            }
          });
        }
      );

      render(<ItemsList jobId="job-123" totalFiltered={10} />);

      act(() => {
        jest.advanceTimersByTime(0);
      });

      await waitFor(() => {
        expect(screen.getByTestId("pagination")).toBeInTheDocument();
      });

      // Navigate to page 2 — aborts the page 1 request
      fireEvent.click(screen.getByTestId("page-2-btn"));

      act(() => {
        jest.advanceTimersByTime(50);
      });

      // Navigate to page 3 — aborts the page 2 request
      fireEvent.click(screen.getByTestId("page-3-btn"));

      // Let the final page 3 request complete
      act(() => {
        jest.advanceTimersByTime(400);
      });

      // Aborted requests must be silently ignored — no error state
      await waitFor(() => {
        expect(screen.queryByText(/Erro de conexão/i)).not.toBeInTheDocument();
        expect(
          screen.queryByText(/Erro ao carregar/i)
        ).not.toBeInTheDocument();
        expect(
          screen.queryByRole("button", { name: /Tentar novamente/i })
        ).not.toBeInTheDocument();
      });
    });
  });
});
