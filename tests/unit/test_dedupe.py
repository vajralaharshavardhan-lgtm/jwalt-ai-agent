from src.memory.dedupe import normalize_company_name, normalize_domain, normalize_phone


class TestNormalizeCompanyName:
    def test_strips_legal_suffixes_and_case(self):
        assert normalize_company_name("ABC Hotels Group LLC") == "abc hotels"
        assert normalize_company_name("abc hotels") == "abc hotels"

    def test_strips_punctuation_and_collapses_whitespace(self):
        assert normalize_company_name("J-WALT, Interiors  Co.") == "j walt interiors"

    def test_empty_input(self):
        assert normalize_company_name("") == ""


class TestNormalizeDomain:
    def test_strips_protocol_and_www(self):
        assert normalize_domain("https://www.example.com/path?x=1") == "example.com"

    def test_bare_domain_passthrough(self):
        assert normalize_domain("example.com") == "example.com"

    def test_none_input(self):
        assert normalize_domain(None) is None


class TestNormalizePhone:
    def test_digits_only(self):
        assert normalize_phone("+971 4 123 4567") == "97141234567"

    def test_equivalent_formats_match(self):
        assert normalize_phone("+971-50-123-4567") == normalize_phone("+971 50 123 4567")

    def test_none_input(self):
        assert normalize_phone(None) is None


class TestDuplicateChecker:
    def test_finds_by_domain_first(self, store):
        c1, created = store.get_or_create_company(name="ABC Hotels Group LLC", domain="https://www.abchotels.com", source="test")
        assert created is True
        found = store.dedupe.find_existing_company(domain="abchotels.com", name="A totally different name")
        assert found is not None
        assert found.id == c1.id

    def test_finds_by_normalized_name_when_no_domain_match(self, store):
        c1, _ = store.get_or_create_company(name="ABC Hotels Group LLC", domain=None, source="test")
        found = store.dedupe.find_existing_company(domain="unrelated-domain.com", name="ABC Hotels")
        assert found is not None
        assert found.id == c1.id

    def test_no_match_returns_none(self, store):
        store.get_or_create_company(name="ABC Hotels", domain="abchotels.com", source="test")
        found = store.dedupe.find_existing_company(domain="xyz.com", name="XYZ Corp")
        assert found is None

    def test_contact_dedupe_by_email_case_insensitive(self, store):
        company, _ = store.get_or_create_company(name="ABC Hotels", domain="abchotels.com", source="test")
        contact = store.contacts.create(company_id=company.id, full_name="John Smith", email="John.Smith@ABCHotels.com", source="test")
        found = store.dedupe.find_existing_contact(email="john.smith@abchotels.com", phone=None)
        assert found is not None
        assert found.id == contact.id

    def test_contact_dedupe_by_phone(self, store):
        company, _ = store.get_or_create_company(name="ABC Hotels", domain="abchotels.com", source="test")
        contact = store.contacts.create(company_id=company.id, full_name="John Smith", phone="+971 50 123 4567", source="test")
        found = store.dedupe.find_existing_contact(email=None, phone="00971501234567")
        assert found is not None
        assert found.id == contact.id
