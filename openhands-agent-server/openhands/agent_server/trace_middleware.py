"""Middleware to extract W3C Trace Context and Baggage from incoming HTTP requests.

The runtime API (Go/dd-trace-go) injects both Datadog and W3C trace headers when
DD_TRACE_PROPAGATION_STYLE=datadog,tracecontext is set. This middleware extracts
the W3C traceparent/tracestate headers so that OTEL spans created by Laminar inside
the agent-server become children of the upstream trace, producing a single end-to-end
distributed trace in Datadog.

It also extracts W3C Baggage values (user_id, trigger, org_id, etc.) injected by the
OpenHands app and promotes them to span attributes for searchability in Datadog.
"""

from opentelemetry import (
    baggage as otel_baggage,
)
from opentelemetry import (
    context as otel_context,
)
from opentelemetry import (
    propagate,
    trace,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TraceContextMiddleware(BaseHTTPMiddleware):
    """Extract W3C Trace Context + Baggage from incoming requests."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract W3C traceparent, tracestate, and baggage from request headers.
        # propagate.extract() uses the globally configured propagators which
        # include W3C TraceContext and Baggage by default.
        ctx = propagate.extract(carrier=dict(request.headers))
        token = otel_context.attach(ctx)
        try:
            # Promote baggage values to span attributes so they're searchable
            # in Datadog (e.g. baggage.user_id, baggage.trigger).
            span = trace.get_current_span()
            if span and span.is_recording():
                for key, value in otel_baggage.get_all(ctx).items():
                    span.set_attribute(f'baggage.{key}', value)

            response = await call_next(request)
            return response
        finally:
            otel_context.detach(token)
