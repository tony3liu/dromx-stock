import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";

describe("landing page", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/");
  });

  it("renders the landing page in english by default", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /Infinite productivity for the world/i })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: /Primary navigation/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Platform/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Trust/i })).not.toBeInTheDocument();
  });

  it("opens the console at its own url", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);

    await user.click(screen.getByRole("link", { name: /Start a Workflow/i }));

    expect(window.location.pathname).toBe("/console");
    expect(screen.getByRole("heading", { name: /Role Agent Console/i })).toBeInTheDocument();
  });

  it("supports browser back between pages", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);

    await user.click(screen.getByRole("link", { name: /Start a Workflow/i }));
    await user.click(screen.getByRole("button", { name: /Edit Sales Agent/i }));

    expect(window.location.pathname).toBe("/agents/0/edit");

    window.history.back();
    await screen.findByRole("heading", { name: /Role Agent Console/i });
    expect(window.location.pathname).toBe("/console");
  });

  it("selects an agent by clicking the card", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);

    await user.click(screen.getByRole("link", { name: /Start a Workflow/i }));
    const registry = screen.getByRole("region", { name: /Role Agents/i });
    const card = within(registry).getByRole("button", { name: /^Content Agent$/i });
    await user.click(card);

    expect(card).toHaveClass("is-selected");
    expect(screen.getByRole("heading", { name: /Content Agent/i })).toBeInTheDocument();
  });

  it("filters and searches role agents", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);

    await user.click(screen.getByRole("link", { name: /Start a Workflow/i }));
    await user.click(screen.getByRole("button", { name: /Filter Status/i }));
    expect(screen.queryByRole("button", { name: /Finance Agent/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Search Roles/i }));
    const searchInput = screen.getByRole("textbox", { name: /Search role agents/i });
    await user.clear(searchInput);
    await user.type(searchInput, "Research");
    expect(screen.getByRole("button", { name: /^Research Agent$/i })).toBeInTheDocument();
  });

  it("shows compact primary and tertiary actions on role agent cards", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);

    await user.click(screen.getByRole("link", { name: /Start a Workflow/i }));
    const registry = screen.getByRole("region", { name: /Role Agents/i });
    const card = within(registry).getByRole("button", { name: /^Sales Agent$/i });

    expect(within(card).getByRole("button", { name: /Edit Sales Agent/i })).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: /Debug Sales Agent/i })).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: /^Publish Sales Agent$/i })).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: /^Unpublish Sales Agent$/i })).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: /Copy Sales Agent/i })).toBeInTheDocument();
  });

  it("shows the shared top navigation on console and builder pages", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);

    await user.click(screen.getByRole("link", { name: /Start a Workflow/i }));
    expect(screen.getByRole("navigation", { name: /Primary navigation/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Edit Sales Agent/i }));
    expect(screen.getByRole("navigation", { name: /Primary navigation/i })).toBeInTheDocument();
  });

  it("shows breadcrumb navigation on the agent builder page", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);

    await user.click(screen.getByRole("link", { name: /Start a Workflow/i }));
    await user.click(screen.getByRole("button", { name: /Edit Sales Agent/i }));

    const breadcrumb = screen.getByRole("navigation", { name: /Breadcrumb/i });
    expect(within(breadcrumb).getByRole("link", { name: /Console/i })).toBeInTheDocument();
    expect(within(breadcrumb).getByText(/Sales Agent/i)).toBeInTheDocument();
  });
});
