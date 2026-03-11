import { render, screen, fireEvent } from "@testing-library/react";
import { Select } from "../../app/components/Select";

const options = [
  { value: "a", label: "Option A" },
  { value: "b", label: "Option B" },
  { value: "c", label: "Option C", disabled: true },
];

describe("Select", () => {
  it("renders all options", () => {
    render(<Select options={options} />);
    expect(screen.getByText("Option A")).toBeInTheDocument();
    expect(screen.getByText("Option B")).toBeInTheDocument();
    expect(screen.getByText("Option C")).toBeInTheDocument();
  });

  it("renders with label", () => {
    render(<Select label="Setor" options={options} />);
    expect(screen.getByLabelText("Setor")).toBeInTheDocument();
  });

  it("renders with placeholder", () => {
    render(<Select options={options} placeholder="Selecione..." />);
    expect(screen.getByText("Selecione...")).toBeInTheDocument();
  });

  it("renders with error message", () => {
    render(<Select label="Setor" options={options} error="Required" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Required");
    expect(screen.getByLabelText("Setor")).toHaveAttribute("aria-invalid", "true");
  });

  it("renders with hint text", () => {
    render(<Select label="Setor" id="setor" options={options} hint="Choose one" />);
    expect(screen.getByText("Choose one")).toBeInTheDocument();
  });

  it("does not show hint when error is present", () => {
    render(<Select label="Setor" id="setor" options={options} hint="Hint" error="Error" />);
    expect(screen.queryByText("Hint")).not.toBeInTheDocument();
    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("applies error variant classes", () => {
    render(<Select label="Test" options={options} error="Err" />);
    expect(screen.getByLabelText("Test").className).toContain("border-error");
  });

  it("applies size classes", () => {
    render(<Select selectSize="lg" options={options} data-testid="sel" />);
    expect(screen.getByTestId("sel").className).toContain("text-lg");
  });

  it("supports disabled state", () => {
    render(<Select label="Disabled" options={options} disabled />);
    expect(screen.getByLabelText("Disabled")).toBeDisabled();
  });

  it("supports disabled options", () => {
    render(<Select options={options} data-testid="sel" />);
    const optC = screen.getByText("Option C") as HTMLOptionElement;
    expect(optC.disabled).toBe(true);
  });

  it("fires onChange", () => {
    const onChange = jest.fn();
    render(<Select label="Test" options={options} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Test"), { target: { value: "b" } });
    expect(onChange).toHaveBeenCalled();
  });

  it("generates id from label", () => {
    render(<Select label="My Select" options={options} />);
    expect(screen.getByLabelText("My Select")).toHaveAttribute("id", "my-select");
  });

  it("uses custom id over generated", () => {
    render(<Select label="Test" id="custom" options={options} />);
    expect(screen.getByLabelText("Test")).toHaveAttribute("id", "custom");
  });

  it("applies custom className", () => {
    render(<Select options={options} className="extra" data-testid="sel" />);
    expect(screen.getByTestId("sel").className).toContain("extra");
  });

  it("has aria-describedby for error", () => {
    render(<Select id="sel" options={options} error="Error" />);
    expect(screen.getByRole("combobox")).toHaveAttribute("aria-describedby", "sel-error");
  });

  it("renders without label or hint", () => {
    render(<Select options={options} data-testid="bare" />);
    expect(screen.getByTestId("bare")).toBeInTheDocument();
  });
});
