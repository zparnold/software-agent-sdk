# Multi-Language Runtime Examples

This directory contains examples demonstrating how to use different Docker image variants with various programming language runtimes.

## Prerequisites

1. Build or pull the appropriate Docker images:
   ```bash
   # Build JVM variant
   python openhands-agent-server/openhands/agent_server/docker/build.py \
     --dockerfile-variant jvm \
     --custom-tags latest-jvm \
     --load
   
   # Build Go variant
   python openhands-agent-server/openhands/agent_server/docker/build.py \
     --dockerfile-variant go \
     --custom-tags latest-go \
     --load
   
   # Build Full variant
   python openhands-agent-server/openhands/agent_server/docker/build.py \
     --dockerfile-variant full \
     --custom-tags latest-full \
     --load
   ```

2. Install the OpenHands SDK:
   ```bash
   pip install openhands-sdk
   ```

3. Set your LLM API key:
   ```bash
   export LLM_API_KEY=your_api_key_here
   ```

## Examples

### `multi_language_examples.py`

Demonstrates using different language runtime variants:

- **Java Project**: Uses JVM variant to create and run a Maven project
- **Go Project**: Uses Go variant to create a web server
- **Multi-Language Project**: Uses Full variant for a microservices architecture
- **Custom Java Version**: Shows how to use SDKMAN to switch Java versions

## Running the Examples

1. Edit `multi_language_examples.py` and uncomment the example you want to run
2. Run the script:
   ```bash
   python multi_language_examples.py
   ```

## Available Image Variants

| Variant | Tag | Pre-installed Languages |
|---------|-----|------------------------|
| Default | `latest` | Python 3.12, Node.js 22 |
| JVM | `latest-jvm` | Python, Node.js, Java 21, Maven, Gradle |
| Go | `latest-go` | Python, Node.js, Go 1.23.5 |
| Full | `latest-full` | Python, Node.js, Java, Go, Maven, Gradle |

## Documentation

For more information about language runtime support, see:
- [Language Runtime Documentation](../../../openhands-agent-server/openhands/agent_server/docker/LANGUAGE_RUNTIMES.md)
- [Main README](../../../README.md)
