import { render } from "@testing-library/react";
import "@testing-library/jest-dom";
import AuthModal from "@/app/components/AuthModal";

// Mock AuthContext using the path relative to the component under test.
// jest.mock() resolves paths differently from imports (no tsconfig-path
// expansion), so we use the relative filesystem path to the actual module.
jest.mock("../../app/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: null,
    session: null,
    loading: false,
    signIn: jest.fn().mockResolvedValue({ error: null }),
    signUp: jest.fn().mockResolvedValue({ error: null }),
    signOut: jest.fn().mockResolvedValue(undefined),
  }),
}));

// Mock dialog.showModal / dialog.close — jsdom doesn't implement them
HTMLDialogElement.prototype.showModal = jest.fn();
HTMLDialogElement.prototype.close = jest.fn();

const themes = ["light", "paperwhite", "sepia", "dim", "dark"] as const;

describe("AuthModal theme snapshots", () => {
  afterEach(() => {
    document.documentElement.removeAttribute("data-theme");
  });

  themes.forEach((theme) => {
    it(`renders correctly in ${theme} theme`, () => {
      document.documentElement.setAttribute("data-theme", theme);
      const { container } = render(
        <AuthModal open={true} onClose={jest.fn()} />
      );
      expect(container).toMatchSnapshot();
    });
  });
});
