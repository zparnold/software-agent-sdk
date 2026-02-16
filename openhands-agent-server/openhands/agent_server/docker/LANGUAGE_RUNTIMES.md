# Multi-Language Runtime Support for OpenHands Agent Server

The OpenHands Agent Server now supports multiple Docker image variants with different language runtime stacks, allowing you to work with projects in various programming languages beyond the default Python and Node.js.

## Available Variants

### 1. Default (Python + Node.js)
**Dockerfile:** `Dockerfile` (default)  
**Pre-installed:**
- Python 3.12
- Node.js 22
- Git, Docker, GitHub CLI, build-essential
- UV (Python package manager)

**Use case:** Python and JavaScript/TypeScript projects

**Build command:**
```bash
python openhands-agent-server/openhands/agent_server/docker/build.py \
  --target binary \
  --custom-tags latest
```

### 2. JVM Variant (Java + Maven + Gradle)
**Dockerfile:** `Dockerfile.jvm`  
**Additional pre-installed:**
- OpenJDK 21 (LTS)
- Maven (via SDKMAN)
- Gradle (via SDKMAN)
- SDKMAN for Java version management

**Use case:** Java, Kotlin, Scala, and other JVM language projects

**Build command:**
```bash
python openhands-agent-server/openhands/agent_server/docker/build.py \
  --dockerfile-variant jvm \
  --target binary \
  --custom-tags jvm,latest-jvm
```

**Example usage:**
```python
from openhands.sdk.workspace import DockerDevWorkspace

# Use the JVM variant
workspace = DockerDevWorkspace(
    base_image="ghcr.io/openhands/agent-server:latest-jvm"
)
```

### 3. Go Variant
**Dockerfile:** `Dockerfile.go`  
**Additional pre-installed:**
- Go 1.23.5
- goenv for Go version management

**Use case:** Go projects

**Build command:**
```bash
python openhands-agent-server/openhands/agent_server/docker/build.py \
  --dockerfile-variant go \
  --target binary \
  --custom-tags go,latest-go
```

**Example usage:**
```python
from openhands.sdk.workspace import DockerDevWorkspace

# Use the Go variant
workspace = DockerDevWorkspace(
    base_image="ghcr.io/openhands/agent-server:latest-go"
)
```

### 4. Full Variant (All Language Runtimes)
**Dockerfile:** `Dockerfile.full`  
**Additional pre-installed:**
- All runtimes from JVM and Go variants
- OpenJDK 21 + Maven + Gradle (via SDKMAN)
- Go 1.23.5 + goenv

**Use case:** Multi-language projects or when you're not sure which runtime you need

**Build command:**
```bash
python openhands-agent-server/openhands/agent_server/docker/build.py \
  --dockerfile-variant full \
  --target binary \
  --custom-tags full,latest-full
```

**Example usage:**
```python
from openhands.sdk.workspace import DockerDevWorkspace

# Use the full variant with all language runtimes
workspace = DockerDevWorkspace(
    base_image="ghcr.io/openhands/agent-server:latest-full"
)
```

## Version Management

Each variant includes version managers that allow you to install and switch between different language versions on-demand:

### Java (JVM and Full variants)
Uses [SDKMAN](https://sdkman.io/) for managing Java, Maven, and Gradle versions.

**Example commands:**
```bash
# List available Java versions
sdk list java

# Install a specific Java version
sdk install java 17.0.9-tem

# Switch to a different version
sdk use java 17.0.9-tem

# Install different Maven version
sdk install maven 3.9.6
```

### Go (Go and Full variants)
Uses [goenv](https://github.com/syndbg/goenv) for managing Go versions.

**Example commands:**
```bash
# List available Go versions
goenv install --list

# Install a specific Go version
goenv install 1.21.5

# Set global Go version
goenv global 1.21.5

# Set local Go version (for current directory)
goenv local 1.22.0
```

## Image Size Comparison

| Variant | Approximate Size | Build Time |
|---------|-----------------|------------|
| Default | ~2.5 GB | ~5 min |
| JVM | ~3.2 GB | ~7 min |
| Go | ~2.8 GB | ~6 min |
| Full | ~3.5 GB | ~8 min |

*Sizes and times are approximate and may vary based on platform and cache status.*

## Choosing the Right Variant

- **Default**: Start here for Python/Node.js projects
- **JVM**: Choose this for Java, Kotlin, Scala, or any JVM-based project
- **Go**: Choose this for Go projects
- **Full**: Use when working with multiple languages or if you're unsure

You can always switch to a different variant by changing the `base_image` parameter.

## Building Custom Variants

You can also create your own custom Dockerfile variants by:

1. Creating a new `Dockerfile.<variant>` in `openhands-agent-server/openhands/agent_server/docker/`
2. Building with `--dockerfile-variant <variant>`

Example custom variant for Rust:
```dockerfile
# Dockerfile.rust
# Start with the default base
ARG BASE_IMAGE=nikolaik/python-nodejs:python3.12-nodejs22
FROM ${BASE_IMAGE} AS base-image-minimal

# Install Rust
USER root
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# ... rest of the Dockerfile structure ...
```

Build command:
```bash
python openhands-agent-server/openhands/agent_server/docker/build.py \
  --dockerfile-variant rust \
  --target binary \
  --custom-tags rust
```

## Advanced Configuration

### Environment Variables

You can configure the build using environment variables:

```bash
export DOCKERFILE_VARIANT=jvm
export CUSTOM_TAGS=my-jvm-variant
export TARGET=binary
export PLATFORMS=linux/amd64,linux/arm64

python openhands-agent-server/openhands/agent_server/docker/build.py
```

### Multi-Platform Builds

Build for multiple architectures:

```bash
python openhands-agent-server/openhands/agent_server/docker/build.py \
  --dockerfile-variant jvm \
  --platforms linux/amd64,linux/arm64 \
  --push \
  --custom-tags jvm
```

## Troubleshooting

### Out of Memory During Build
If you encounter out-of-memory errors during build, try:
- Building one platform at a time
- Increasing Docker's memory limit
- Using `--target binary-minimal` for a lighter build

### Version Manager Not Available
If SDKMAN or goenv commands aren't available in your session:

For SDKMAN:
```bash
source ~/.sdkman/bin/sdkman-init.sh
```

For goenv:
```bash
eval "$(goenv init -)"
```

These are already added to `~/.bashrc` and should be available in interactive shells.

## Migration Guide

### From Custom Base Images

If you were previously using custom base images for Java or Go support:

**Before:**
```python
workspace = DockerDevWorkspace(
    base_image="my-custom-java-image:latest"
)
```

**After:**
```python
workspace = DockerDevWorkspace(
    base_image="ghcr.io/openhands/agent-server:latest-jvm"
)
```

### From Manual Installation

If your agents were installing language runtimes at runtime:

**Before:**
```python
# Agent had to run these commands every time
agent.execute("sudo apt-get install -y openjdk-21-jdk")
agent.execute("curl -s https://get.sdkman.io | bash")
```

**After:**
```python
# Just use the appropriate variant - everything is pre-installed
workspace = DockerDevWorkspace(
    base_image="ghcr.io/openhands/agent-server:latest-jvm"
)
```

## Contributing

To add support for additional languages:

1. Create a new `Dockerfile.<variant>` based on the existing structure
2. Follow the pattern of minimal and full base image stages
3. Include version managers where appropriate
4. Document the new variant in this README
5. Submit a pull request

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for more details.
