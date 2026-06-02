import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

export function useFeatureGraph() {
  const { data, isLoading } = useQuery({
    queryKey: ["feature-graph"],
    queryFn: async () => {
      const [featRes, overviewRes] = await Promise.all([
        api.get("/api/v1/features/"),
        api.get("/api/v1/graph/overview"),
      ]);
      return { features: featRes.data.features, overview: overviewRes.data };
    },
    refetchInterval: 30_000,
  });

  return {
    features: data?.features ?? [],
    relationships: (data?.features ?? []).flatMap((f: any) => f.relationships ?? []),
    overview: data?.overview,
    isLoading,
  };
}
