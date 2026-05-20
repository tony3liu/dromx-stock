import { Fingerprint, Network, Terminal, Workflow, Cpu } from "lucide-react";

type ConsoleSidebarProps = {
  items: readonly string[];
  activeIndex: number;
  onNavigate: (index: number) => void;
};

function ConsoleSidebar({ items, activeIndex, onNavigate }: ConsoleSidebarProps) {
  const getIcon = (index: number) => {
    switch (index) {
      case 0:
        return <Fingerprint size={16} />;
      case 1:
        return <Network size={16} />;
      case 2:
        return <Terminal size={16} />;
      case 3:
        return <Workflow size={16} />;
      case 4:
        return <Cpu size={16} />;
      default:
        return null;
    }
  };

  return (
    <aside className="console-sidebar" aria-label="Console navigation" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
      {items.map((item, index) => (
        <button
          key={item}
          className={`console-nav-item ${index === activeIndex ? "is-active" : ""}`}
          type="button"
          onClick={() => onNavigate(index)}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            textAlign: "left",
            width: "100%",
            padding: "10px 14px",
            borderRadius: "6px",
            border: "none",
            cursor: "pointer",
            background: index === activeIndex ? "rgba(255, 255, 255, 0.05)" : "transparent",
            color: index === activeIndex ? "var(--text-primary)" : "var(--text-muted)",
            transition: "all 0.2s ease"
          }}
        >
          {getIcon(index)}
          <span style={{ fontSize: "14px", fontWeight: index === activeIndex ? 600 : 400 }}>{item}</span>
        </button>
      ))}
    </aside>
  );
}

export default ConsoleSidebar;
