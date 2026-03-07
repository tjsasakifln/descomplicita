"""Tests for SOURCES_CONFIG and DEFAULT_MODALIDADES in config.py."""

from config import SOURCES_CONFIG, DEFAULT_MODALIDADES


class TestSourcesConfig:
    """Tests for multi-source configuration."""

    def test_pncp_enabled_by_default(self):
        assert SOURCES_CONFIG["pncp"]["enabled"] is True

    def test_non_implemented_sources_disabled(self):
        """Sources not yet implemented should remain disabled."""
        implemented = {"pncp", "comprasgov", "transparencia", "querido_diario", "tce_rj"}
        for name, cfg in SOURCES_CONFIG.items():
            if name not in implemented:
                assert cfg["enabled"] is False, f"{name} should be disabled"

    def test_deprecated_sources_disabled(self):
        """Sources with deprecated/broken endpoints must be disabled."""
        deprecated = {
            "comprasgov": "SR-001.3",
            "querido_diario": "SR-001.4",
            "tce_rj": "SR-001.5",
        }
        for name, story in deprecated.items():
            assert SOURCES_CONFIG[name]["enabled"] is False, (
                f"{name} should be disabled per {story}"
            )

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
        expected = {"pncp", "comprasgov", "transparencia", "querido_diario", "tce_rj"}
        assert expected == set(SOURCES_CONFIG.keys())

    def test_orchestrator_timeouts(self):
        """SR-001.1: Timeouts must allow full source operations to complete."""
        assert SOURCES_CONFIG["pncp"]["timeout"] == 120
        assert SOURCES_CONFIG["comprasgov"]["timeout"] == 60
        assert SOURCES_CONFIG["transparencia"]["timeout"] == 90
        assert SOURCES_CONFIG["querido_diario"]["timeout"] == 60
        assert SOURCES_CONFIG["tce_rj"]["timeout"] == 90

    def test_default_modalidades_contains_expected(self):
        """SE-001.3: DEFAULT_MODALIDADES must include all 7 modalities."""
        expected = [4, 5, 6, 7, 8, 13, 15]
        assert DEFAULT_MODALIDADES == expected

    def test_default_modalidades_includes_ata_registro(self):
        """SE-001.3: Modalidade 13 (Leilão Presencial / Ata Registro) must be present."""
        assert 13 in DEFAULT_MODALIDADES

    def test_default_modalidades_includes_chamada_publica(self):
        """SE-001.3: Modalidade 15 (Chamada pública) must be present."""
        assert 15 in DEFAULT_MODALIDADES

    def test_timeouts_are_positive_integers(self):
        for name, cfg in SOURCES_CONFIG.items():
            assert isinstance(cfg["timeout"], int), f"{name} timeout must be int"
            assert cfg["timeout"] > 0, f"{name} timeout must be positive"
