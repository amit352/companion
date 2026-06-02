import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { api } from "../api";
import { useProject } from "../projectContext";

export function useCompanion() {
  const { repoParam } = useProject();

  const { data, isLoading } = useQuery({
    queryKey: ["companion", repoParam],
    queryFn: async () => {
      const params = repoParam ? `?repo_path=${encodeURIComponent(repoParam)}` : "";
      const [featRes, relsRes, overviewRes] = await Promise.all([
        api.get(`/api/v1/features/${params}`),
        api.get("/api/v1/graph/relationships"),
        api.get(`/api/v1/graph/overview${params}`),
      ]);
      return {
        features:      featRes.data.features as any[],
        relationships: relsRes.data.relationships as any[],
        overview:      overviewRes.data,
      };
    },
    refetchInterval: 30_000,
  });

  const features      = useMemo(() => data?.features ?? [],      [data?.features]);
  const relationships = useMemo(() => data?.relationships ?? [], [data?.relationships]);

  return { features, relationships, overview: data?.overview, isLoading };
}
