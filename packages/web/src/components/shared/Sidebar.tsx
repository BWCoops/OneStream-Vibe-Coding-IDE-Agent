interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const navItems = [
  { id: 'explorer', label: 'Explorer', icon: '{}' },
  { id: 'rules', label: 'Business Rules', icon: 'BR' },
  { id: 'pipelines', label: 'Pipelines', icon: 'PL' },
  { id: 'testing', label: 'Testing', icon: 'TS' },
  { id: 'alm', label: 'ALM', icon: 'AL' },
  { id: 'rtm', label: 'Traceability', icon: 'RT' },
] as const;

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className={`flex flex-col border-r border-[var(--border)] bg-[var(--bg-secondary)] transition-all ${
        collapsed ? 'w-12' : 'w-56'
      }`}
    >
      <button
        onClick={onToggle}
        className="flex h-10 items-center justify-center border-b border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
      >
        {collapsed ? '>' : '<'}
      </button>
      <nav className="flex flex-1 flex-col gap-1 p-1">
        {navItems.map((item) => (
          <button
            key={item.id}
            className="flex items-center gap-2 rounded px-2 py-2 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-surface)] hover:text-[var(--text-primary)]"
          >
            <span className="flex h-6 w-6 items-center justify-center rounded bg-[var(--bg-surface)] text-xs font-bold">
              {item.icon}
            </span>
            {!collapsed && <span>{item.label}</span>}
          </button>
        ))}
      </nav>
    </aside>
  );
}
