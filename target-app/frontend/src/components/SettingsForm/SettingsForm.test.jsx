import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import SettingsForm from "./SettingsForm";

const userUpdate = vi.fn();
const setAuthState = vi.fn();
const navigate = vi.fn();

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({
    headers: { Authorization: "Token test" },
    isAuth: true,
    loggedUser: {
      bio: "",
      email: "developer@example.com",
      image: "",
      username: "developer",
    },
    setAuthState,
  }),
}));

vi.mock("../../services/userUpdate", () => ({
  default: (...args) => userUpdate(...args),
}));

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigate,
}));

describe("SettingsForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  test("re-enables submission after an update fails", async () => {
    userUpdate.mockRejectedValueOnce(new Error("request failed"));
    render(<SettingsForm />);

    fireEvent.click(screen.getByRole("button", { name: "Update Settings" }));

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Update Settings" }),
      ).toBeInTheDocument();
    });
    expect(userUpdate).toHaveBeenCalledOnce();
  });
});
