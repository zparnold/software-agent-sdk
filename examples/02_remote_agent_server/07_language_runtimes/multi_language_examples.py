"""
Example: Using Different Language Runtime Variants

This example demonstrates how to use different Docker image variants
to work with projects in different programming languages.
"""

from openhands.sdk import Agent, Conversation, LLM, Tool
from openhands.sdk.workspace import DockerDevWorkspace
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool


def example_java_project():
    """Work with a Java/Maven project using the JVM variant."""
    print("=== Java Project Example ===")

    # Use the JVM variant with Java, Maven, and Gradle pre-installed
    workspace = DockerDevWorkspace(
        base_image="ghcr.io/openhands/agent-server:latest-jvm",
        working_dir="/workspace",
    )

    llm = LLM(model="anthropic/claude-sonnet-4-5-20250929")

    agent = Agent(
        llm=llm,
        tools=[
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
        ],
    )

    conversation = Conversation(agent=agent, workspace=workspace)

    conversation.send_message(
        "Create a simple Java Maven project with a Hello World class. "
        "Then compile and run it using Maven."
    )
    conversation.run()


def example_go_project():
    """Work with a Go project using the Go variant."""
    print("=== Go Project Example ===")

    # Use the Go variant with Go toolchain pre-installed
    workspace = DockerDevWorkspace(
        base_image="ghcr.io/openhands/agent-server:latest-go",
        working_dir="/workspace",
    )

    llm = LLM(model="anthropic/claude-sonnet-4-5-20250929")

    agent = Agent(
        llm=llm,
        tools=[
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
        ],
    )

    conversation = Conversation(agent=agent, workspace=workspace)

    conversation.send_message(
        "Create a simple Go web server that responds with 'Hello, World!' "
        "on port 8080. Initialize go.mod and build the project."
    )
    conversation.run()


def example_multi_language_project():
    """Work with a multi-language project using the full variant."""
    print("=== Multi-Language Project Example ===")

    # Use the full variant with all language runtimes
    workspace = DockerDevWorkspace(
        base_image="ghcr.io/openhands/agent-server:latest-full",
        working_dir="/workspace",
    )

    llm = LLM(model="anthropic/claude-sonnet-4-5-20250929")

    agent = Agent(
        llm=llm,
        tools=[
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
        ],
    )

    conversation = Conversation(agent=agent, workspace=workspace)

    conversation.send_message(
        "Create a microservices project with:\n"
        "1. A Python Flask backend on port 5000\n"
        "2. A Go service for data processing\n"
        "3. A Java Spring Boot service for authentication\n"
        "4. A Node.js frontend using Express\n"
        "Create a README documenting how to run each service."
    )
    conversation.run()


def example_custom_java_version():
    """Use SDKMAN to switch Java versions on-demand."""
    print("=== Custom Java Version Example ===")

    workspace = DockerDevWorkspace(
        base_image="ghcr.io/openhands/agent-server:latest-jvm",
        working_dir="/workspace",
    )

    llm = LLM(model="anthropic/claude-sonnet-4-5-20250929")

    agent = Agent(
        llm=llm,
        tools=[
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
        ],
    )

    conversation = Conversation(agent=agent, workspace=workspace)

    conversation.send_message(
        "This project requires Java 17. Use SDKMAN to install Java 17, "
        "then create a simple Maven project and verify it compiles with Java 17."
    )
    conversation.run()


if __name__ == "__main__":
    # Uncomment the example you want to run
    # example_java_project()
    # example_go_project()
    # example_multi_language_project()
    # example_custom_java_version()
    print(
        "Examples defined. Uncomment one in the __main__ block to run it.\n"
        "Make sure you have the appropriate Docker images built or pulled."
    )
