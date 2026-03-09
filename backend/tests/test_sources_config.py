"""Tests for SOURCES_CONFIG and DEFAULT_MODALIDADES in config.py."""

from config import SOURCES_CONFIG, DEFAULT_MODALIDADES


class TestSourcesConfig:
    """Tests for multi-source configuration (v2-story-1.0: TD-C03 dead code removal)."""

    def test_pncp_enabled_by_default(self):
        assert SOURCES_CONFIG["pncp"]["enabled"] is True

    def test_transparencia_enabled(self):
        assert SOURCES_CONFIG["transparencia"]["enabled"] is True

    def test_deprecated_sources_removed(self):
        """TD-C03: ComprasGov, Querido Diario, TCE-RJ removed from config."""
        assert "comprasgov" not in SOURCES_CONFIG
        assert "querido_diario" not in SOURCES_CONFIG
        assert "tce_rj" not in SOURCES_CONFIG

    def test_only_two_active_sources(self):
        """v2-story-1.0: Source registry lists exactly 2 active sources."""
        assert set(SOURCES_CONFIG.keys()) == {"pncp", "transparencia"}

    def test_all_sources_have_required_keys(self):
        required_keys = {"enabled", "base_url", "auth", "rate_limit_rps", "timeout", "priority"}
        for name, cfg in SOURCES_CONFIG.items():
            assert required_keys.issubset(cfg.keys()), f"{name} missing keys: {required_keys - cfg.keys()}"

    def test_pncp_base_url(self):
        assert "pncp.gov.br" in SOURCES_CONFIG["pncp"]["base_url"]

    def test_priorities_are_unique(self):
        priorities = [cfg["priority"] for cfg in SOURCES_CONFIG.values()]
        assert len(priorities) == len(set(priorities))

    def test_orchestrator_timeouts(self):
        """Timeouts must allow full source operations to complete."""
        assert SOURCES_CONFIG["pncp"]["timeout"] == 300
        assert SOURCES_CONFIG["transparencia"]["timeout"] == 90

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
