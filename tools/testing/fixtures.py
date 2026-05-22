"""Test fixtures — mirrors src/tools/testing/fixtures.ts"""
TOOL_USE_FIXTURES = [
    {
        "type": "tool_use",
        "id": "toolu_01",
        "name": "Bash",
        "input": {"command": "echo hello"},
    },
    {
        "type": "tool_use",
        "id": "toolu_02",
        "name": "Read",
        "input": {"file_path": "/tmp/test.txt"},
    },
]

BASH_FIXTURES = [
    {"command": "echo hello", "expected_exit": 0, "expected_stdout": "hello\n"},
    {"command": "ls /nonexistent", "expected_exit": 2, "expected_stdout": ""},
    {"command": "grep pattern /dev/null", "expected_exit": 1, "expected_stdout": ""},
]
