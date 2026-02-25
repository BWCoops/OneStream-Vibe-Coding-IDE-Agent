import { useState, useRef, useEffect } from 'react';
import { useChatStore, type ChatMessage } from '@/stores/chatStore';

interface ChatPanelProps {
  onClose: () => void;
}

export function ChatPanel({ onClose }: ChatPanelProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { messages, isStreaming, sendMessage } = useChatStore();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    sendMessage(input.trim());
    setInput('');
  };

  return (
    <div className="flex h-full flex-col bg-[var(--bg-secondary)]">
      {/* Header */}
      <div className="flex h-10 items-center justify-between border-b border-[var(--border)] px-3">
        <span className="text-sm font-medium">AI Assistant</span>
        <button
          onClick={onClose}
          className="text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        >
          x
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-[var(--text-secondary)]">
            Ask me about OneStream business rules, data pipelines, or code generation.
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {messages.map((msg: ChatMessage) => (
              <div
                key={msg.id}
                className={`rounded-lg px-3 py-2 text-sm ${
                  msg.role === 'user'
                    ? 'ml-8 bg-[var(--accent)] text-[var(--bg-primary)]'
                    : 'mr-8 bg-[var(--bg-surface)] text-[var(--text-primary)]'
                }`}
              >
                <pre className="whitespace-pre-wrap font-[inherit]">{msg.content}</pre>
              </div>
            ))}
            {isStreaming && (
              <div className="mr-8 rounded-lg bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-secondary)]">
                Thinking...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t border-[var(--border)] p-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about OneStream..."
            disabled={isStreaming}
            className="flex-1 rounded bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-secondary)] outline-none focus:ring-1 focus:ring-[var(--accent)]"
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="rounded bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--bg-primary)] hover:bg-[var(--accent-hover)] disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
