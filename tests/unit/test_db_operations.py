class TestCompanyRepository:
    def test_create_and_get(self, store):
        company = store.companies.create(name="ABC Hotels", domain="abchotels.com", industry="hospitality", source="test")
        assert company.id is not None
        fetched = store.companies.get(company.id)
        assert fetched.name == "ABC Hotels"
        assert fetched.normalized_name == "abc hotels"

    def test_update_does_not_clobber_with_blank(self, store):
        company = store.companies.create(name="ABC Hotels", domain="abchotels.com", industry="hospitality", source="test")
        updated = store.companies.update(company.id, industry=None, city="Dubai")
        assert updated.industry == "hospitality"  # unchanged
        assert updated.city == "Dubai"  # new field applied

    def test_search_by_industry(self, store):
        store.companies.create(name="ABC Hotels", domain="a.com", industry="hospitality", source="test")
        store.companies.create(name="XYZ Software", domain="x.com", industry="software", source="test")
        results = store.companies.search(industry="hospitality")
        assert len(results) == 1
        assert results[0].name == "ABC Hotels"


class TestContactRepository:
    def test_create_and_list_for_company(self, store):
        company = store.companies.create(name="ABC Hotels", domain="abchotels.com", source="test")
        store.contacts.create(company_id=company.id, full_name="John Smith", email="john@abchotels.com", source="test")
        store.contacts.create(company_id=company.id, full_name="Jane Doe", email="jane@abchotels.com", source="test")
        contacts = store.contacts.list_for_company(company.id)
        assert len(contacts) == 2


class TestLeadRepository:
    def test_create_update_search(self, store):
        company = store.companies.create(name="ABC Hotels", domain="abchotels.com", source="test")
        lead = store.leads.create(company_id=company.id, classification="WARM", score=60)
        assert lead.status == "NEW"

        updated = store.leads.update(lead.id, status="QUALIFIED", classification="HOT", score=85)
        assert updated.classification == "HOT"
        assert updated.score == 85

        hot_leads = store.leads.search(classification="HOT")
        assert len(hot_leads) == 1
        assert hot_leads[0].id == lead.id

        none_found = store.leads.search(classification="COLD")
        assert len(none_found) == 0

    def test_get_for_company_returns_most_recent(self, store):
        company = store.companies.create(name="ABC Hotels", domain="abchotels.com", source="test")
        store.leads.create(company_id=company.id, classification="COLD", score=30)
        second = store.leads.create(company_id=company.id, classification="HOT", score=90)
        latest = store.leads.get_for_company(company.id)
        assert latest.id == second.id


class TestOutreachRepository:
    def test_create_and_update_status(self, store):
        company = store.companies.create(name="ABC Hotels", domain="abchotels.com", source="test")
        lead = store.leads.create(company_id=company.id)
        event = store.outreach.create(lead_id=lead.id, contact_id=None, event_type="DRAFT_CREATED", subject="Hi", body="...")
        assert event.status == "DRAFT"
        updated = store.outreach.update_status(event.id, "APPROVED")
        assert updated.status == "APPROVED"


class TestRunLogRepository:
    def test_log_and_list_for_run(self, store):
        store.run_logs.log(run_id="r1", agent="test", action="do_thing", status="SUCCESS")
        store.run_logs.log(run_id="r1", agent="test", action="do_other", status="ERROR", error_message="boom")
        store.run_logs.log(run_id="r2", agent="test", action="unrelated", status="SUCCESS")

        r1_entries = store.run_logs.list_for_run("r1")
        assert len(r1_entries) == 2
        assert r1_entries[1].error_message == "boom"
