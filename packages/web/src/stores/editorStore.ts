import { create } from 'zustand';

export interface EditorFile {
  path: string;
  name: string;
  content: string;
  language: string;
  dirty: boolean;
}

interface EditorState {
  files: EditorFile[];
  activeFile: string | null;
  openFile: (file: EditorFile) => void;
  closeFile: (path: string) => void;
  setActiveFile: (path: string) => void;
  updateFileContent: (path: string, content: string) => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  files: [],
  activeFile: null,

  openFile: (file) =>
    set((state) => {
      const exists = state.files.some((f) => f.path === file.path);
      if (exists) {
        return { activeFile: file.path };
      }
      return {
        files: [...state.files, file],
        activeFile: file.path,
      };
    }),

  closeFile: (path) =>
    set((state) => {
      const filtered = state.files.filter((f) => f.path !== path);
      const newActive =
        state.activeFile === path
          ? filtered[filtered.length - 1]?.path ?? null
          : state.activeFile;
      return { files: filtered, activeFile: newActive };
    }),

  setActiveFile: (path) => set({ activeFile: path }),

  updateFileContent: (path, content) =>
    set((state) => ({
      files: state.files.map((f) =>
        f.path === path ? { ...f, content, dirty: true } : f,
      ),
    })),
}));
