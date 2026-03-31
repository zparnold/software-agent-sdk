"""Test that maybe_init_laminar sets the correct OTEL service.name.

Regression test for the bug where Laminar's TracerManager.init captured
sys.argv[0] at *import time* (the binary path, e.g.
/usr/local/bin/openhands-agent-server) and ignored the OTEL_SERVICE_NAME
env var.
"""

import subprocess
import sys
import textwrap


def test_service_name_uses_otel_env_var_not_argv():
    """service.name should come from OTEL_SERVICE_NAME, not sys.argv[0].

    Run in a subprocess to get a clean Python interpreter — OTEL and Laminar
    are singleton-heavy and impossible to reset reliably in-process.
    """
    script = textwrap.dedent("""\
        import os, sys

        # Simulate the container: argv[0] is the installed console-script path
        sys.argv[0] = "/usr/local/bin/openhands-agent-server"

        os.environ["OTEL_SERVICE_NAME"] = "openhands-agent-server"
        os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = "http://localhost:4317"

        from openhands.sdk.observability.laminar import maybe_init_laminar
        maybe_init_laminar()

        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider as SdkTracerProvider
        from opentelemetry.sdk.resources import SERVICE_NAME

        provider = trace.get_tracer_provider()
        assert isinstance(provider, SdkTracerProvider), (
            f"Expected SdkTracerProvider, got {type(provider)}"
        )
        service = provider.resource.attributes.get(SERVICE_NAME)
        assert service == "openhands-agent-server", (
            f"Expected 'openhands-agent-server', got '{service}'"
        )
        # Must NOT contain the binary path
        assert "/usr/local/bin" not in str(service), (
            f"service.name leaked binary path: {service}"
        )
        print("OK")
    """)
    result = subprocess.run(
        [sys.executable, '-c', script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f'Subprocess failed:\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )
    assert 'OK' in result.stdout


def test_custom_service_name():
    """A non-default OTEL_SERVICE_NAME should be respected."""
    script = textwrap.dedent("""\
        import os, sys

        sys.argv[0] = "/usr/local/bin/openhands-agent-server"
        os.environ["OTEL_SERVICE_NAME"] = "my-custom-service"
        os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = "http://localhost:4317"

        from openhands.sdk.observability.laminar import maybe_init_laminar
        maybe_init_laminar()

        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider as SdkTracerProvider
        from opentelemetry.sdk.resources import SERVICE_NAME

        provider = trace.get_tracer_provider()
        assert isinstance(provider, SdkTracerProvider)
        service = provider.resource.attributes.get(SERVICE_NAME)
        assert service == "my-custom-service", (
            f"Expected 'my-custom-service', got '{service}'"
        )
        print("OK")
    """)
    result = subprocess.run(
        [sys.executable, '-c', script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f'Subprocess failed:\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )
    assert 'OK' in result.stdout
