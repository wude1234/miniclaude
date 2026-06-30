#!/usr/bin/env python3
"""Run v6 offline tests without requiring pytest."""

from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import test_v6_offline as tests


def main() -> None:
    tests.test_anthropic_stream_content_block_stop_marks_tool_ready()
    with tempfile.TemporaryDirectory() as tmp:
        tests.test_mcp_discovery_and_call(Path(tmp))
    tests.test_file_safety_session_and_compression()
    print("PASS v6 offline tests")


if __name__ == "__main__":
    main()
