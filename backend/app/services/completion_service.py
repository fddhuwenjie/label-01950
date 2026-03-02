"""
SQL code completion service.
"""
from typing import List, Optional

from ..core import logger
from ..models import CompletionItem, CompletionItemKind


class CompletionService:
    """Service for SQL code completion suggestions."""
    
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
    
    def __init__(self):
        self._completion_cache: dict = {}
        logger.info("CompletionService initialized")
    
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
        Get completion suggestions for the given position.
        
        Args:
            text: Full document text.
            line: Current line number (0-indexed).
            character: Current character position (0-indexed).
            dialect: SQL dialect.
            
        Returns:
            List of completion items.
        """
        # Get the current word being typed
        lines = text.split('\n')
        if line >= len(lines):
            return []
        
        current_line = lines[line]
        prefix = self._get_word_prefix(current_line, character)
        
        logger.debug(f"Getting completions for prefix: '{prefix}', dialect: {dialect}")
        
        # Build all completions
        all_items = []
        all_items.extend(self._build_keyword_completions())
        all_items.extend(self._build_function_completions())
        all_items.extend(self._build_type_completions())
        all_items.extend(self._build_dialect_completions(dialect))
        
        # Filter by prefix
        if prefix:
            prefix_upper = prefix.upper()
            filtered_items = [
                item for item in all_items
                if item.label.upper().startswith(prefix_upper)
            ]
        else:
            filtered_items = all_items
        
        logger.debug(f"Returning {len(filtered_items)} completion items")
        return filtered_items[:50]  # Limit results
    
    def _get_word_prefix(self, line: str, character: int) -> str:
        """
        Extract the word prefix at the given position.
        
        Args:
            line: Current line text.
            character: Character position.
            
        Returns:
            Word prefix string.
        """
        if character > len(line):
            character = len(line)
        
        # Find word start
        start = character
        while start > 0 and self._is_word_char(line[start - 1]):
            start -= 1
        
        return line[start:character]
    
    def _is_word_char(self, char: str) -> bool:
        """Check if character is part of a word."""
        return char.isalnum() or char == '_'


# Singleton instance
completion_service = CompletionService()


__all__ = ["CompletionService", "completion_service"]
