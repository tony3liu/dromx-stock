import { ArrowRight, Play, ShieldCheck, Sparkles } from "lucide-react";
import type { AppContent, Locale } from "../i18n/content";
import LogoMark from "../components/LogoMark";

type LandingPageProps = {
  locale: Locale;
  onOpenConsole: () => void;
  onToggleLocale: () => void;
  t: AppContent;
};

function LandingPage({ locale, onOpenConsole, onToggleLocale, t }: LandingPageProps) {
  return (
    <main className="site-shell" lang={locale}>
      <header className="topbar">
        <a className="brand" href="/" aria-label={`${t.brand} home`}>
          <span className="brand-mark">
            <LogoMark size={18} />
          </span>
          <span>{t.brand}</span>
        </a>
        <nav className="nav-links" aria-label="Primary navigation">
          <a href="#platform">{t.nav.platform}</a>
          <a
            href="#console"
            onClick={(event) => {
              event.preventDefault();
              onOpenConsole();
            }}
          >
            {t.nav.console}
          </a>
          <a href="#trust">{t.nav.trust}</a>
        </nav>
        <button className="lang-switch" type="button" onClick={onToggleLocale}>
          {t.switchTo}
        </button>
      </header>

      <section className="hero-section">
        <div className="hero-copy">
          <div className="eyebrow">
            <Sparkles size={15} />
            {t.heroEyebrow}
          </div>
          <h1>{t.heroTitle}</h1>
          <h2 className="hero-subtitle">{t.heroSubtitle}</h2>
          <p>{t.heroCopy}</p>
          <div className="hero-actions">
            <a
              className="primary-action"
              href="#console"
              onClick={(event) => {
                event.preventDefault();
                onOpenConsole();
              }}
            >
              <Play size={17} />
              {t.primaryCta}
            </a>
            <a className="secondary-action" href="#platform">
              {t.secondaryCta}
              <ArrowRight size={16} />
            </a>
          </div>
        </div>

        <section className="mission-panel" id="console" aria-label="Live console preview">
          <div className="panel-header">
            <div>
              <span className="panel-kicker">{t.panelKicker}</span>
              <h2>{t.panelTitle}</h2>
            </div>
          </div>

          <div className="objective-box">
            <span>{t.objectiveLabel}</span>
            <strong>{t.objectiveText}</strong>
          </div>

          <div className="run-track" aria-label="Example roles and progress">
            <div className="run-track-inner">
              {[...t.liveRuns, ...t.liveRuns].map((run, index) => (
                <article className="run-row" key={`${run.task}-${index}`}>
                  <div>
                    <strong>{run.task}</strong>
                    <span>{run.agent}</span>
                  </div>
                  <span className="run-state">{run.state}</span>
                  <span className="progress">{run.progress}</span>
                </article>
              ))}
            </div>
          </div>
        </section>
      </section>

      <section className="platform-grid" id="platform" aria-label="Platform layers">
        {t.platformLayers.map((layer) => {
          const Icon = layer.icon;
          return (
            <article className="layer-card" key={layer.title}>
              <div className="layer-icon">
                <Icon size={22} />
              </div>
              <span>{layer.label}</span>
              <h2>{layer.title}</h2>
              <p>{layer.copy}</p>
            </article>
          );
        })}
      </section>

      <section className="operating-loop">
        <div>
          <span className="section-label">{t.loopLabel}</span>
          <h2>{t.loopTitle}</h2>
        </div>
        <div className="loop-steps" aria-label="Business loop steps">
          {t.businessLoop.map((step, index) => (
            <div className="loop-step" key={step}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{step}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="outcome-section">
        <div className="section-intro">
          <span className="section-label">{t.outcomesTitle}</span>
        </div>
        <div className="outcome-strip" aria-label="Outcome strip">
          {t.outcomes.map((item) => (
            <div className="outcome-card" key={item}>
              <strong>{item}</strong>
              <span>{t.outcomeCopy}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="split-section" id="trust">
        <div className="trust-copy">
          <span className="section-label">{t.trustLabel}</span>
          <h2>{t.trustTitle}</h2>
          <p>{t.trustCopy}</p>
        </div>
        <div className="trust-grid">
          {t.trustItems.map(([Icon, label]) => {
            const TrustIcon = Icon as typeof ShieldCheck;
            return (
              <div className="trust-item" key={label as string}>
                <TrustIcon size={18} />
                <span>{label as string}</span>
              </div>
            );
          })}
        </div>
      </section>

      <section className="use-case-strip" aria-label="Use cases">
        {t.useCases.map((useCase) => (
          <span key={useCase}>{useCase}</span>
        ))}
      </section>

      <section className="final-cta">
        <div>
          <span className="section-label">{t.finalLabel}</span>
          <h2>{t.finalTitle}</h2>
        </div>
        <a
          className="primary-action"
          href="#console"
          onClick={(event) => {
            event.preventDefault();
            onOpenConsole();
          }}
        >
          {t.finalCta}
          <ArrowRight size={16} />
        </a>
      </section>
    </main>
  );
}

export default LandingPage;
