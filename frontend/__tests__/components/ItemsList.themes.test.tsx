import { render } from "@testing-library/react";
import "@testing-library/jest-dom";
import { ItemsList } from "@/app/components/ItemsList";

// Mock fetch globally — return a pending promise so the component stays
// in a predictable "loading" state during snapshot capture.
const mockFetch = jest.fn();
global.fetch = mockFetch;

const themes = ["light", "paperwhite", "sepia", "dim", "dark"] as const;

describe("ItemsList theme snapshots", () => {
  beforeEach(() => {
    // Never resolves — keeps the component in the loading state so snapshots
    // are stable across runs (no async data races).
    mockFetch.mockReturnValue(new Promise<never>(() => {}));
  });

  afterEach(() => {
    jest.clearAllMocks();
    document.documentElement.removeAttribute("data-theme");
  });

  themes.forEach((theme) => {
    it(`renders correctly in ${theme} theme`, () => {
      document.documentElement.setAttribute("data-theme", theme);
      const { container } = render(
        <ItemsList jobId="snapshot-job" totalFiltered={5} />
      );
      expect(container).toMatchSnapshot();
    });
  });
});
