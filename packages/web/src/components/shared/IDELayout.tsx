import { useState } from 'react';
import { EditorPanel } from '@/components/editor/EditorPanel';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { Sidebar } from '@/components/shared/Sidebar';

export function IDELayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [chatOpen, setChatOpen] = useState(true);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--bg-primary)]">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <main className="flex flex-1 overflow-hidden">
        <div className="flex-1 flex flex-col overflow-hidden">
          <EditorPanel />
        </div>
        {chatOpen && (
          <div className="w-[400px] border-l border-[var(--border)]">
            <ChatPanel onClose={() => setChatOpen(false)} />
          </div>
        )}
      </main>
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-4 right-4 rounded-full bg-[var(--accent)] p-3 text-[var(--bg-primary)] shadow-lg hover:bg-[var(--accent-hover)]"
        >
          AI
        </button>
      )}
    </div>
  );
}
