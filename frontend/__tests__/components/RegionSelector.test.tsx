import { render, screen, fireEvent } from "@testing-library/react";
import { RegionSelector } from "../../app/components/RegionSelector";

describe("RegionSelector", () => {
  const onToggleRegion = jest.fn();

  afterEach(() => jest.clearAllMocks());

  it("renders all 5 region buttons", () => {
    render(<RegionSelector selected={new Set()} onToggleRegion={onToggleRegion} />);
    expect(screen.getByText("Norte")).toBeInTheDocument();
    expect(screen.getByText("Nordeste")).toBeInTheDocument();
    expect(screen.getByText("Centro-Oeste")).toBeInTheDocument();
    expect(screen.getByText("Sudeste")).toBeInTheDocument();
    expect(screen.getByText("Sul")).toBeInTheDocument();
  });

  it("applies fully selected style when all region UFs selected", () => {
    const selected = new Set(["PR", "RS", "SC"]);
    render(<RegionSelector selected={selected} onToggleRegion={onToggleRegion} />);
    const sulButton = screen.getByText("Sul");
    expect(sulButton.className).toContain("bg-brand-navy");
  });

  it("applies partially selected style when some UFs selected", () => {
    const selected = new Set(["PR"]);
    render(<RegionSelector selected={selected} onToggleRegion={onToggleRegion} />);
    const sulButton = screen.getByText("Sul");
    expect(sulButton.className).toContain("bg-brand-blue-subtle");
  });

  it("shows count for partially selected region", () => {
    const selected = new Set(["PR", "SC"]);
    render(<RegionSelector selected={selected} onToggleRegion={onToggleRegion} />);
    expect(screen.getByText("(2/3)")).toBeInTheDocument();
  });

  it("does not show count for fully selected region", () => {
    const selected = new Set(["PR", "RS", "SC"]);
    render(<RegionSelector selected={selected} onToggleRegion={onToggleRegion} />);
    expect(screen.queryByText(/\d\/3/)).not.toBeInTheDocument();
  });

  it("applies default style when no UFs selected", () => {
    render(<RegionSelector selected={new Set()} onToggleRegion={onToggleRegion} />);
    const sulButton = screen.getByText("Sul");
    expect(sulButton.className).toContain("bg-surface-1");
  });

  it("calls onToggleRegion with region UFs on click", () => {
    render(<RegionSelector selected={new Set()} onToggleRegion={onToggleRegion} />);
    fireEvent.click(screen.getByText("Sul"));
    expect(onToggleRegion).toHaveBeenCalledWith(["PR", "RS", "SC"]);
  });

  it("has aria-label for each region button", () => {
    render(<RegionSelector selected={new Set()} onToggleRegion={onToggleRegion} />);
    expect(screen.getByLabelText("Selecionar região Sul")).toBeInTheDocument();
    expect(screen.getByLabelText("Selecionar região Norte")).toBeInTheDocument();
  });
});
