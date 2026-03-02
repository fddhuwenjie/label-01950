"""
Unit tests for CompletionService.
"""
import pytest
from app.services.completion_service import CompletionService, completion_service
from app.models import CompletionItemKind


class TestCompletionService:
    """Tests for CompletionService class."""
    
    @pytest.fixture
    def service(self):
        """Create a fresh CompletionService instance."""
        return CompletionService()
    
    def test_get_completions_empty_prefix(self, service):
        """Test completions with empty prefix returns all items."""
        text = ""
        completions = service.get_completions(text, 0, 0, "ansi")
        
        # Should return items (limited to 50)
        assert len(completions) > 0
        assert len(completions) <= 50
    
    def test_get_completions_select_prefix(self, service):
        """Test completions with 'SEL' prefix."""
        text = "SEL"
        completions = service.get_completions(text, 0, 3, "ansi")
        
        # Should include SELECT
        labels = [c.label for c in completions]
        assert "SELECT" in labels
    
    def test_get_completions_function_prefix(self, service):
        """Test completions with function prefix."""
        text = "SELECT COU"
        completions = service.get_completions(text, 0, 10, "ansi")
        
        # Should include COUNT
        labels = [c.label for c in completions]
        assert "COUNT" in labels
    
    def test_get_completions_case_insensitive(self, service):
        """Test completions are case insensitive."""
        text = "sel"
        completions = service.get_completions(text, 0, 3, "ansi")
        
        # Should include SELECT (uppercase)
        labels = [c.label for c in completions]
        assert "SELECT" in labels
    
    def test_get_completions_sparksql_dialect(self, service):
        """Test SparkSQL specific completions."""
        text = "EXPL"
        completions = service.get_completions(text, 0, 4, "sparksql")
        
        # Should include EXPLODE (SparkSQL specific)
        labels = [c.label for c in completions]
        assert "EXPLODE" in labels
    
    def test_get_completions_hive_dialect(self, service):
        """Test Hive specific completions."""
        text = "LATE"
        completions = service.get_completions(text, 0, 4, "hive")
        
        # Should include LATERAL VIEW (Hive specific)
        labels = [c.label for c in completions]
        assert "LATERAL VIEW" in labels
    
    def test_get_completions_multiline(self, service):
        """Test completions on multiline text."""
        text = "SELECT *\nFROM users\nWHERE na"
        completions = service.get_completions(text, 2, 8, "ansi")
        
        # Should include NATURAL (starts with 'na')
        labels = [c.label for c in completions]
        assert "NATURAL" in labels
    
    def test_get_completions_mid_line(self, service):
        """Test completions in middle of line."""
        text = "SELECT id, na FROM users"
        completions = service.get_completions(text, 0, 13, "ansi")
        
        # Should include items starting with 'na'
        labels = [c.label for c in completions]
        assert any(l.upper().startswith("NA") for l in labels)
    
    def test_completion_item_kind_keyword(self, service):
        """Test keyword completions have correct kind."""
        text = "SEL"
        completions = service.get_completions(text, 0, 3, "ansi")
        
        select_item = next((c for c in completions if c.label == "SELECT"), None)
        assert select_item is not None
        assert select_item.kind == CompletionItemKind.KEYWORD
    
    def test_completion_item_kind_function(self, service):
        """Test function completions have correct kind."""
        text = "COU"
        completions = service.get_completions(text, 0, 3, "ansi")
        
        count_item = next((c for c in completions if c.label == "COUNT"), None)
        assert count_item is not None
        assert count_item.kind == CompletionItemKind.FUNCTION
    
    def test_completion_item_has_documentation(self, service):
        """Test function completions have documentation."""
        text = "COU"
        completions = service.get_completions(text, 0, 3, "ansi")
        
        count_item = next((c for c in completions if c.label == "COUNT"), None)
        assert count_item is not None
        assert count_item.documentation is not None
        assert "COUNT" in count_item.documentation
    
    def test_get_word_prefix_start_of_line(self, service):
        """Test word prefix extraction at start of line."""
        prefix = service._get_word_prefix("SELECT", 3)
        assert prefix == "SEL"
    
    def test_get_word_prefix_after_space(self, service):
        """Test word prefix extraction after space."""
        prefix = service._get_word_prefix("SELECT id", 9)
        assert prefix == "id"
    
    def test_get_word_prefix_empty(self, service):
        """Test word prefix extraction with no word."""
        prefix = service._get_word_prefix("SELECT ", 7)
        assert prefix == ""
    
    def test_get_word_prefix_with_underscore(self, service):
        """Test word prefix with underscore."""
        prefix = service._get_word_prefix("user_id", 7)
        assert prefix == "user_id"
    
    def test_is_word_char_alphanumeric(self, service):
        """Test word character detection for alphanumeric."""
        assert service._is_word_char('a') is True
        assert service._is_word_char('Z') is True
        assert service._is_word_char('5') is True
    
    def test_is_word_char_underscore(self, service):
        """Test word character detection for underscore."""
        assert service._is_word_char('_') is True
    
    def test_is_word_char_special(self, service):
        """Test word character detection for special chars."""
        assert service._is_word_char(' ') is False
        assert service._is_word_char('.') is True  # Dot is allowed for qualified names (table.column)
        assert service._is_word_char(',') is False
    
    def test_completions_limit(self, service):
        """Test completions are limited to 50 items."""
        text = ""
        completions = service.get_completions(text, 0, 0, "ansi")
        assert len(completions) <= 50
    
    def test_completions_out_of_bounds_line(self, service):
        """Test completions with out of bounds line number."""
        text = "SELECT"
        completions = service.get_completions(text, 10, 0, "ansi")
        assert completions == []


class TestContextAwareCompletion:
    """Test context-aware completion features."""
    
    @pytest.fixture
    def service(self):
        return CompletionService()
    
    def test_from_clause_suggests_tables(self, service):
        """Test that FROM clause suggests table names."""
        text = "SELECT * FROM "
        completions = service.get_completions(text, 0, 14, "ansi")
        labels = [c.label for c in completions]
        # Should include table names
        assert "users" in labels
        assert "orders" in labels
        assert "products" in labels
    
    def test_select_clause_suggests_functions(self, service):
        """Test that SELECT clause suggests functions."""
        text = "SELECT CO"
        completions = service.get_completions(text, 0, 9, "ansi")
        labels = [c.label for c in completions]
        # Should include functions starting with CO
        assert "COUNT" in labels
        assert "COALESCE" in labels
    
    def test_where_clause_suggests_columns(self, service):
        """Test that WHERE clause suggests columns from referenced tables."""
        text = "SELECT * FROM users WHERE "
        completions = service.get_completions(text, 0, 26, "ansi")
        labels = [c.label for c in completions]
        # Should include columns from users table
        assert "id" in labels
        assert "name" in labels
        assert "email" in labels
    
    def test_qualified_column_completion(self, service):
        """Test completion for qualified column names (table.column)."""
        text = "SELECT users."
        completions = service.get_completions(text, 0, 13, "ansi")
        labels = [c.label for c in completions]
        # Should include qualified column names
        assert any("users.id" in label for label in labels)
        assert any("users.name" in label for label in labels)
    
    def test_join_clause_suggests_tables(self, service):
        """Test that JOIN clause suggests table names."""
        text = "SELECT * FROM users JOIN "
        completions = service.get_completions(text, 0, 25, "ansi")
        labels = [c.label for c in completions]
        # Should include table names
        assert "orders" in labels
        assert "products" in labels
    
    def test_order_by_suggests_columns(self, service):
        """Test that ORDER BY clause suggests columns."""
        text = "SELECT * FROM users ORDER BY "
        completions = service.get_completions(text, 0, 29, "ansi")
        labels = [c.label for c in completions]
        # Should include columns from users table
        assert "id" in labels
        assert "name" in labels
    
    def test_table_metadata_exists(self, service):
        """Test that mock table metadata is available."""
        assert "users" in service.MOCK_TABLES
        assert "columns" in service.MOCK_TABLES["users"]
        assert "id" in service.MOCK_TABLES["users"]["columns"]


class TestCompletionServiceSingleton:
    """Tests for completion_service singleton."""
    
    def test_singleton_get_completions(self):
        """Test singleton instance can get completions."""
        completions = completion_service.get_completions("SEL", 0, 3, "ansi")
        assert len(completions) > 0
        labels = [c.label for c in completions]
        assert "SELECT" in labels
