from __future__ import annotations

from elenchus.domains import CodeDomain, MathDomain, ReadingDomain


def test_code_domain_reads_an_existing_file() -> None:
    domain = CodeDomain(files={"a.py": "print(1)\n"})
    assert domain.run_tool("read_file", {"path": "a.py"}) == "print(1)\n"


def test_code_domain_reports_missing_file_without_raising() -> None:
    domain = CodeDomain(files={"a.py": "print(1)\n"})
    result = domain.run_tool("read_file", {"path": "missing.py"})
    assert "no such file" in result
    assert "a.py" in result


def test_code_domain_lists_none_when_empty() -> None:
    domain = CodeDomain(files={})
    result = domain.run_tool("read_file", {"path": "anything.py"})
    assert "(none)" in result


def test_code_domain_exposes_one_tool() -> None:
    domain = CodeDomain(files={})
    names = [tool["name"] for tool in domain.tools()]
    assert names == ["read_file"]


def test_math_and_reading_domains_have_no_tools() -> None:
    assert MathDomain().tools() == []
    assert ReadingDomain().tools() == []


def test_math_and_reading_run_tool_reports_error_without_raising() -> None:
    assert "no tools" in MathDomain().run_tool("anything", {})
    assert "no tools" in ReadingDomain().run_tool("anything", {})


def test_domain_names() -> None:
    assert CodeDomain(files={}).name == "code"
    assert MathDomain().name == "math"
    assert ReadingDomain().name == "reading"


def test_framings_are_non_empty_and_distinct() -> None:
    framings = {
        CodeDomain(files={}).framing(),
        MathDomain().framing(),
        ReadingDomain().framing(),
    }
    assert len(framings) == 3
    assert all(framings)
