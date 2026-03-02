"""
SQL code completion service with context-aware suggestions.
"""
import re
from abc import ABC, abstractmethod
from typing import List, Optional, Set, Tuple, Dict, Any, Protocol

from enum import Enum

from ..core import logger
from ..models import CompletionItem, CompletionItemKind


class SQLContext(Enum):
    """SQL syntax context for smart completion."""
    UNKNOWN = "unknown"
    SELECT_CLAUSE = "select"      # After SELECT, before FROM
    FROM_CLAUSE = "from"          # After FROM, before WHERE/JOIN
    JOIN_CLAUSE = "join"          # After JOIN keyword
    WHERE_CLAUSE = "where"        # After WHERE
    GROUP_BY_CLAUSE = "group_by"  # After GROUP BY
    ORDER_BY_CLAUSE = "order_by"  # After ORDER BY
    INSERT_INTO = "insert_into"   # After INSERT INTO
    UPDATE_SET = "update_set"     # After UPDATE ... SET
    CREATE_TABLE = "create_table" # After CREATE TABLE


class MetadataProvider(Protocol):
    """
    Protocol for metadata providers.
    
    Implement this interface to provide custom table/column metadata
    from external sources (databases, catalogs, etc.).
    """
    
    def get_tables(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available tables with their metadata.
        
        Returns:
            Dict mapping table names to metadata dicts containing:
            - columns: List[str] - column names
            - description: str - table description
        """
        ...
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """
        Get columns for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column names
        """
        ...
    
    def refresh(self) -> None:
        """Refresh metadata from the source."""
        ...


class MockMetadataProvider:
    """
    Mock metadata provider with hardcoded table structures.
    
    This is the default provider for demonstration purposes.
    Replace with a real implementation to connect to actual databases.
    """
    
    def __init__(self):
        self._tables = {
            "users": {
                "columns": ["id", "name", "email", "status", "created_at", "updated_at"],
                "description": "User accounts table"
            },
            "orders": {
                "columns": ["id", "user_id", "product_id", "quantity", "price", "status", "created_at"],
                "description": "Customer orders table"
            },
            "products": {
                "columns": ["id", "name", "description", "price", "category_id", "stock", "created_at"],
                "description": "Product catalog table"
            },
            "categories": {
                "columns": ["id", "name", "parent_id", "description"],
                "description": "Product categories table"
            },
            "customers": {
                "columns": ["id", "name", "email", "phone", "address", "city", "country"],
                "description": "Customer information table"
            },
            "employees": {
                "columns": ["id", "name", "department", "position", "salary", "hire_date"],
                "description": "Employee records table"
            },
            "transactions": {
                "columns": ["id", "order_id", "amount", "payment_method", "status", "transaction_date"],
                "description": "Payment transactions table"
            },
            "inventory": {
                "columns": ["id", "product_id", "warehouse_id", "quantity", "last_updated"],
                "description": "Inventory tracking table"
            }
        }
        logger.info("MockMetadataProvider initialized with {} tables", len(self._tables))
    
    def get_tables(self) -> Dict[str, Dict[str, Any]]:
        """Get all available tables."""
        return self._tables.copy()
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """Get columns for a specific table."""
        if table_name in self._tables:
            return self._tables[table_name]["columns"].copy()
        return []
    
    def refresh(self) -> None:
        """Refresh metadata (no-op for mock provider)."""
        logger.debug("MockMetadataProvider refresh called (no-op)")


class CompletionService:
    """Service for SQL code completion suggestions with context awareness."""
    
    # SQL Keywords
    SQL_KEYWORDS = [
        "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "IN", "BETWEEN",
        "LIKE", "IS", "NULL", "TRUE", "FALSE", "AS", "ON", "JOIN",
        "LEFT", "RIGHT", "INNER", "OUTER", "FULL", "CROSS", "NATURAL",
        "GROUP", "BY", "HAVING", "ORDER", "ASC", "DESC", "LIMIT",
        "OFFSET", "UNION", "ALL", "INTERSECT", "EXCEPT", "DISTINCT",
        "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE", "CREATE",
        "TABLE", "VIEW", "INDEX", "DROP", "ALTER", "ADD", "COLUMN",
        "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "UNIQUE", "CHECK",
        "DEFAULT", "CONSTRAINT", "CASCADE", "RESTRICT", "TRUNCATE",
        "CASE", "WHEN", "THEN", "ELSE", "END", "CAST", "CONVERT",
        "COALESCE", "NULLIF", "EXISTS", "ANY", "SOME", "WITH", "RECURSIVE",
        "OVER", "PARTITION", "ROW", "ROWS", "RANGE", "UNBOUNDED",
        "PRECEDING", "FOLLOWING", "CURRENT", "FIRST", "LAST", "NULLS",
    ]
    
    # SQL Functions
    SQL_FUNCTIONS = [
        # Aggregate functions
        ("COUNT", "COUNT(expression) - Returns the number of rows"),
        ("SUM", "SUM(expression) - Returns the sum of values"),
        ("AVG", "AVG(expression) - Returns the average value"),
        ("MIN", "MIN(expression) - Returns the minimum value"),
        ("MAX", "MAX(expression) - Returns the maximum value"),
        ("GROUP_CONCAT", "GROUP_CONCAT(expression) - Concatenates values"),
        
        # String functions
        ("CONCAT", "CONCAT(str1, str2, ...) - Concatenates strings"),
        ("SUBSTRING", "SUBSTRING(str, start, length) - Extracts substring"),
        ("LENGTH", "LENGTH(str) - Returns string length"),
        ("UPPER", "UPPER(str) - Converts to uppercase"),
        ("LOWER", "LOWER(str) - Converts to lowercase"),
        ("TRIM", "TRIM(str) - Removes leading/trailing spaces"),
        ("LTRIM", "LTRIM(str) - Removes leading spaces"),
        ("RTRIM", "RTRIM(str) - Removes trailing spaces"),
        ("REPLACE", "REPLACE(str, from, to) - Replaces occurrences"),
        ("REVERSE", "REVERSE(str) - Reverses string"),
        ("SPLIT", "SPLIT(str, delimiter) - Splits string into array"),
        
        # Date functions
        ("NOW", "NOW() - Returns current timestamp"),
        ("CURRENT_DATE", "CURRENT_DATE - Returns current date"),
        ("CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP - Returns current timestamp"),
        ("DATE_ADD", "DATE_ADD(date, interval) - Adds interval to date"),
        ("DATE_SUB", "DATE_SUB(date, interval) - Subtracts interval from date"),
        ("DATEDIFF", "DATEDIFF(date1, date2) - Returns difference in days"),
        ("DATE_FORMAT", "DATE_FORMAT(date, format) - Formats date"),
        ("YEAR", "YEAR(date) - Extracts year"),
        ("MONTH", "MONTH(date) - Extracts month"),
        ("DAY", "DAY(date) - Extracts day"),
        ("HOUR", "HOUR(datetime) - Extracts hour"),
        ("MINUTE", "MINUTE(datetime) - Extracts minute"),
        ("SECOND", "SECOND(datetime) - Extracts second"),
        
        # Numeric functions
        ("ABS", "ABS(n) - Returns absolute value"),
        ("CEIL", "CEIL(n) - Rounds up to nearest integer"),
        ("FLOOR", "FLOOR(n) - Rounds down to nearest integer"),
        ("ROUND", "ROUND(n, decimals) - Rounds to specified decimals"),
        ("MOD", "MOD(n, m) - Returns remainder of n/m"),
        ("POWER", "POWER(base, exp) - Returns base raised to exp"),
        ("SQRT", "SQRT(n) - Returns square root"),
        ("LOG", "LOG(n) - Returns natural logarithm"),
        ("EXP", "EXP(n) - Returns e raised to n"),
        ("RAND", "RAND() - Returns random number between 0 and 1"),
        
        # Window functions
        ("ROW_NUMBER", "ROW_NUMBER() OVER(...) - Assigns unique row number"),
        ("RANK", "RANK() OVER(...) - Assigns rank with gaps"),
        ("DENSE_RANK", "DENSE_RANK() OVER(...) - Assigns rank without gaps"),
        ("NTILE", "NTILE(n) OVER(...) - Divides rows into n groups"),
        ("LAG", "LAG(col, offset) OVER(...) - Accesses previous row"),
        ("LEAD", "LEAD(col, offset) OVER(...) - Accesses next row"),
        ("FIRST_VALUE", "FIRST_VALUE(col) OVER(...) - Returns first value"),
        ("LAST_VALUE", "LAST_VALUE(col) OVER(...) - Returns last value"),
        
        # Conditional functions
        ("IF", "IF(condition, true_val, false_val) - Conditional expression"),
        ("IFNULL", "IFNULL(expr, default) - Returns default if null"),
        ("NVL", "NVL(expr, default) - Returns default if null"),
        ("DECODE", "DECODE(expr, search, result, ...) - Conditional mapping"),
    ]
    
    # SparkSQL specific keywords and functions
    SPARK_SPECIFIC = [
        ("LATERAL", "LATERAL VIEW - Generates rows from array/map"),
        ("EXPLODE", "EXPLODE(array) - Expands array to rows"),
        ("POSEXPLODE", "POSEXPLODE(array) - Explode with position"),
        ("INLINE", "INLINE(array_of_structs) - Explodes struct array"),
        ("STACK", "STACK(n, ...) - Separates values into rows"),
        ("COLLECT_LIST", "COLLECT_LIST(col) - Aggregates into array"),
        ("COLLECT_SET", "COLLECT_SET(col) - Aggregates into unique array"),
        ("ARRAY", "ARRAY(val1, val2, ...) - Creates array"),
        ("MAP", "MAP(key1, val1, ...) - Creates map"),
        ("STRUCT", "STRUCT(val1, val2, ...) - Creates struct"),
        ("NAMED_STRUCT", "NAMED_STRUCT(name1, val1, ...) - Creates named struct"),
        ("GET_JSON_OBJECT", "GET_JSON_OBJECT(json, path) - Extracts JSON value"),
        ("FROM_JSON", "FROM_JSON(json, schema) - Parses JSON string"),
        ("TO_JSON", "TO_JSON(struct) - Converts to JSON string"),
        ("TRANSFORM", "TRANSFORM(array, func) - Transforms array elements"),
        ("FILTER", "FILTER(array, func) - Filters array elements"),
        ("AGGREGATE", "AGGREGATE(array, start, merge, finish) - Reduces array"),
        ("DISTRIBUTE", "DISTRIBUTE BY - Controls data distribution"),
        ("CLUSTER", "CLUSTER BY - Distributes and sorts data"),
        ("SORT", "SORT BY - Sorts within partition"),
        ("TABLESAMPLE", "TABLESAMPLE - Samples table data"),
        ("PIVOT", "PIVOT - Rotates rows to columns"),
        ("UNPIVOT", "UNPIVOT - Rotates columns to rows"),
    ]
    
    # HiveSQL specific keywords and functions
    HIVE_SPECIFIC = [
        ("PARTITIONED", "PARTITIONED BY - Defines table partitions"),
        ("CLUSTERED", "CLUSTERED BY - Defines table clustering"),
        ("BUCKETS", "INTO n BUCKETS - Specifies bucket count"),
        ("STORED", "STORED AS - Specifies storage format"),
        ("LOCATION", "LOCATION - Specifies data location"),
        ("TBLPROPERTIES", "TBLPROPERTIES - Table properties"),
        ("SERDEPROPERTIES", "SERDEPROPERTIES - SerDe properties"),
        ("ROW FORMAT", "ROW FORMAT - Specifies row format"),
        ("DELIMITED", "DELIMITED - Specifies delimiters"),
        ("FIELDS", "FIELDS TERMINATED BY - Field delimiter"),
        ("COLLECTION", "COLLECTION ITEMS TERMINATED BY - Collection delimiter"),
        ("MAP KEYS", "MAP KEYS TERMINATED BY - Map key delimiter"),
        ("LINES", "LINES TERMINATED BY - Line delimiter"),
        ("EXTERNAL", "EXTERNAL TABLE - Creates external table"),
        ("TEMPORARY", "TEMPORARY TABLE - Creates temp table"),
        ("MSCK", "MSCK REPAIR TABLE - Recovers partitions"),
        ("ANALYZE", "ANALYZE TABLE - Computes statistics"),
        ("COMPUTE", "COMPUTE STATISTICS - Computes table stats"),
        ("DESCRIBE", "DESCRIBE - Shows table schema"),
        ("SHOW", "SHOW - Lists database objects"),
        ("USE", "USE database - Switches database"),
        ("OVERWRITE", "INSERT OVERWRITE - Overwrites data"),
        ("DIRECTORY", "DIRECTORY - Specifies output directory"),
        ("LATERAL VIEW", "LATERAL VIEW - Generates rows"),
        ("PARSE_URL", "PARSE_URL(url, part) - Parses URL"),
        ("REFLECT", "REFLECT(class, method, ...) - Calls Java method"),
        ("XPATH", "XPATH(xml, path) - Extracts XML values"),
        ("XPATH_STRING", "XPATH_STRING(xml, path) - Extracts XML string"),
    ]
    
    # Data types
    DATA_TYPES = [
        "INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT",
        "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC",
        "VARCHAR", "CHAR", "STRING", "TEXT",
        "DATE", "DATETIME", "TIMESTAMP", "TIME",
        "BOOLEAN", "BOOL",
        "BINARY", "VARBINARY", "BLOB",
        "ARRAY", "MAP", "STRUCT", "JSON",
    ]
    
    def __init__(self, metadata_provider: Optional[MetadataProvider] = None):
        """
        Initialize CompletionService.
        
        Args:
            metadata_provider: Optional metadata provider for table/column info.
                              If not provided, uses MockMetadataProvider.
        """
        self._completion_cache: dict = {}
        self._table_aliases: dict = {}  # Track table aliases in current query
        self._metadata_provider = metadata_provider or MockMetadataProvider()
        logger.info("CompletionService initialized with {}", type(self._metadata_provider).__name__)
    
    @property
    def MOCK_TABLES(self) -> Dict[str, Dict[str, Any]]:
        """Get tables from metadata provider (for backward compatibility)."""
        return self._metadata_provider.get_tables()
    
    def set_metadata_provider(self, provider: MetadataProvider) -> None:
        """
        Set a new metadata provider.
        
        Args:
            provider: New metadata provider instance
        """
        self._metadata_provider = provider
        logger.info("Metadata provider changed to {}", type(provider).__name__)
    
    def refresh_metadata(self) -> None:
        """Refresh metadata from the current provider."""
        self._metadata_provider.refresh()
        logger.info("Metadata refreshed")
    
    def _analyze_context(self, text: str, line: int, character: int) -> Tuple[SQLContext, Set[str], dict]:
        """
        Analyze SQL context at the given position.
        
        Returns:
            Tuple of (context, referenced_tables, table_aliases)
        """
        # Get text up to cursor position
        lines = text.split('\n')
        text_before_cursor = '\n'.join(lines[:line]) + '\n' + lines[line][:character] if line < len(lines) else text
        
        # Normalize whitespace for analysis
        normalized = ' '.join(text_before_cursor.upper().split())
        
        # Extract table aliases (e.g., "users u", "orders AS o")
        table_aliases = {}
        alias_pattern = r'\b(\w+)\s+(?:AS\s+)?(\w+)\s*(?:,|JOIN|WHERE|GROUP|ORDER|ON|LEFT|RIGHT|INNER|$)'
        
        # Find referenced tables
        referenced_tables: Set[str] = set()
        for table_name in self.MOCK_TABLES.keys():
            if table_name.upper() in normalized:
                referenced_tables.add(table_name)
        
        # Extract aliases from FROM clause
        from_match = re.search(r'\bFROM\s+(.+?)(?:\bWHERE\b|\bGROUP\b|\bORDER\b|\bLIMIT\b|\bJOIN\b|$)', normalized, re.IGNORECASE)
        if from_match:
            from_clause = from_match.group(1)
            # Parse "table alias" or "table AS alias" patterns
            for table_name in self.MOCK_TABLES.keys():
                pattern = rf'\b{table_name.upper()}\s+(?:AS\s+)?(\w+)'
                alias_match = re.search(pattern, from_clause)
                if alias_match:
                    table_aliases[alias_match.group(1).lower()] = table_name
        
        # Determine context based on keywords
        context = SQLContext.UNKNOWN
        
        # Check context in reverse order of SQL clause precedence
        # Use more flexible patterns that match end of string or trailing whitespace
        if re.search(r'\bORDER\s+BY\b', normalized):
            context = SQLContext.ORDER_BY_CLAUSE
        elif re.search(r'\bGROUP\s+BY\b', normalized):
            context = SQLContext.GROUP_BY_CLAUSE
        elif re.search(r'\bWHERE\b', normalized) and not re.search(r'\bGROUP\s+BY\b', normalized) and not re.search(r'\bORDER\s+BY\b', normalized):
            context = SQLContext.WHERE_CLAUSE
        elif re.search(r'\bJOIN\s*$', normalized) or re.search(r'\bJOIN\s+\w*$', normalized):
            context = SQLContext.JOIN_CLAUSE
        elif re.search(r'\bFROM\s*$', normalized) or re.search(r'\bFROM\s+\w*$', normalized):
            context = SQLContext.FROM_CLAUSE
        elif re.search(r'\bSELECT\b', normalized) and not re.search(r'\bFROM\b', normalized):
            context = SQLContext.SELECT_CLAUSE
        elif re.search(r'\bINSERT\s+INTO\s*$', normalized) or re.search(r'\bINSERT\s+INTO\s+\w*$', normalized):
            context = SQLContext.INSERT_INTO
        elif re.search(r'\bUPDATE\s+\w+\s+SET\b', normalized):
            context = SQLContext.UPDATE_SET
        elif re.search(r'\bCREATE\s+TABLE\b', normalized):
            context = SQLContext.CREATE_TABLE
        
        logger.debug(f"Context analysis: {context.value}, tables: {referenced_tables}, aliases: {table_aliases}")
        return context, referenced_tables, table_aliases
    
    def _build_table_completions(self) -> List[CompletionItem]:
        """Build completion items for table names."""
        return [
            CompletionItem(
                label=table_name,
                kind=CompletionItemKind.CLASS,  # Use CLASS for tables
                detail=f"Table: {meta['description']}",
                documentation=f"Columns: {', '.join(meta['columns'])}",
                insertText=table_name,
                sortText=f"0_{table_name}"  # High priority
            )
            for table_name, meta in self.MOCK_TABLES.items()
        ]
    
    def _build_column_completions(self, tables: Set[str], aliases: dict) -> List[CompletionItem]:
        """Build completion items for column names from referenced tables."""
        items = []
        seen_columns: Set[str] = set()
        
        for table_name in tables:
            if table_name in self.MOCK_TABLES:
                meta = self.MOCK_TABLES[table_name]
                for col in meta['columns']:
                    if col not in seen_columns:
                        items.append(CompletionItem(
                            label=col,
                            kind=CompletionItemKind.FIELD,
                            detail=f"Column from {table_name}",
                            insertText=col,
                            sortText=f"0_{col}"  # High priority
                        ))
                        seen_columns.add(col)
        
        # Also add qualified column names (table.column or alias.column)
        for table_name in tables:
            if table_name in self.MOCK_TABLES:
                meta = self.MOCK_TABLES[table_name]
                # Find alias for this table
                table_alias = None
                for alias, tbl in aliases.items():
                    if tbl == table_name:
                        table_alias = alias
                        break
                
                prefix = table_alias if table_alias else table_name
                for col in meta['columns']:
                    qualified_name = f"{prefix}.{col}"
                    items.append(CompletionItem(
                        label=qualified_name,
                        kind=CompletionItemKind.FIELD,
                        detail=f"Column from {table_name}",
                        insertText=qualified_name,
                        sortText=f"1_{qualified_name}"
                    ))
        
        return items
    
    def _build_keyword_completions(self) -> List[CompletionItem]:
        """Build completion items for SQL keywords."""
        return [
            CompletionItem(
                label=kw,
                kind=CompletionItemKind.KEYWORD,
                detail="SQL Keyword",
                insertText=kw,
                sortText=f"0_{kw}"
            )
            for kw in self.SQL_KEYWORDS
        ]
    
    def _build_function_completions(self) -> List[CompletionItem]:
        """Build completion items for SQL functions."""
        return [
            CompletionItem(
                label=name,
                kind=CompletionItemKind.FUNCTION,
                detail="SQL Function",
                documentation=doc,
                insertText=f"{name}($0)",
                sortText=f"1_{name}"
            )
            for name, doc in self.SQL_FUNCTIONS
        ]
    
    def _build_type_completions(self) -> List[CompletionItem]:
        """Build completion items for data types."""
        return [
            CompletionItem(
                label=dt,
                kind=CompletionItemKind.TYPE_PARAMETER,
                detail="Data Type",
                insertText=dt,
                sortText=f"2_{dt}"
            )
            for dt in self.DATA_TYPES
        ]
    
    def _build_dialect_completions(self, dialect: str) -> List[CompletionItem]:
        """Build dialect-specific completion items."""
        items = []
        
        if dialect == "sparksql":
            for name, doc in self.SPARK_SPECIFIC:
                items.append(CompletionItem(
                    label=name,
                    kind=CompletionItemKind.FUNCTION if "(" in doc else CompletionItemKind.KEYWORD,
                    detail="SparkSQL",
                    documentation=doc,
                    insertText=name,
                    sortText=f"3_{name}"
                ))
        elif dialect == "hive":
            for name, doc in self.HIVE_SPECIFIC:
                items.append(CompletionItem(
                    label=name,
                    kind=CompletionItemKind.FUNCTION if "(" in doc else CompletionItemKind.KEYWORD,
                    detail="HiveSQL",
                    documentation=doc,
                    insertText=name,
                    sortText=f"3_{name}"
                ))
        
        return items
    
    def get_completions(
        self,
        text: str,
        line: int,
        character: int,
        dialect: str = "ansi"
    ) -> List[CompletionItem]:
        """
        Get context-aware completion suggestions for the given position.
        
        Args:
            text: Full document text.
            line: Current line number (0-indexed).
            character: Current character position (0-indexed).
            dialect: SQL dialect.
            
        Returns:
            List of completion items based on SQL context.
        """
        # Get the current word being typed
        lines = text.split('\n')
        if line >= len(lines):
            return []
        
        current_line = lines[line]
        prefix = self._get_word_prefix(current_line, character)
        
        # Analyze SQL context
        context, referenced_tables, table_aliases = self._analyze_context(text, line, character)
        
        logger.debug(f"Getting completions for prefix: '{prefix}', context: {context.value}, dialect: {dialect}")
        
        # Build context-aware completions
        all_items = []
        
        # Context-specific completions
        if context == SQLContext.FROM_CLAUSE or context == SQLContext.JOIN_CLAUSE:
            # After FROM or JOIN: prioritize table names
            all_items.extend(self._build_table_completions())
            all_items.extend(self._build_keyword_completions())
            
        elif context == SQLContext.SELECT_CLAUSE:
            # After SELECT: prioritize columns and functions
            if referenced_tables:
                all_items.extend(self._build_column_completions(referenced_tables, table_aliases))
            all_items.extend(self._build_function_completions())
            all_items.extend(self._build_keyword_completions())
            # Also add table names for qualified column access
            all_items.extend(self._build_table_completions())
            
        elif context == SQLContext.WHERE_CLAUSE:
            # After WHERE: prioritize columns, then functions and keywords
            if referenced_tables:
                all_items.extend(self._build_column_completions(referenced_tables, table_aliases))
            all_items.extend(self._build_function_completions())
            all_items.extend(self._build_keyword_completions())
            
        elif context == SQLContext.GROUP_BY_CLAUSE or context == SQLContext.ORDER_BY_CLAUSE:
            # After GROUP BY or ORDER BY: prioritize columns
            if referenced_tables:
                all_items.extend(self._build_column_completions(referenced_tables, table_aliases))
            all_items.extend(self._build_keyword_completions())
            
        elif context == SQLContext.INSERT_INTO:
            # After INSERT INTO: prioritize table names
            all_items.extend(self._build_table_completions())
            
        elif context == SQLContext.UPDATE_SET:
            # After UPDATE SET: prioritize columns
            if referenced_tables:
                all_items.extend(self._build_column_completions(referenced_tables, table_aliases))
            all_items.extend(self._build_function_completions())
            
        elif context == SQLContext.CREATE_TABLE:
            # After CREATE TABLE: suggest data types
            all_items.extend(self._build_type_completions())
            all_items.extend(self._build_keyword_completions())
            
        else:
            # Default: provide all completions
            all_items.extend(self._build_keyword_completions())
            all_items.extend(self._build_function_completions())
            all_items.extend(self._build_table_completions())
            all_items.extend(self._build_type_completions())
            if referenced_tables:
                all_items.extend(self._build_column_completions(referenced_tables, table_aliases))
        
        # Add dialect-specific completions
        all_items.extend(self._build_dialect_completions(dialect))
        
        # Filter by prefix
        if prefix:
            prefix_upper = prefix.upper()
            # Handle qualified names (e.g., "users." or "u.")
            if '.' in prefix:
                # User is typing a qualified column name
                table_prefix, col_prefix = prefix.rsplit('.', 1)
                table_prefix_lower = table_prefix.lower()
                
                # Find the actual table name from alias or direct reference
                actual_table = table_aliases.get(table_prefix_lower, table_prefix_lower)
                
                if actual_table in self.MOCK_TABLES:
                    # Return only columns from this specific table
                    filtered_items = []
                    for col in self.MOCK_TABLES[actual_table]['columns']:
                        if col.upper().startswith(col_prefix.upper()):
                            qualified_name = f"{table_prefix}.{col}"
                            filtered_items.append(CompletionItem(
                                label=qualified_name,
                                kind=CompletionItemKind.FIELD,
                                detail=f"Column from {actual_table}",
                                insertText=qualified_name,
                                sortText=f"0_{col}"
                            ))
                    return filtered_items[:50]
            
            filtered_items = [
                item for item in all_items
                if item.label.upper().startswith(prefix_upper)
            ]
        else:
            filtered_items = all_items
        
        # Remove duplicates while preserving order
        seen = set()
        unique_items = []
        for item in filtered_items:
            if item.label not in seen:
                seen.add(item.label)
                unique_items.append(item)
        
        logger.debug(f"Returning {len(unique_items)} completion items for context: {context.value}")
        return unique_items[:50]  # Limit results
    
    def _get_word_prefix(self, line: str, character: int) -> str:
        """
        Extract the word prefix at the given position, including qualified names.
        
        Args:
            line: Current line text.
            character: Character position.
            
        Returns:
            Word prefix string (may include dots for qualified names).
        """
        if character > len(line):
            character = len(line)
        
        # Find word start (including dots for qualified names like "table.column")
        start = character
        while start > 0 and self._is_word_char(line[start - 1]):
            start -= 1
        
        return line[start:character]
    
    def _is_word_char(self, char: str) -> bool:
        """Check if character is part of a word (including dots for qualified names)."""
        return char.isalnum() or char == '_' or char == '.'


# Singleton instance
completion_service = CompletionService()


__all__ = [
    "CompletionService",
    "completion_service",
    "MetadataProvider",
    "MockMetadataProvider",
    "SQLContext",
]
