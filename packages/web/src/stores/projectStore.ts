import { create } from 'zustand';

export interface Environment {
  id: string;
  name: string;
  type: 'DEV' | 'TEST' | 'UAT' | 'PROD';
  url: string;
  apiVersion: string;
  platformVersion: string | null;
  dotnetRuntime: 'net8.0' | 'net48' | null;
  sicEnabled: boolean;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  defaultEnvironmentId: string | null;
}

interface ProjectState {
  currentProject: Project | null;
  environments: Environment[];
  activeEnvironment: Environment | null;
  setCurrentProject: (project: Project) => void;
  setEnvironments: (envs: Environment[]) => void;
  setActiveEnvironment: (env: Environment) => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  currentProject: null,
  environments: [],
  activeEnvironment: null,
  setCurrentProject: (project) => set({ currentProject: project }),
  setEnvironments: (environments) => set({ environments }),
  setActiveEnvironment: (env) => set({ activeEnvironment: env }),
}));
