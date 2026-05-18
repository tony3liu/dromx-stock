import type { AppContent } from "../../i18n/content";
import LogoMark from "../LogoMark";

type ConsoleHeaderProps = {
  onBackHome: () => void;
  onToggleLocale: () => void;
  t: AppContent;
};

function ConsoleHeader({ onBackHome, onToggleLocale, t }: ConsoleHeaderProps) {
  return (
    <header className="console-topbar">
      <a
        className="brand"
        href="/"
        aria-label={`${t.brand} home`}
        onClick={(event) => {
          event.preventDefault();
          onBackHome();
        }}
      >
        <span className="brand-mark">
          <LogoMark size={18} />
        </span>
        <span>{t.brand}</span>
      </a>
      <button className="lang-switch" type="button" onClick={onToggleLocale}>
        {t.switchTo}
      </button>
    </header>
  );
}

export default ConsoleHeader;
