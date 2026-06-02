"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";

const API = "http://localhost:8000";

interface Repo {
  path:         string;
  name:         string;
  last_analyzed: string;
  feature_count: number;
}

interface ProjectContextValue {
  repos:        Repo[];
  selectedRepo: Repo | null;
  selectRepo:   (repo: Repo | null) => void;
  repoParam:    string;   // query param value — empty string = all repos
}

const ProjectContext = createContext<ProjectContextValue>({
  repos: [], selectedRepo: null, selectRepo: () => {}, repoParam: "",
});

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [repos, setRepos]               = useState<Repo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<Repo | null>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/graph/repositories`)
      .then((r) => r.json())
      .then((d) => {
        const list: Repo[] = d.repositories ?? [];
        setRepos(list);
        // Auto-select first repo if there are multiple
        if (list.length === 1) setSelectedRepo(list[0]);
      })
      .catch(() => {});
  }, []);

  const repoParam = selectedRepo?.path ?? "";

  return (
    <ProjectContext.Provider value={{ repos, selectedRepo, selectRepo: setSelectedRepo, repoParam }}>
      {children}
    </ProjectContext.Provider>
  );
}

export const useProject = () => useContext(ProjectContext);
