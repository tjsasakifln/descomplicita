import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import ErrorBoundary from "@/app/error";

// Mock console.error to avoid noise in test output
const originalConsoleError = console.error;
beforeAll(() => {
  console.error = jest.fn();
});
afterAll(() => {
  console.error = originalConsoleError;
});

describe("Error Boundary Component", () => {
  const mockReset = jest.fn();
  const mockError = new Error("Test error message");

  beforeEach(() => {
    mockReset.mockClear();
    (console.error as jest.Mock).mockClear();
  });

  // AC1: Arquivo app/error.tsx criado
  it("should exist as a client component", () => {
    const { container } = render(<ErrorBoundary error={mockError} reset={mockReset} />);
    expect(container).toBeTruthy();
  });

  // AC2: Fallback UI amigável implementada
  describe("Fallback UI", () => {
    it("should render user-friendly error heading", () => {
      render(<ErrorBoundary error={mockError} reset={mockReset} />);
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
        "Ops! Algo deu errado"
      );
    });

    it("should display friendly error message", () => {
      render(<ErrorBoundary error={mockError} reset={mockReset} />);
      expect(
        screen.getByText(/Ocorreu um erro inesperado. Por favor, tente novamente./)
      ).toBeInTheDocument();
    });

    it("should show error icon with theme-aware color", () => {
      const { container } = render(<ErrorBoundary error={mockError} reset={mockReset} />);
      const svg = container.querySelector("svg");
      expect(svg).toBeInTheDocument();
      // Uses CSS custom property var(--error) via inline style instead of hardcoded class
      expect(svg).toHaveStyle({ color: "var(--error, #dc2626)" });
    });

    it("should display technical error message when available", () => {
      render(<ErrorBoundary error={mockError} reset={mockReset} />);
      expect(screen.getByText("Test error message")).toBeInTheDocument();
    });

    it("should render error message in monospace font for readability", () => {
      render(<ErrorBoundary error={mockError} reset={mockReset} />);
      const errorText = screen.getByText("Test error message");
      expect(errorText).toHaveClass("font-mono");
    });

    it("should display support contact message", () => {
      render(<ErrorBoundary error={mockError} reset={mockReset} />);
      expect(
        screen.getByText(/Se o problema persistir, entre em contato com o suporte./)
      ).toBeInTheDocument();
    });

    it("should be responsive and centered", () => {
      const { container } = render(<ErrorBoundary error={mockError} reset={mockReset} />);
      const wrapper = container.firstChild;
      expect(wrapper).toHaveClass("min-h-screen", "flex", "items-center", "justify-center");
    });
  });

  // AC3: Botão "Tentar novamente" funcional
  describe("Reset Button", () => {
    it('should render "Tentar novamente" button', () => {
      render(<ErrorBoundary error={mockError} reset={mockReset} />);
      expect(screen.getByRole("button", { name: /tentar novamente/i })).toBeInTheDocument();
    });

    it("should call reset function when button is clicked", () => {
      render(<ErrorBoundary error={mockError} reset={mockReset} />);
      const button = screen.getByRole("button", { name: /tentar novamente/i });
      fireEvent.click(button);
      expect(mockReset).toHaveBeenCalledTimes(1);
    });

    it("should call reset multiple times on multiple clicks", () => {
      render(<ErrorBoundary error={mockError} reset={mockReset} />);
      const button = screen.getByRole("button", { name: /tentar novamente/i });
      fireEvent.click(button);
      fireEvent.click(button);
      fireEvent.click(button);
      expect(mockReset).toHaveBeenCalledTimes(3);
    });

    it("should use theme-aware styling with CSS custom properties", () => {
      render(<ErrorBoundary error={mockError} reset={mockReset} />);
      const button = screen.getByRole("button", { name: /tentar novamente/i });
      // Uses var(--brand-navy) via inline style instead of hardcoded green classes
      expect(button).toHaveStyle({ background: "var(--brand-navy, #0a1e3f)" });
      expect(button).toHaveClass("focus:ring-2");
    });
  });

  // AC4: Erros logados apropriadamente
  describe("Error Logging", () => {
    it("should log error to console on mount", () => {
      render(<ErrorBoundary error={mockError} reset={mockReset} />);
      expect(console.error).toHaveBeenCalledWith("Application error:", mockError);
    });

    it("should log error only once per mount", () => {
      const { unmount } = render(<ErrorBoundary error={mockError} reset={mockReset} />);
      expect(console.error).toHaveBeenCalledTimes(1);
      unmount();
    });

    it("should re-log when error changes", () => {
      const { rerender } = render(<ErrorBoundary error={mockError} reset={mockReset} />);
      expect(console.error).toHaveBeenCalledTimes(1);

      const newError = new Error("Different error");
      rerender(<ErrorBoundary error={newError} reset={mockReset} />);
      expect(console.error).toHaveBeenCalledTimes(2);
      expect(console.error).toHaveBeenLastCalledWith("Application error:", newError);
    });
  });

  // Edge Cases
  describe("Edge Cases", () => {
    it("should handle error without message", () => {
      const errorWithoutMessage = new Error();
      errorWithoutMessage.message = "";
      const { container } = render(<ErrorBoundary error={errorWithoutMessage} reset={mockReset} />);
      expect(screen.getByRole("heading")).toBeInTheDocument();
      // When error.message is empty string (falsy), the error detail div should not render
      const errorDetailDivs = container.querySelectorAll(".rounded-md");
      // Empty message means the conditional block is skipped
      expect(errorDetailDivs.length).toBe(0);
    });

    it("should handle error with digest property", () => {
      const errorWithDigest = Object.assign(new Error("Digest error"), {
        digest: "abc123xyz",
      });
      render(<ErrorBoundary error={errorWithDigest} reset={mockReset} />);
      expect(screen.getByText("Digest error")).toBeInTheDocument();
    });

    it("should handle very long error messages with word wrap", () => {
      const longMessage = "x".repeat(500);
      const longError = new Error(longMessage);
      render(<ErrorBoundary error={longError} reset={mockReset} />);
      const errorText = screen.getByText(longMessage);
      expect(errorText).toHaveClass("break-words");
    });

    it("should handle special characters in error message", () => {
      const specialError = new Error('Error: <script>alert("xss")</script>');
      render(<ErrorBoundary error={specialError} reset={mockReset} />);
      expect(screen.getByText(/Error: <script>alert/)).toBeInTheDocument();
    });
  });

  // Accessibility
  describe("Accessibility", () => {
    it("should have proper ARIA attributes on icon", () => {
      const { container } = render(<ErrorBoundary error={mockError} reset={mockReset} />);
      const svg = container.querySelector("svg[aria-hidden='true']");
      expect(svg).toBeInTheDocument();
      expect(svg).toHaveAttribute("aria-hidden", "true");
    });

    it("should have focusable button with proper focus styles", () => {
      render(<ErrorBoundary error={mockError} reset={mockReset} />);
      const button = screen.getByRole("button", { name: /tentar novamente/i });
      button.focus();
      expect(button).toHaveFocus();
      expect(button).toHaveClass("focus:outline-none", "focus:ring-2");
    });

    it("should use CSS custom properties for theme-aware colors", () => {
      render(<ErrorBoundary error={mockError} reset={mockReset} />);
      const heading = screen.getByRole("heading");
      // Uses var(--ink) inline style instead of hardcoded text-gray-900
      expect(heading).toHaveStyle({ color: "var(--ink, #1e2d3b)" });
      const description = screen.getByText(/Ocorreu um erro inesperado/);
      expect(description).toHaveStyle({ color: "var(--ink-secondary, #3d5975)" });
    });
  });

  // Integration
  describe("Integration", () => {
    it("should work with Next.js error boundary contract", () => {
      const nextJsError = new Error("Next.js error");
      (nextJsError as any).digest = "nextjs-digest-123";

      render(<ErrorBoundary error={nextJsError} reset={mockReset} />);
      expect(screen.getByText("Next.js error")).toBeInTheDocument();
      expect(console.error).toHaveBeenCalledWith("Application error:", nextJsError);
    });

    it("should maintain component state after reset click", () => {
      const { rerender } = render(<ErrorBoundary error={mockError} reset={mockReset} />);
      const button = screen.getByRole("button", { name: /tentar novamente/i });

      fireEvent.click(button);
      expect(mockReset).toHaveBeenCalled();

      // Simulate re-render after reset
      rerender(<ErrorBoundary error={mockError} reset={mockReset} />);
      expect(screen.getByRole("heading")).toBeInTheDocument();
    });
  });

  // Visual Consistency — now using CSS custom properties (TD-030)
  describe("Visual Consistency", () => {
    it("should have consistent spacing classes", () => {
      const { container } = render(<ErrorBoundary error={mockError} reset={mockReset} />);
      const card = container.querySelector(".shadow-lg");
      expect(card).toHaveClass("p-8", "rounded-lg");
    });

    it("should use design tokens via CSS custom properties", () => {
      render(<ErrorBoundary error={mockError} reset={mockReset} />);
      const button = screen.getByRole("button", { name: /tentar novamente/i });
      // Now uses var(--brand-navy) instead of hardcoded bg-green-600
      expect(button).toHaveStyle({ background: "var(--brand-navy, #0a1e3f)" });
    });

    it("should render with proper layout structure", () => {
      const { container } = render(<ErrorBoundary error={mockError} reset={mockReset} />);
      expect(container.querySelector(".max-w-md")).toBeInTheDocument();
      // Uses inline style background instead of .bg-white class
      const card = container.querySelector(".shadow-lg");
      expect(card).toHaveStyle({ background: "var(--surface-0, #ffffff)" });
    });
  });
});
