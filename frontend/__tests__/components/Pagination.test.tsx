import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import { Pagination } from "@/app/components/Pagination";

describe("Pagination", () => {
  const defaultProps = {
    currentPage: 1,
    totalPages: 5,
    onPageChange: jest.fn(),
    totalItems: 100,
    pageSize: 20,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders nothing when totalPages <= 1", () => {
    const { container } = render(
      <Pagination {...defaultProps} totalPages={1} totalItems={10} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when totalPages is 0", () => {
    const { container } = render(
      <Pagination {...defaultProps} totalPages={0} totalItems={0} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("shows correct item range info for first page", () => {
    render(<Pagination {...defaultProps} />);
    expect(screen.getByText("Mostrando 1-20 de 100 itens")).toBeInTheDocument();
  });

  it("shows correct item range info for middle page", () => {
    render(<Pagination {...defaultProps} currentPage={3} />);
    expect(
      screen.getByText("Mostrando 41-60 de 100 itens")
    ).toBeInTheDocument();
  });

  it("shows correct item range for last partial page", () => {
    render(
      <Pagination
        {...defaultProps}
        currentPage={5}
        totalPages={5}
        totalItems={95}
      />
    );
    expect(
      screen.getByText("Mostrando 81-95 de 95 itens")
    ).toBeInTheDocument();
  });

  it("disables previous button on first page", () => {
    render(<Pagination {...defaultProps} currentPage={1} />);
    const prevButton = screen.getByLabelText("Pagina anterior");
    expect(prevButton).toBeDisabled();
  });

  it("disables next button on last page", () => {
    render(<Pagination {...defaultProps} currentPage={5} />);
    const nextButton = screen.getByLabelText("Proxima pagina");
    expect(nextButton).toBeDisabled();
  });

  it("enables both buttons on a middle page", () => {
    render(<Pagination {...defaultProps} currentPage={3} />);
    expect(screen.getByLabelText("Pagina anterior")).not.toBeDisabled();
    expect(screen.getByLabelText("Proxima pagina")).not.toBeDisabled();
  });

  it("calls onPageChange when clicking next", () => {
    const onPageChange = jest.fn();
    render(
      <Pagination {...defaultProps} currentPage={2} onPageChange={onPageChange} />
    );
    fireEvent.click(screen.getByLabelText("Proxima pagina"));
    expect(onPageChange).toHaveBeenCalledWith(3);
  });

  it("calls onPageChange when clicking previous", () => {
    const onPageChange = jest.fn();
    render(
      <Pagination {...defaultProps} currentPage={3} onPageChange={onPageChange} />
    );
    fireEvent.click(screen.getByLabelText("Pagina anterior"));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("calls onPageChange when clicking a page number", () => {
    const onPageChange = jest.fn();
    render(
      <Pagination {...defaultProps} currentPage={1} onPageChange={onPageChange} />
    );
    fireEvent.click(screen.getByLabelText("Pagina 4"));
    expect(onPageChange).toHaveBeenCalledWith(4);
  });

  it("highlights current page with aria-current", () => {
    render(<Pagination {...defaultProps} currentPage={3} />);
    const currentBtn = screen.getByLabelText("Pagina 3");
    expect(currentBtn).toHaveAttribute("aria-current", "page");
  });

  it("shows all page numbers when totalPages <= 7", () => {
    render(<Pagination {...defaultProps} totalPages={7} totalItems={140} />);
    for (let i = 1; i <= 7; i++) {
      expect(screen.getByLabelText(`Pagina ${i}`)).toBeInTheDocument();
    }
  });

  it("shows ellipsis for many pages", () => {
    render(
      <Pagination
        {...defaultProps}
        currentPage={5}
        totalPages={20}
        totalItems={400}
      />
    );
    // Should have at least one ellipsis
    const ellipses = screen.getAllByText("...");
    expect(ellipses.length).toBeGreaterThanOrEqual(1);
  });

  it("has navigation aria-label", () => {
    render(<Pagination {...defaultProps} />);
    expect(
      screen.getByRole("navigation", { name: /paginas/i })
    ).toBeInTheDocument();
  });
});
