import { useRef } from 'react';
import Editor, { type OnMount } from '@monaco-editor/react';
import { useEditorStore } from '@/stores/editorStore';

export function EditorPanel() {
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null);
  const { activeFile, files, setActiveFile } = useEditorStore();
  const currentFile = files.find((f) => f.path === activeFile);

  const handleEditorMount: OnMount = (editor) => {
    editorRef.current = editor;
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Tab bar */}
      <div className="flex h-9 items-center gap-0 border-b border-[var(--border)] bg-[var(--bg-secondary)]">
        {files.map((file) => (
          <button
            key={file.path}
            onClick={() => setActiveFile(file.path)}
            className={`flex h-full items-center gap-1 border-r border-[var(--border)] px-3 text-xs ${
              file.path === activeFile
                ? 'bg-[var(--bg-primary)] text-[var(--text-primary)]'
                : 'text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]'
            }`}
          >
            {file.name}
          </button>
        ))}
      </div>

      {/* Editor */}
      <div className="flex-1">
        {currentFile ? (
          <Editor
            height="100%"
            language={currentFile.language}
            value={currentFile.content}
            theme="vs-dark"
            onMount={handleEditorMount}
            options={{
              minimap: { enabled: true },
              fontSize: 14,
              lineNumbers: 'on',
              wordWrap: 'on',
              automaticLayout: true,
              scrollBeyondLastLine: false,
            }}
          />
        ) : (
          <div className="flex h-full items-center justify-center text-[var(--text-secondary)]">
            <div className="text-center">
              <h2 className="mb-2 text-lg">OneStream IDE Agent</h2>
              <p className="text-sm">Open a file or start a conversation with the AI assistant</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
