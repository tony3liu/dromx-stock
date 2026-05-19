type BreadcrumbItem = {
  label: string;
  path?: string;
};

type BreadcrumbsProps = {
  items: BreadcrumbItem[];
  onNavigate: (path: string) => void;
};

function Breadcrumbs({ items, onNavigate }: BreadcrumbsProps) {
  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <ol>
        {items.map((item, index) => {
          const isCurrent = index === items.length - 1;

          return (
            <li key={`${item.label}-${index}`}>
              {item.path && !isCurrent ? (
                <a
                  href={item.path}
                  onClick={(event) => {
                    event.preventDefault();
                    onNavigate(item.path!);
                  }}
                >
                  {item.label}
                </a>
              ) : (
                <span aria-current={isCurrent ? "page" : undefined}>{item.label}</span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export default Breadcrumbs;
