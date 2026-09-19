from src.orchestrator import actions as A
from src.reporting.report import ReportGenerator


class TestReportGenerator:
    def test_tallies_from_run_logs(self, store):
        run_id = "r1"
        store.run_logs.log(run_id=run_id, agent="research_agent", action=A.RESEARCH_COMPANIES, status="SUCCESS", output_summary="3")
        store.run_logs.log(run_id=run_id, agent="orchestrator", action=A.DUPLICATE_DETECTED, status="SUCCESS")
        store.run_logs.log(run_id=run_id, agent="contact_agent", action=A.CONTACT_FOUND, status="SUCCESS")
        store.run_logs.log(run_id=run_id, agent="qualification_agent", action=A.LEAD_QUALIFIED, status="SUCCESS", output_summary="HOT")
        store.run_logs.log(run_id=run_id, agent="qualification_agent", action=A.LEAD_QUALIFIED, status="SUCCESS", output_summary="COLD")
        store.run_logs.log(run_id=run_id, agent="outreach_agent", action=A.DRAFT_CREATED, status="SUCCESS")
        store.run_logs.log(run_id=run_id, agent="approval_gate", action=A.APPROVAL_DECISION, status="SUCCESS", output_summary="APPROVED")
        store.run_logs.log(run_id=run_id, agent="research_agent", action="search_companies", status="ERROR", error_message="Apollo timeout")
        # entry from a different run must not leak into this report
        store.run_logs.log(run_id="other-run", agent="x", action=A.LEAD_QUALIFIED, status="SUCCESS", output_summary="HOT")

        report = ReportGenerator(store).generate(run_id)

        assert report.leads_researched == 3
        assert report.duplicates_skipped == 1
        assert report.contacts_found == 1
        assert report.qualified_by_classification == {"HOT": 1, "COLD": 1}
        assert report.drafts_created == 1
        assert report.approvals_approved == 1
        assert report.actions_awaiting_approval == 0
        assert len(report.errors) == 1
        assert "Apollo timeout" in report.errors[0]

    def test_empty_run_produces_zeroed_report(self, store):
        report = ReportGenerator(store).generate("nonexistent-run")
        assert report.leads_researched == 0
        assert report.errors == []
        text = report.as_text()
        assert "nonexistent-run" in text
