from src.agents.common import UNKNOWN, or_unknown, present


class TestPresent:
    def test_none_is_not_present(self):
        assert present(None) is False

    def test_empty_string_is_not_present(self):
        assert present("") is False

    def test_empty_list_is_not_present(self):
        assert present([]) is False

    def test_zero_is_present(self):
        assert present(0) is True

    def test_false_is_present(self):
        assert present(False) is True

    def test_nonempty_string_is_present(self):
        assert present("Dubai") is True


class TestOrUnknown:
    def test_missing_value_becomes_unknown(self):
        assert or_unknown(None) == UNKNOWN
        assert or_unknown("") == UNKNOWN
        assert or_unknown([]) == UNKNOWN

    def test_real_value_passes_through(self):
        assert or_unknown("Dubai") == "Dubai"
        assert or_unknown(0) == 0
