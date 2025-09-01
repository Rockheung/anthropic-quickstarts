# Anthropic Quickstarts - Computer-Use Demo

## Overview

This repository provides a reference implementation for computer use with Claude, featuring:

- Docker container setup with all necessary dependencies
- Computer use agent loop using Anthropic API, Bedrock, or Vertex
- Anthropic-defined computer use tools
- Streamlit app for interacting with the agent loop

### Project Structure

```
computer-use-demo/
├── .gitignore
├── CONTRIBUTING.md
├── Dockerfile
├── LICENSE
├── README.md
├── pyproject.toml
├── ruff.toml
├── setup.sh
├── dev-requirements.txt
├── computer_use_demo/
│   ├── __init__.py
│   ├── loop.py
│   ├── streamlit.py
│   ├── requirements.txt
│   └── tools/
├── image/
│   ├── entrypoint.sh
│   ├── http_server.py
│   ├── start_all.sh
│   └── static_content/
└── tests/
    ├── conftest.py
    ├── loop_test.py
    ├── streamlit_test.py
    └── tools/
```

## Setup & Development

- **Setup environment**: `./setup.sh`
- **Build Docker**: `docker build . -t computer-use-demo:local`
- **Run container**: `docker run -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY -v $(pwd)/computer_use_demo:/home/computeruse/computer_use_demo/ -v $HOME/.anthropic:/home/computeruse/.anthropic -p 5900:5900 -p 8501:8501 -p 6080:6080 -p 8080:8080 -it computer-use-demo:local`

## Testing & Code Quality

- **Lint**: `ruff check .`
- **Format**: `ruff format .`
- **Typecheck**: `pyright`
- **Run tests**: `pytest`
- **Run single test**: `pytest tests/path_to_test.py::test_name -v`

## Code Style

- **Python**: snake_case for functions/variables, PascalCase for classes
- **Imports**: Use isort with combine-as-imports
- **Error handling**: Use custom ToolError for tool errors
- **Types**: Add type annotations for all parameters and returns
- **Classes**: Use dataclasses and abstract base classes

## Development Process

1. Fork the repository and create a branch for your changes
2. Make your changes following our coding standards
3. Submit a pull request with a clear description of the changes

## Tool Development Guidelines

When creating new tools:

1. Inherit from `BaseAnthropicTool`
2. Implement `__call__` and `to_params` methods
3. Use appropriate result types (`ToolResult`, `CLIResult`, or `ToolFailure`)
4. Add comprehensive tests
5. Document parameters and return types

## Important Notes

- Computer use is a beta feature with unique risks
- Use dedicated virtual machines or containers with minimal privileges
- Limit internet access to reduce exposure to malicious content
- The Beta API used in this reference implementation is subject to change
- Components are weakly separated and can only be used by one session at a time
