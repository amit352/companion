import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { api } from "../api";

export function useFeatureGraph() {
  const { data, isLoading } = useQuery({
    queryKey: ["feature-graph"],
    queryFn: async () => {
      const [featRes, overviewRes] = await Promise.all([
        api.get("/api/v1/features/"),
        api.get("/api/v1/graph/overview"),
      ]);
      return { features: featRes.data.features as any[], overview: overviewRes.data };
    },
    refetchInterval: 30_000,
  });

  const features = useMemo(() => data?.features ?? [], [data?.features]);
  const relationships = useMemo(
    () => features.flatMap((f) => f.relationships ?? []),
    [features]
  );

  return { features, relationships, overview: data?.overview, isLoading };
}
