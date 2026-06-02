import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

export function useFeatureDetail(featureId: string | null) {
  const featureQuery = useQuery({
    queryKey: ["feature", featureId],
    queryFn: () => api.get(`/api/v1/features/${featureId}`).then((r) => r.data),
    enabled: !!featureId,
  });

  const impactQuery = useQuery({
    queryKey: ["feature-impact", featureId],
    queryFn: () => api.get(`/api/v1/features/${featureId}/impact`).then((r) => r.data),
    enabled: !!featureId,
  });

  return {
    feature: featureQuery.data,
    impact: impactQuery.data,
    isLoading: featureQuery.isLoading || impactQuery.isLoading,
  };
}
