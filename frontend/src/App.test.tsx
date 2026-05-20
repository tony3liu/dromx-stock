import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
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

    // Open filter dropdown and select "Active" status
    await user.click(screen.getByRole("button", { name: /Filter Status/i }));
    const activeOption = screen.getByRole("checkbox", { name: /Active/i });
    await user.click(activeOption);
    // Close dropdown
    await user.click(screen.getByRole("button", { name: /Filter Status/i }));
    // Finance Agent is queued, should be hidden when filtering by active only
    expect(screen.queryByRole("button", { name: /Finance Agent/i })).not.toBeInTheDocument();

    // Toggle search input visible and search for Research
    await user.click(screen.getByRole("button", { name: /Search Roles/i }));
    const searchInput = screen.getByRole("textbox", { name: /Search role agents/i });
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

  it("keeps builder breadcrumbs below the sticky top navigation", () => {
    const styles = readFileSync(resolve(__dirname, "styles.css"), "utf8");

    expect(styles).toMatch(/\.builder-sticky-head\s+\.breadcrumbs\s*{[^}]*margin:\s*0\s+0\s+16px;/s);
  });

  it("navigates to workflows section via sidebar", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);

    await user.click(screen.getByRole("link", { name: /Start a Workflow/i }));

    // Click "Workflows" nav item in sidebar
    const sidebar = screen.getByRole("complementary", { name: /Console navigation/i });
    await user.click(within(sidebar).getByRole("button", { name: /Workflows/i }));

    expect(screen.getByRole("heading", { name: /Workflow Builder/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /New Workflow/i })).toBeInTheDocument();
  });

  it("opens workflow editor from the list", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);

    await user.click(screen.getByRole("link", { name: /Start a Workflow/i }));

    // Navigate to workflows
    const sidebar = screen.getByRole("complementary", { name: /Console navigation/i });
    await user.click(within(sidebar).getByRole("button", { name: /Workflows/i }));

    // Click edit on first workflow
    const editButtons = screen.getAllByRole("button", { name: /Edit Workflow/i });
    await user.click(editButtons[0]);

    expect(window.location.pathname).toBe("/workflows/0/edit");
    expect(screen.getByRole("button", { name: /Publish/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Add Step/i })).toBeInTheDocument();
  });

  it("shows breadcrumbs on workflow editor page", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);

    await user.click(screen.getByRole("link", { name: /Start a Workflow/i }));
    const sidebar = screen.getByRole("complementary", { name: /Console navigation/i });
    await user.click(within(sidebar).getByRole("button", { name: /Workflows/i }));
    const editButtons = screen.getAllByRole("button", { name: /Edit Workflow/i });
    await user.click(editButtons[0]);

    const breadcrumb = screen.getByRole("navigation", { name: /Breadcrumb/i });
    expect(within(breadcrumb).getByRole("link", { name: /Console/i })).toBeInTheDocument();
  });

  it("navigates to Role Agent Store via sidebar", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);

    await user.click(screen.getByRole("link", { name: /Start a Workflow/i }));

    const sidebar = screen.getByRole("complementary", { name: /Console navigation/i });
    await user.click(within(sidebar).getByRole("button", { name: /Role Agents/i }));

    expect(screen.getByRole("heading", { name: /Role Agent Store/i })).toBeInTheDocument();
    const useButtons = screen.getAllByRole("button", { name: /Use Agent/i });
    expect(useButtons.length).toBeGreaterThan(0);
  });

  it("filters store agents by tabs", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);

    await user.click(screen.getByRole("link", { name: /Start a Workflow/i }));
    const sidebar = screen.getByRole("complementary", { name: /Console navigation/i });
    await user.click(within(sidebar).getByRole("button", { name: /Role Agents/i }));

    // Click Free filter
    await user.click(screen.getByRole("button", { name: /Free/i }));
    // All visible agents should show FREE badge
    const freeBadges = screen.getAllByText(/FREE/i);
    expect(freeBadges.length).toBeGreaterThan(0);

    // Click Purchased filter
    await user.click(screen.getByRole("button", { name: /Purchased/i }));
    // All visible agents should show Purchased chip
    const purchasedChips = screen.getAllByText(/Purchased/i);
    expect(purchasedChips.length).toBeGreaterThan(0);
  });
});
