"""OTEL Sampler that drops health-check spans to reduce APM noise.

Wraps the delegate sampler (typically ParentBased) and returns DROP for spans
whose name or ``http.target`` attribute matches a known health-check path.
All other spans are delegated to the original sampler.

This follows the same pattern as the Java example in the OpenTelemetry docs:
a custom ``Sampler`` that inspects span attributes and returns
``SamplingDecision.DROP`` for unwanted spans.

See: https://stackoverflow.com/a/74600948
"""

from opentelemetry.context import Context
from opentelemetry.sdk.trace.sampling import Decision, Sampler, SamplingResult
from opentelemetry.trace import Link, SpanKind
from opentelemetry.util.types import Attributes

# Paths that should never produce traces.
_HEALTH_PATHS = frozenset({'/health', '/alive', '/ready', '/server_info'})


class HealthCheckSampler(Sampler):
    """Drop health-check spans, delegate everything else."""

    def __init__(self, delegate: Sampler) -> None:
        self._delegate = delegate

    def should_sample(
        self,
        parent_context: Context | None,
        trace_id: int,
        name: str,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: list[Link] | None = None,
    ) -> SamplingResult:
        # Check span name (often set to the HTTP route)
        if name in _HEALTH_PATHS:
            return SamplingResult(Decision.DROP)

        # Check http.target attribute (standard OTEL semantic convention)
        if attributes:
            http_target = attributes.get('http.target', '')
            if http_target in _HEALTH_PATHS:
                return SamplingResult(Decision.DROP)

        return self._delegate.should_sample(
            parent_context, trace_id, name, kind, attributes, links
        )

    def get_description(self) -> str:
        return f'HealthCheckSampler({self._delegate.get_description()})'
