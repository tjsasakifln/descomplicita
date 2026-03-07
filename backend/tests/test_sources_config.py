"""Tests for SOURCES_CONFIG in config.py."""

from config import SOURCES_CONFIG


class TestSourcesConfig:
    """Tests for multi-source configuration."""

    def test_pncp_enabled_by_default(self):
        assert SOURCES_CONFIG["pncp"]["enabled"] is True

    def test_non_implemented_sources_disabled(self):
        """Sources not yet implemented should remain disabled."""
        implemented = {"pncp", "comprasgov"}
        for name, cfg in SOURCES_CONFIG.items():
            if name not in implemented:
                assert cfg["enabled"] is False, f"{name} should be disabled"

    def test_all_sources_have_required_keys(self):
        required_keys = {"enabled", "base_url", "auth", "rate_limit_rps", "timeout", "priority"}
        for name, cfg in SOURCES_CONFIG.items():
            assert required_keys.issubset(cfg.keys()), f"{name} missing keys: {required_keys - cfg.keys()}"

    def test_pncp_base_url(self):
        assert "pncp.gov.br" in SOURCES_CONFIG["pncp"]["base_url"]

    def test_priorities_are_unique(self):
        priorities = [cfg["priority"] for cfg in SOURCES_CONFIG.values()]
        assert len(priorities) == len(set(priorities))

    def test_expected_sources_present(self):
        expected = {"pncp", "comprasgov", "portal_transparencia", "querido_diario", "tce_rj"}
        assert expected == set(SOURCES_CONFIG.keys())
