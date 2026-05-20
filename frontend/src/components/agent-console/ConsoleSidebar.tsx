type ConsoleSidebarProps = {
  items: readonly string[];
  activeIndex: number;
  onNavigate: (index: number) => void;
};

function ConsoleSidebar({ items, activeIndex, onNavigate }: ConsoleSidebarProps) {
  return (
    <aside className="console-sidebar" aria-label="Console navigation">
      {items.map((item, index) => (
        <button
          key={item}
          className={`console-nav-item ${index === activeIndex ? "is-active" : ""}`}
          type="button"
          onClick={() => onNavigate(index)}
        >
          {item}
        </button>
      ))}
    </aside>
  );
}

export default ConsoleSidebar;
