"""Tests for modular import structure (story-2.1: main.py decomposition).

Verifies that each router and service module can be imported independently
without side effects, and that main.py re-exports maintain backward compatibility.
"""

import importlib
import sys


class TestRouterImports:
    """Each router module must be importable independently without side effects."""

    def test_auth_router_importable(self):
        """routers.auth can be imported independently."""
        mod = importlib.import_module("routers.auth")
        assert hasattr(mod, "router")
        assert hasattr(mod, "auth_token")
        assert hasattr(mod, "auth_signup")
        assert hasattr(mod, "auth_login")
        assert hasattr(mod, "auth_refresh")

    def test_health_router_importable(self):
        """routers.health can be imported independently."""
        mod = importlib.import_module("routers.health")
        assert hasattr(mod, "router")
        assert hasattr(mod, "root")
        assert hasattr(mod, "health")
        assert hasattr(mod, "listar_setores")

    def test_search_router_importable(self):
        """routers.search can be imported independently."""
        mod = importlib.import_module("routers.search")
        assert hasattr(mod, "router")
        assert hasattr(mod, "buscar_licitacoes")
        assert hasattr(mod, "job_status")
        assert hasattr(mod, "cancel_job")
        assert hasattr(mod, "job_result")
        assert hasattr(mod, "job_items")
        assert hasattr(mod, "job_download")
        assert hasattr(mod, "search_history")


class TestServiceImports:
    """Each service module must be importable independently."""

    def test_term_parser_importable(self):
        """services.term_parser can be imported independently."""
        mod = importlib.import_module("services.term_parser")
        assert hasattr(mod, "parse_multi_word_terms")
        # Verify function works
        result = mod.parse_multi_word_terms('"camisa polo", uniforme')
        assert result == ["camisa polo", "uniforme"]

    def test_search_pipeline_importable(self):
        """services.search_pipeline can be imported independently."""
        mod = importlib.import_module("services.search_pipeline")
        assert hasattr(mod, "execute_search_pipeline")
        assert callable(mod.execute_search_pipeline)


class TestMainBackwardCompatibility:
    """main.py must re-export all names that tests depend on."""

    def test_app_importable_from_main(self):
        """from main import app must work."""
        from main import app

        assert app is not None
        assert app.title == "Descomplicita API"

    def test_limiter_importable_from_main(self):
        """from main import limiter must work."""
        from main import limiter

        assert limiter is not None

    def test_run_search_job_importable_from_main(self):
        """from main import run_search_job must work."""
        from main import run_search_job

        assert callable(run_search_job)

    def test_parse_multi_word_terms_importable_from_main(self):
        """from main import parse_multi_word_terms must work."""
        from main import parse_multi_word_terms

        assert callable(parse_multi_word_terms)

    def test_filter_executor_importable_from_main(self):
        """from main import _filter_executor must work."""
        from main import _filter_executor

        assert _filter_executor is not None

    def test_lifespan_importable_from_main(self):
        """from main import lifespan must work."""
        from main import lifespan

        assert callable(lifespan)

    def test_auth_token_importable_from_main(self):
        """from main import auth_token must work (used by test_security)."""
        from main import auth_token

        assert callable(auth_token)

    def test_debug_enabled_accessible_from_main(self):
        """main._debug_enabled must be accessible (used by test_cache)."""
        import main as main_module

        assert hasattr(main_module, "_debug_enabled")

    def test_filter_batch_importable_from_main(self):
        """from main import filter_batch must work (monkeypatch target)."""
        from main import filter_batch

        assert callable(filter_batch)

    def test_gerar_resumo_importable_from_main(self):
        """from main import gerar_resumo must work (monkeypatch target)."""
        from main import gerar_resumo

        assert callable(gerar_resumo)

    def test_create_excel_importable_from_main(self):
        """from main import create_excel must work (monkeypatch target)."""
        from main import create_excel

        assert callable(create_excel)


class TestNoCircularImports:
    """Verify no circular import issues exist."""

    def test_routers_do_not_import_main_at_module_level(self):
        """Router modules must not import main at module level (would cause circular imports)."""
        import inspect

        for module_name in ["routers.auth", "routers.health", "routers.search"]:
            mod = importlib.import_module(module_name)
            source = inspect.getsource(mod)
            # Check that 'import main' only appears inside function bodies, not at module level
            lines = source.split("\n")
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("import main") or stripped.startswith("from main import"):
                    # Must be indented (inside a function), not at module level
                    assert line[0] == " " or line[0] == "\t", (
                        f"{module_name} has module-level import of main at line {i + 1}: {line}"
                    )

    def test_services_do_not_import_main_at_module_level(self):
        """Service modules must not import main at module level."""
        import inspect

        for module_name in ["services.term_parser", "services.search_pipeline"]:
            mod = importlib.import_module(module_name)
            source = inspect.getsource(mod)
            lines = source.split("\n")
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("import main") or stripped.startswith("from main import"):
                    assert line[0] == " " or line[0] == "\t", (
                        f"{module_name} has module-level import of main at line {i + 1}: {line}"
                    )


class TestMainLineCount:
    """Verify main.py meets the <300 line requirement."""

    def test_main_under_300_lines(self):
        """main.py must be under 300 lines after decomposition."""
        import inspect

        import main as main_module

        source = inspect.getsource(main_module)
        line_count = len(source.strip().split("\n"))
        assert line_count < 300, f"main.py has {line_count} lines, must be under 300"
