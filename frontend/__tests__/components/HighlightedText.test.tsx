import { render, screen } from "@testing-library/react";
import { HighlightedText } from "../../app/components/HighlightedText";

describe("HighlightedText", () => {
  it("renders plain text when no keywords", () => {
    render(<HighlightedText text="Aquisição de uniformes" keywords={[]} />);
    expect(screen.getByText("Aquisição de uniformes")).toBeInTheDocument();
    expect(screen.queryByRole("mark")).toBeNull();
  });

  it("renders plain text when keywords is empty array", () => {
    const { container } = render(
      <HighlightedText text="Sem destaque" keywords={[]} />
    );
    expect(container.querySelectorAll("mark")).toHaveLength(0);
  });

  it("highlights a single keyword", () => {
    const { container } = render(
      <HighlightedText text="Aquisição de uniformes escolares" keywords={["uniformes"]} />
    );
    const marks = container.querySelectorAll("mark");
    expect(marks).toHaveLength(1);
    expect(marks[0].textContent).toBe("uniformes");
  });

  it("highlights multiple keywords", () => {
    const { container } = render(
      <HighlightedText
        text="Aquisição de uniformes e fardamento escolar"
        keywords={["uniformes", "fardamento"]}
      />
    );
    const marks = container.querySelectorAll("mark");
    expect(marks).toHaveLength(2);
    const texts = Array.from(marks).map((m) => m.textContent);
    expect(texts).toContain("uniformes");
    expect(texts).toContain("fardamento");
  });

  it("highlights accent-insensitive: 'confeccao' matches 'confecção'", () => {
    const { container } = render(
      <HighlightedText text="Confecção de roupas profissionais" keywords={["confeccao"]} />
    );
    const marks = container.querySelectorAll("mark");
    expect(marks).toHaveLength(1);
    expect(marks[0].textContent).toBe("Confecção");
  });

  it("highlights accent-insensitive: 'licitacao' matches 'licitação'", () => {
    const { container } = render(
      <HighlightedText text="Processo de licitação pública" keywords={["licitacao"]} />
    );
    const marks = container.querySelectorAll("mark");
    expect(marks).toHaveLength(1);
    expect(marks[0].textContent).toBe("licitação");
  });

  it("highlights case-insensitive: 'UNIFORME' matches 'uniforme'", () => {
    const { container } = render(
      <HighlightedText text="Compra de uniforme escolar" keywords={["UNIFORME"]} />
    );
    const marks = container.querySelectorAll("mark");
    expect(marks).toHaveLength(1);
    expect(marks[0].textContent).toBe("uniforme");
  });

  it("preserves original text casing in highlighted segments", () => {
    const { container } = render(
      <HighlightedText text="UNIFORMES para a Guarda Municipal" keywords={["uniformes"]} />
    );
    const marks = container.querySelectorAll("mark");
    expect(marks).toHaveLength(1);
    expect(marks[0].textContent).toBe("UNIFORMES");
  });

  it("handles multiple occurrences of the same keyword", () => {
    const { container } = render(
      <HighlightedText text="uniforme tipo A e uniforme tipo B" keywords={["uniforme"]} />
    );
    const marks = container.querySelectorAll("mark");
    expect(marks).toHaveLength(2);
  });

  it("handles overlapping keyword ranges by merging", () => {
    const { container } = render(
      <HighlightedText text="uniformes escolares" keywords={["uniforme", "uniformes"]} />
    );
    const marks = container.querySelectorAll("mark");
    // "uniforme" and "uniformes" overlap — should merge into one mark
    expect(marks).toHaveLength(1);
    expect(marks[0].textContent).toBe("uniformes");
  });

  it("does not use dangerouslySetInnerHTML (XSS safe)", () => {
    const malicious = '<script>alert("xss")</script> uniformes';
    const { container } = render(
      <HighlightedText text={malicious} keywords={["uniformes"]} />
    );
    // Script tag should be rendered as text, not executed
    expect(container.innerHTML).toContain("&lt;script&gt;");
    expect(container.querySelectorAll("script")).toHaveLength(0);
  });

  it("returns original text when keyword not found in text", () => {
    const { container } = render(
      <HighlightedText text="Compra de materiais de escritório" keywords={["uniforme"]} />
    );
    expect(container.querySelectorAll("mark")).toHaveLength(0);
    expect(container.textContent).toBe("Compra de materiais de escritório");
  });

  it("handles empty text gracefully", () => {
    const { container } = render(
      <HighlightedText text="" keywords={["uniforme"]} />
    );
    expect(container.textContent).toBe("");
  });

  it("handles empty keyword strings gracefully", () => {
    const { container } = render(
      <HighlightedText text="Some text" keywords={[""]} />
    );
    expect(container.querySelectorAll("mark")).toHaveLength(0);
  });
});
