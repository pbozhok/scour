"""
Contract tests for Reviewer module interface.

Verifies that all reviewers follow the BaseReviewer interface.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from reviewers.base import BaseReviewer
from core.module import Module, ModuleType
from core.module import PipelineContext


class TestBaseReviewerInterface:
    """Contract tests for BaseReviewer interface."""
    
    def test_base_reviewer_inherits_from_module(self):
        """Test that BaseReviewer inherits from Module."""
        assert issubclass(BaseReviewer, Module)
    
    def test_base_reviewer_has_required_class_attributes(self):
        """Test BaseReviewer has required class attributes."""
        assert hasattr(BaseReviewer, 'name')
        assert hasattr(BaseReviewer, 'module_type')
        assert hasattr(BaseReviewer, 'version')
        assert hasattr(BaseReviewer, 'description')
    
    def test_base_reviewer_module_type_is_reviewer(self):
        """Test BaseReviewer has correct module_type."""
        assert BaseReviewer.module_type == ModuleType.REVIEWER
    
    def test_base_reviewer_has_required_methods(self):
        """Test BaseReviewer has all required Module methods."""
        required_methods = ['initialize', 'validate', 'execute', 'cleanup']
        for method in required_methods:
            assert hasattr(BaseReviewer, method), f"Missing method: {method}"
    
    def test_base_reviewer_has_review_method(self):
        """Test BaseReviewer has abstract review method."""
        assert hasattr(BaseReviewer, 'review')
    
    def test_base_reviewer_has_execute_method(self):
        """Test BaseReviewer has execute method."""
        assert hasattr(BaseReviewer, 'execute')
        assert callable(BaseReviewer.execute)


class MockReviewer(BaseReviewer):
    """Mock concrete reviewer for testing."""
    
    name = "mock-reviewer"
    version = "1.0.0"
    
    async def review(self, listings, context):
        """Mock review implementation."""
        return {}


class TestReviewerLifecycle:
    """Tests for reviewer lifecycle methods."""
    
    def test_base_reviewer_can_be_initialized(self):
        """Test BaseReviewer can be initialized (via concrete subclass)."""
        reviewer = MockReviewer()
        result = reviewer.initialize({})
        assert result is True
        assert reviewer._initialized is True
    
    def test_base_reviewer_validation(self):
        """Test BaseReviewer validation (via concrete subclass)."""
        reviewer = MockReviewer()
        reviewer.initialize({})
        assert reviewer.validate() is True
        
        reviewer2 = MockReviewer()
        assert reviewer2.validate() is False
    
    def test_base_reviewer_cleanup(self):
        """Test BaseReviewer cleanup (via concrete subclass)."""
        reviewer = MockReviewer()
        reviewer.initialize({})
        assert reviewer._initialized is True
        
        reviewer.cleanup()
        assert reviewer._initialized is False
    
    @pytest.mark.asyncio
    async def test_base_reviewer_execute_with_empty_listings(self):
        """Test BaseReviewer.execute with empty listings (via concrete subclass)."""
        reviewer = MockReviewer()
        reviewer.initialize({})
        
        context = PipelineContext(query="test", listings=[])
        result = await reviewer.execute(context)
        
        assert result is context
        assert result.listings == []


class TestReviewerClassAttributes:
    """Tests for reviewer class attributes."""
    
    def test_base_reviewer_default_name(self):
        """Test BaseReviewer has default name."""
        assert BaseReviewer.name == "base-reviewer"
    
    def test_base_reviewer_default_version(self):
        """Test BaseReviewer has default version."""
        assert BaseReviewer.version == "1.0.0"
    
    def test_base_reviewer_default_module_type(self):
        """Test BaseReviewer has default module_type."""
        assert BaseReviewer.module_type == ModuleType.REVIEWER
