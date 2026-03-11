import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Input } from "../../app/components/Input";

describe("Input", () => {
  it("renders a basic input", () => {
    render(<Input placeholder="Type here" />);
    expect(screen.getByPlaceholderText("Type here")).toBeInTheDocument();
  });

  it("renders with label", () => {
    render(<Input label="Email" />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
  });

  it("renders with error message", () => {
    render(<Input label="Name" error="Required field" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Required field");
    expect(screen.getByLabelText("Name")).toHaveAttribute("aria-invalid", "true");
  });

  it("renders with hint text", () => {
    render(<Input label="Name" id="name" hint="Enter your full name" />);
    expect(screen.getByText("Enter your full name")).toBeInTheDocument();
  });

  it("does not show hint when error is present", () => {
    render(<Input label="Name" id="name" hint="Hint text" error="Error text" />);
    expect(screen.queryByText("Hint text")).not.toBeInTheDocument();
    expect(screen.getByText("Error text")).toBeInTheDocument();
  });

  it("applies error variant classes", () => {
    render(<Input label="Test" error="Error" />);
    const input = screen.getByLabelText("Test");
    expect(input.className).toContain("border-error");
  });

  it("applies default variant classes", () => {
    render(<Input label="Test" />);
    const input = screen.getByLabelText("Test");
    expect(input.className).toContain("border-strong");
  });

  it("applies size classes", () => {
    const { rerender } = render(<Input inputSize="sm" data-testid="inp" />);
    expect(screen.getByTestId("inp").className).toContain("text-sm");

    rerender(<Input inputSize="lg" data-testid="inp" />);
    expect(screen.getByTestId("inp").className).toContain("text-lg");
  });

  it("supports disabled state", () => {
    render(<Input label="Disabled" disabled />);
    expect(screen.getByLabelText("Disabled")).toBeDisabled();
  });

  it("generates id from label", () => {
    render(<Input label="Full Name" />);
    expect(screen.getByLabelText("Full Name")).toHaveAttribute("id", "full-name");
  });

  it("uses custom id over generated", () => {
    render(<Input label="Test" id="custom-id" />);
    expect(screen.getByLabelText("Test")).toHaveAttribute("id", "custom-id");
  });

  it("applies custom className", () => {
    render(<Input className="extra-class" data-testid="inp" />);
    expect(screen.getByTestId("inp").className).toContain("extra-class");
  });

  it("fires onChange", async () => {
    const onChange = jest.fn();
    render(<Input label="Test" onChange={onChange} />);
    await userEvent.type(screen.getByLabelText("Test"), "abc");
    expect(onChange).toHaveBeenCalledTimes(3);
  });

  it("has aria-describedby for error", () => {
    render(<Input id="test" error="Error" />);
    expect(screen.getByRole("textbox")).toHaveAttribute("aria-describedby", "test-error");
  });

  it("has aria-describedby for hint", () => {
    render(<Input id="test" hint="Some hint" />);
    expect(screen.getByRole("textbox")).toHaveAttribute("aria-describedby", "test-hint");
  });

  it("renders without label or hint", () => {
    render(<Input data-testid="bare" />);
    expect(screen.getByTestId("bare")).toBeInTheDocument();
  });
});
