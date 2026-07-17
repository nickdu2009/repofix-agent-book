"""Strict function schemas and the small runtime validator used by the core."""

from __future__ import annotations

from typing import Any

from .errors import ModelProtocolError


def _string_parameters(properties: dict[str, str]) -> dict[str, Any]:
    schema_properties = {
        name: {"type": "string", "description": description}
        for name, description in properties.items()
    }
    return {
        "type": "object",
        "properties": schema_properties,
        "required": list(schema_properties),
        "additionalProperties": False,
    }


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "list_files",
        "description": "List regular files under a workspace-relative directory.",
        "parameters": _string_parameters(
            {"path": "Workspace-relative directory; use . for the repository root."}
        ),
        "strict": True,
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read one UTF-8 text file inside the workspace.",
        "parameters": _string_parameters({"path": "Workspace-relative file path."}),
        "strict": True,
    },
    {
        "type": "function",
        "name": "search_code",
        "description": "Search UTF-8 source files for a literal query.",
        "parameters": _string_parameters(
            {
                "query": "Literal text to search for.",
                "path": "Workspace-relative directory; use . for the repository root.",
            }
        ),
        "strict": True,
    },
    {
        "type": "function",
        "name": "write_file",
        "description": "Atomically replace one UTF-8 text file inside the workspace.",
        "parameters": _string_parameters(
            {
                "path": "Workspace-relative file path.",
                "content": "Complete replacement content encoded as UTF-8.",
            }
        ),
        "strict": True,
    },
    {
        "type": "function",
        "name": "run_tests",
        "description": "Run the preconfigured test target inside the isolated sandbox.",
        "parameters": _string_parameters(
            {"target": "Named test target configured by the control plane, such as unit."}
        ),
        "strict": True,
    },
    {
        "type": "function",
        "name": "finish",
        "description": "Request completion after the current workspace revision passes tests.",
        "parameters": _string_parameters({"summary": "Concise explanation of the verified fix."}),
        "strict": True,
    },
]

_SCHEMAS_BY_NAME = {schema["name"]: schema for schema in TOOL_SCHEMAS}


def validate_tool_arguments(name: str, arguments: object) -> dict[str, Any]:
    """Validate the strict string-only schemas again at the trust boundary."""

    schema = _SCHEMAS_BY_NAME.get(name)
    if schema is None:
        raise ModelProtocolError(f"unknown tool: {name}")
    if not isinstance(arguments, dict):
        raise ModelProtocolError(f"arguments for {name} must be a JSON object")

    parameters = schema["parameters"]
    expected = set(parameters["properties"])
    actual = set(arguments)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ModelProtocolError(
            f"invalid arguments for {name}: missing={missing}, extra={extra}"
        )
    for key, value in arguments.items():
        if not isinstance(value, str):
            raise ModelProtocolError(f"argument {name}.{key} must be a string")
    return arguments
