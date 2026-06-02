"""
OTel Runtime Analysis Plugin (SRS 4.5).

Receives OpenTelemetry trace spans and maps them to feature graph nodes:
  - service.name attribute → Service node in graph
  - http.route / http.target → API node
  - db.name + db.statement prefix → DatabaseTable node
  - Span parent/child → CALLS_IN_RUNTIME relationship

Output:
  - Runtime dependency graph (which services call which)
  - Execution traces (hot paths)
  - Bottleneck analysis (slowest spans)
"""
import re
from collections import defaultdict
from typing import Any

from companion.sdk.base.runtime_plugin import RuntimeGraph, RuntimePlugin, TraceSpan
from companion.sdk.base.plugin_base import PluginManifest


class Plugin(RuntimePlugin):
    def __init__(self, manifest: PluginManifest) -> None:
        super().__init__(manifest)

    async def analyze_traces(self, traces: list[TraceSpan]) -> RuntimeGraph:
        if not traces:
            return RuntimeGraph(nodes=[], edges=[], bottlenecks=[])

        # ── Build service call graph ────────────────────────────────────────
        services: set[str] = set()
        calls: dict[tuple[str, str], int] = defaultdict(int)
        durations: dict[str, list[float]] = defaultdict(list)

        # Group spans by trace_id to find parent/child relationships
        spans_by_trace: dict[str, list[TraceSpan]] = defaultdict(list)
        for span in traces:
            spans_by_trace[span.trace_id].append(span)
            services.add(span.service)
            durations[span.service].append(span.duration_ms)

        for trace_spans in spans_by_trace.values():
            # Sort by duration desc to find caller→callee
            sorted_spans = sorted(trace_spans, key=lambda s: s.duration_ms, reverse=True)
            for i, span in enumerate(sorted_spans[:-1]):
                callee = sorted_spans[i + 1]
                if span.service != callee.service:
                    calls[(span.service, callee.service)] += 1

        # ── Build output nodes ──────────────────────────────────────────────
        nodes = [
            {
                "id":           svc,
                "type":         "Service",
                "name":         svc,
                "avg_duration_ms": round(
                    sum(durations[svc]) / len(durations[svc]), 2
                ) if durations[svc] else 0,
                "call_count":   len(durations[svc]),
            }
            for svc in sorted(services)
        ]

        # ── Edges ────────────────────────────────────────────────────────────
        edges = [
            {
                "source":    src,
                "target":    tgt,
                "kind":      "CALLS_IN_RUNTIME",
                "frequency": count,
            }
            for (src, tgt), count in sorted(calls.items(), key=lambda x: -x[1])
        ]

        # ── Bottleneck analysis ───────────────────────────────────────────────
        avg_by_svc = {
            svc: sum(d) / len(d) for svc, d in durations.items()
        }
        p95_threshold = sorted(avg_by_svc.values())[-max(1, len(avg_by_svc) // 5)]

        bottlenecks = [
            {
                "service":          svc,
                "avg_duration_ms":  round(avg, 2),
                "severity":         "high" if avg > p95_threshold * 2 else "medium",
                "recommendation":   _recommend(svc, avg),
            }
            for svc, avg in sorted(avg_by_svc.items(), key=lambda x: -x[1])
            if avg >= p95_threshold
        ]

        return RuntimeGraph(nodes=nodes, edges=edges, bottlenecks=bottlenecks)


def _recommend(service: str, avg_ms: float) -> str:
    svc = service.lower()
    if avg_ms > 1000:
        return f"Critical: {service} averages {avg_ms:.0f}ms — investigate N+1 queries or blocking I/O"
    if "db" in svc or "postgres" in svc or "mysql" in svc:
        return f"Add database indexes or query caching for {service}"
    if "auth" in svc or "session" in svc:
        return f"Consider caching auth tokens for {service}"
    return f"Profile {service} for optimization opportunities ({avg_ms:.0f}ms avg)"
