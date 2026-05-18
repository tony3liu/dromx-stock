import { useState } from "react";
import AgentConsole from "./pages/AgentConsole";
import LandingPage from "./pages/LandingPage";
import { content, type Locale } from "./i18n/content";
type Screen = "landing" | "console";

function App() {
  const [locale, setLocale] = useState<Locale>("en");
  const [screen, setScreen] = useState<Screen>("landing");
  const [selectedAgentIndex, setSelectedAgentIndex] = useState(0);
  const [isEditingAgent, setIsEditingAgent] = useState(false);
  const t = content[locale];
  const selectedAgent = t.console.roles[selectedAgentIndex];
  const openConsole = () => {
    setScreen("console");
    setIsEditingAgent(false);
    window.scrollTo({ behavior: "auto", left: 0, top: 0 });
  };

  if (screen === "console") {
    return (
      <AgentConsole
        isEditingAgent={isEditingAgent}
        locale={locale}
        onBackHome={() => setScreen("landing")}
        onSelectAgent={(index) => {
          setSelectedAgentIndex(index);
          setIsEditingAgent(true);
        }}
        onToggleLocale={() => setLocale(locale === "en" ? "zh" : "en")}
        selectedAgent={selectedAgent}
        selectedAgentIndex={selectedAgentIndex}
        t={t}
      />
    );
  }

  return (
    <LandingPage
      locale={locale}
      onOpenConsole={openConsole}
      onToggleLocale={() => setLocale(locale === "en" ? "zh" : "en")}
      t={t}
    />
  );
}

export default App;
