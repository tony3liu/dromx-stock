import LogoMark from "./LogoMark";
import type { Locale } from "../i18n/content";

type NavItem = {
  active?: boolean;
  label: string;
  path: string;
};

type AppHeaderProps = {
  navItems: NavItem[];
  onNavigate: (path: string) => void;
  onToggleLocale: () => void;
  switchLabel: string;
  variant?: "landing" | "workspace";
};

function AppHeader({ navItems, onNavigate, onToggleLocale, switchLabel, variant = "landing" }: AppHeaderProps) {
  return (
    <header className={variant === "landing" ? "topbar" : "console-topbar"}>
      <a
        className="brand"
        href="/"
        aria-label="DromX home"
        onClick={(event) => {
          event.preventDefault();
          onNavigate("/");
        }}
      >
        <span className="brand-mark">
          <LogoMark size={18} />
        </span>
        <span>DromX</span>
      </a>
      <nav className="nav-links" aria-label="Primary navigation">
        {navItems.map((item) => (
          <a
            key={item.path}
            className={item.active ? "is-active" : ""}
            href={item.path}
            aria-current={item.active ? "page" : undefined}
            onClick={(event) => {
              event.preventDefault();
              onNavigate(item.path);
            }}
          >
            {item.label}
          </a>
        ))}
      </nav>
      <button className="lang-switch" type="button" onClick={onToggleLocale}>
        {switchLabel}
      </button>
    </header>
  );
}

export default AppHeader;
