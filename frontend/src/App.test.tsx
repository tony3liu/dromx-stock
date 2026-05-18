import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";

describe("landing page", () => {
  it("renders the landing page in english by default", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", {
        name: /Infinite productivity for the world/i
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: /Turn real-world capability into digital, structured, collaborative agents/i
      })
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Role Agents/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Skills Graph/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Swarm Runtime/i })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Built to make human capability copyable/i })
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Start a Workflow/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Example roles and progress/i)).toBeInTheDocument();
  });

  it("switches the landing page to chinese", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /中文/i }));

    expect(screen.getByRole("heading", { name: /让世界拥有无限生产力/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /开始执行/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /EN/i })).toBeInTheDocument();
  });

  it("opens the agent console from the landing page", async () => {
    const user = userEvent.setup();
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);

    await user.click(screen.getByRole("link", { name: /Start a Workflow/i }));

    expect(scrollTo).toHaveBeenCalledWith({ behavior: "auto", left: 0, top: 0 });
    expect(screen.getByRole("heading", { name: /Role Agent Console/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Agent Console/i })).toHaveClass("is-active");
    expect(screen.getByRole("heading", { name: /Sales Agent/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Edit Sales Agent/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Debug Sales Agent/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Publish Sales Agent$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Unpublish Sales Agent$/i })).toBeInTheDocument();
  });

  it("opens the agent console from the top navigation", async () => {
    const user = userEvent.setup();
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);

    await user.click(within(screen.getByRole("navigation", { name: /Primary navigation/i })).getByRole("link", { name: /^Console$/i }));

    expect(scrollTo).toHaveBeenCalledWith({ behavior: "auto", left: 0, top: 0 });
    expect(screen.getByRole("heading", { name: /Role Agent Console/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Agent Console/i })).toHaveClass("is-active");
  });

  it("opens a role agent editor with workflows skills mcp tools and debug", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);

    await user.click(screen.getByRole("link", { name: /Start a Workflow/i }));
    await user.click(screen.getByRole("button", { name: /Edit Sales Agent/i }));

    expect(screen.getByRole("heading", { name: /Sales Agent Builder/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Workflows/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Skills/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /MCP & Tools/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Debug Console/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Add Workflow/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Add Skill/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Bind MCP Tool/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Run Debug/i })).toBeInTheDocument();
  });
});
