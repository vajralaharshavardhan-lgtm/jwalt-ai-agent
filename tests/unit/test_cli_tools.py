"""Tests for src/cli_tools.py. Uses a temp DB path and a temp run-id marker
file so these never touch the real data/leads.db or data/.current_run_id.
"""
import json

import pytest

import src.cli_tools as cli_tools


@pytest.fixture(autouse=True)
def isolate_filesystem(tmp_path, monkeypatch):
    monkeypatch.setenv("JWALT_DB_PATH", str(tmp_path / "test_leads.db"))
    monkeypatch.setattr(cli_tools, "RUN_ID_MARKER", tmp_path / ".current_run_id")


def run_main(monkeypatch, argv):
    monkeypatch.setattr("sys.argv", ["cli_tools"] + argv)
    return cli_tools.main()


class TestListTools:
    def test_excludes_api_mode_only_tools_and_includes_cc_tools(self, monkeypatch, capsys):
        exit_code = run_main(monkeypatch, ["list-tools"])
        assert exit_code == 0
        schemas = json.loads(capsys.readouterr().out)
        names = {s["name"] for s in schemas}
        for forbidden in cli_tools.API_MODE_ONLY:
            assert forbidden not in names
        for expected in ("check_duplicate", "qualify_lead", "store_lead", "generate_report", "finish"):
            assert expected in names
        for expected in ("cc_extract_evidence", "cc_submit_outreach_draft", "cc_request_approval", "cc_record_approval_decision"):
            assert expected in names


class TestNewRun:
    def test_creates_and_persists_a_run_id(self, monkeypatch, capsys):
        exit_code = run_main(monkeypatch, ["new-run"])
        assert exit_code == 0
        run_id = capsys.readouterr().out.strip()
        assert run_id.startswith("ccrun-")
        assert cli_tools.RUN_ID_MARKER.read_text().strip() == run_id

    def test_call_without_new_run_reuses_existing_marker(self, monkeypatch, capsys):
        run_main(monkeypatch, ["new-run"])
        first_run_id = capsys.readouterr().out.strip()

        run_main(monkeypatch, ["call", "generate_report", "{}"])
        second_output = json.loads(capsys.readouterr().out)
        assert second_output["run_id"] == first_run_id


class TestCallDispatch:
    def test_api_mode_only_tool_gives_clear_guidance_not_a_crash(self, monkeypatch, capsys):
        exit_code = run_main(monkeypatch, ["call", "search_companies", '{"target_count": 1}'])
        assert exit_code == 1
        err = json.loads(capsys.readouterr().err)
        assert "API-mode only" in err["error"]

    def test_unknown_tool(self, monkeypatch, capsys):
        exit_code = run_main(monkeypatch, ["call", "not_a_real_tool", "{}"])
        assert exit_code == 1
        err = json.loads(capsys.readouterr().err)
        assert "Unknown tool" in err["error"]

    def test_invalid_json_args(self, monkeypatch, capsys):
        exit_code = run_main(monkeypatch, ["call", "generate_report", "{not valid json"])
        assert exit_code == 1
        err = json.loads(capsys.readouterr().err)
        assert "invalid JSON" in err["error"]

    def test_full_pipeline_through_cli(self, monkeypatch, capsys):
        company = {
            "name": "Palm Grove Hospitality Group", "domain": "palmgrovehospitality.ae",
            "industry": "hospitality", "employee_count": 620, "city": "Dubai",
            "country": "United Arab Emirates", "apollo_org_id": "org_1",
            "description": "Hotel group with a new opening in Dubai Marina.",
        }

        run_main(monkeypatch, ["call", "cc_extract_evidence", json.dumps({"description": company["description"], "keywords": []})])
        evidence = json.loads(capsys.readouterr().out)["result"]["evidence"]
        company["evidence"] = evidence

        run_main(monkeypatch, ["call", "check_duplicate", json.dumps({"company_name": company["name"], "domain": company["domain"]})])
        dup = json.loads(capsys.readouterr().out)["result"]
        assert dup["is_duplicate"] is False

        run_main(monkeypatch, ["call", "qualify_lead", json.dumps({"company": company, "has_decision_maker": False})])
        qualification = json.loads(capsys.readouterr().out)["result"]

        run_main(monkeypatch, ["call", "store_lead", json.dumps({"company": company, "qualification": qualification})])
        stored = json.loads(capsys.readouterr().out)["result"]
        assert stored["company_was_new"] is True

        run_main(monkeypatch, ["call", "generate_report", "{}"])
        report = json.loads(capsys.readouterr().out)["result"]["report_text"]
        assert "Companies researched" in report

    def test_errors_are_logged_to_run_logs(self, monkeypatch, capsys):
        run_main(monkeypatch, ["call", "qualify_lead", "{}"])  # missing required "company" key
        capsys.readouterr()

        run_main(monkeypatch, ["call", "generate_report", "{}"])
        report = json.loads(capsys.readouterr().out)["result"]["report_text"]
        assert "Errors (1)" in report
