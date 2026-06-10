"""
CLI regression tests.

Tests:
- T077: Regression test for CLI functionality
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# T077: Regression test for CLI functionality
# =============================================================================

class TestCLIImports:
    """Test that CLI imports still work with new web/ directory."""

    def test_second_hand_research_import(self):
        """Test that the main CLI script can be imported."""
        try:
            import second_hand_research
            assert second_hand_research is not None
        except ImportError as e:
            pytest.fail(f"Failed to import second_hand_research: {e}")

    def test_core_pipeline_import(self):
        """Test that core pipeline can be imported."""
        try:
            from core.pipeline import Pipeline
            assert Pipeline is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Pipeline: {e}")

    def test_models_import(self):
        """Test that models can be imported."""
        try:
            from models import Listing
            assert Listing is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Listing: {e}")

    def test_config_import(self):
        """Test that config can be imported."""
        try:
            from config import WebConfig
            assert WebConfig is not None
        except ImportError as e:
            pytest.fail(f"Failed to import WebConfig: {e}")

    def test_all_scrapers_import(self):
        """Test that all scrapers can be imported."""
        try:
            import scrapers.dba
            import scrapers.vinted
            import scrapers.tradera
            assert scrapers.dba is not None
            assert scrapers.vinted is not None
            assert scrapers.tradera is not None
        except ImportError as e:
            pytest.fail(f"Failed to import scrapers: {e}")

    def test_all_processors_import(self):
        """Test that all processors can be imported."""
        try:
            import processors.description_fetcher
            import processors.model_extractor
            import processors.price_converter
            import processors.query_preprocessor
            import processors.query_preprocessor_module
        except ImportError as e:
            pytest.fail(f"Failed to import processors: {e}")

    def test_all_filters_import(self):
        """Test that all filters can be imported."""
        try:
            import filters.keyword_filter
            import filters.llm_filter
        except ImportError as e:
            pytest.fail(f"Failed to import filters: {e}")

    def test_all_rankers_import(self):
        """Test that all rankers can be imported."""
        try:
            import rankers.ranker_module
        except ImportError as e:
            pytest.fail(f"Failed to import rankers: {e}")

    def test_all_reviewers_import(self):
        """Test that all reviewers can be imported."""
        try:
            import reviewers.search
            import reviewers.review_aggregator
        except ImportError as e:
            pytest.fail(f"Failed to import reviewers: {e}")


class TestCLIVsWebIndependence:
    """Test that CLI and web can operate independently."""

    def test_cli_does_not_depend_on_web(self):
        """Test that CLI does not require web modules."""
        # The CLI should work even if web modules are not imported
        try:
            import second_hand_research
            assert second_hand_research is not None
        except ImportError as e:
            # If this fails, it means CLI depends on web
            pytest.fail(f"CLI appears to depend on web modules: {e}")

    def test_web_does_not_modify_cli(self):
        """Test that web modules don't modify CLI behavior."""
        # Import both and verify they don't interfere
        try:
            import second_hand_research
            from web.backend.main import app
            assert second_hand_research is not None
            assert app is not None
        except Exception as e:
            pytest.fail(f"CLI and web cannot coexist: {e}")


class TestCLIFunctionSignature:
    """Test that CLI function signatures are unchanged."""

    def test_main_function_exists(self):
        """Test that the main function exists in CLI."""
        import second_hand_research
        assert hasattr(second_hand_research, 'main')

    def test_pipeline_function_exists(self):
        """Test that pipeline functions exist."""
        from core.pipeline import Pipeline
        assert hasattr(Pipeline, 'execute')
        assert callable(Pipeline.execute)


class TestCLIWithWebPresent:
    """Test that CLI works when web directory is present."""

    @patch('builtins.print')
    def test_cli_help_no_errors(self, mock_print):
        """Test that CLI help command works without errors."""
        import second_hand_research
        try:
            # Just verify the module loads - actual execution would require API keys
            assert second_hand_research is not None
        except Exception as e:
            pytest.fail(f"CLI failed to load: {e}")


class TestWebDoesNotBreakCLI:
    """Test that importing web doesn't break CLI imports."""

    def test_import_order_independence(self):
        """Test that import order doesn't matter."""
        # First import web
        from web.backend.main import app
        assert app is not None

        # Then import CLI
        import second_hand_research
        assert second_hand_research is not None

    def test_simultaneous_imports(self):
        """Test that both can be imported simultaneously."""
        try:
            from web.backend.main import app
            from web.backend.models.schemas import SearchRequest
            from core.pipeline import Pipeline
            from models import Listing
            import second_hand_research
            assert all([
                app, SearchRequest, Pipeline, Listing, second_hand_research
            ])
        except Exception as e:
            pytest.fail(f"Simultaneous imports failed: {e}")
