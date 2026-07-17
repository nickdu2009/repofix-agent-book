from repofix_agent.schemas import TOOL_SCHEMAS


def test_all_tool_schemas_are_strict_and_closed() -> None:
    assert {schema["name"] for schema in TOOL_SCHEMAS} == {
        "list_files",
        "read_file",
        "search_code",
        "write_file",
        "run_tests",
        "finish",
    }
    for schema in TOOL_SCHEMAS:
        parameters = schema["parameters"]
        assert schema["strict"] is True
        assert parameters["additionalProperties"] is False
        assert set(parameters["required"]) == set(parameters["properties"])
