"""Tests for the --apollo-smoke-test / --anthropic-smoke-test CLI paths.
The underlying client methods are monkeypatched so these never touch the
network -- they verify the CLI wiring (missing-key handling, success/error
reporting, that credit-worthy calls actually happen), not live connectivity.
"""
import src.main as main_module
from src.tools.apollo_client import ApolloAuthError


class TestApolloSmokeTest:
    def test_missing_key_returns_error_without_calling_apollo(self, monkeypatch, capsys):
        monkeypatch.delenv("APOLLO_API_KEY", raising=False)
        exit_code = main_module._apollo_smoke_test()
        assert exit_code == 1
        assert "APOLLO_API_KEY is not set" in capsys.readouterr().err

    def test_successful_call_reports_success_and_never_prints_the_key(self, monkeypatch, capsys):
        monkeypatch.setenv("APOLLO_API_KEY", "super-secret-test-key")
        monkeypatch.setattr(
            "src.tools.apollo_client.ApolloClient.enrich_organization",
            lambda self, domain: {"name": "Apollo.io", "industry": "software"},
        )
        exit_code = main_module._apollo_smoke_test()
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "SUCCESS" in out
        assert "Apollo.io" in out
        assert "super-secret-test-key" not in out

    def test_no_match_is_not_treated_as_failure(self, monkeypatch, capsys):
        monkeypatch.setenv("APOLLO_API_KEY", "test-key")
        monkeypatch.setattr(
            "src.tools.apollo_client.ApolloClient.enrich_organization", lambda self, domain: None
        )
        exit_code = main_module._apollo_smoke_test()
        assert exit_code == 0
        assert "no match" in capsys.readouterr().out.lower()

    def test_auth_error_is_reported_and_never_fabricates_a_result(self, monkeypatch, capsys):
        monkeypatch.setenv("APOLLO_API_KEY", "wrong-key")

        def raise_auth_error(self, domain):
            raise ApolloAuthError("Apollo rejected the API key (401)")

        monkeypatch.setattr("src.tools.apollo_client.ApolloClient.enrich_organization", raise_auth_error)
        exit_code = main_module._apollo_smoke_test()
        err = capsys.readouterr().err
        assert exit_code == 1
        assert "401" in err or "rejected" in err.lower()


class TestAnthropicSmokeTest:
    def test_missing_key_returns_error_without_calling_anthropic(self, monkeypatch, capsys):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        exit_code = main_module._anthropic_smoke_test()
        assert exit_code == 1
        assert "ANTHROPIC_API_KEY is not set" in capsys.readouterr().err

    def test_successful_call_reports_success_and_never_prints_the_key(self, monkeypatch, capsys):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "super-secret-anthropic-key")
        monkeypatch.setattr(
            "src.tools.llm_client.AnthropicLLMClient.complete",
            lambda self, *, system, user, max_tokens=1024: "OK",
        )
        exit_code = main_module._anthropic_smoke_test()
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "SUCCESS" in out
        assert "super-secret-anthropic-key" not in out

    def test_api_error_is_reported_not_swallowed(self, monkeypatch, capsys):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "bad-key")

        def raise_error(self, *, system, user, max_tokens=1024):
            raise RuntimeError("authentication_error: invalid x-api-key")

        monkeypatch.setattr("src.tools.llm_client.AnthropicLLMClient.complete", raise_error)
        exit_code = main_module._anthropic_smoke_test()
        err = capsys.readouterr().err
        assert exit_code == 1
        assert "authentication_error" in err
