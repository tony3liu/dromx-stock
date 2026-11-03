import logoIcon from "../assets/brand/logo-icon.png";

/** DromX brand mark — circular mascot icon from the new logo lockup.
 *  Transparent PNG so it works on both dark and light surfaces. */
export function Logo({ size = 36, className = "" }: { size?: number; className?: string }) {
  return (
    <img
      src={logoIcon}
      alt="DromX"
      width={size}
      height={size}
      className={`h-auto object-contain ${className}`}
      style={{ width: size, height: size }}
    />
  );
}

/** Wordmark lockup: mascot icon + "Drom" white / "X" brand gradient.
 *  Icon is the dominant element; text is scaled down so the lockup stays readable
 *  even when the icon is enlarged for small high-DPI screens. */
export function LogoLockup({ size = 30, className = "" }: { size?: number; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <Logo size={size} />
      <span
        className="font-black tracking-tight text-[var(--color-ink)]"
        style={{ fontFamily: "var(--font-display)", fontSize: size * 0.45 }}
      >
        Drom<span className="gradient-text-static">X</span>
      </span>
    </span>
  );
}
