type ConsoleSidebarProps = {
  items: readonly string[];
};

function ConsoleSidebar({ items }: ConsoleSidebarProps) {
  return (
    <aside className="console-sidebar" aria-label="Console navigation">
      {items.map((item, index) => (
        <button key={item} className={`console-nav-item ${index === 1 ? "is-active" : ""}`} type="button">
          {item}
        </button>
      ))}
    </aside>
  );
}

export default ConsoleSidebar;
