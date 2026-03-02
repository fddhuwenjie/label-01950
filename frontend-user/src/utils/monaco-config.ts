/**
 * Monaco Editor configuration and SQL language setup.
 */
import * as monaco from 'monaco-editor'

// SQL Keywords for syntax highlighting
const SQL_KEYWORDS = [
  'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'BETWEEN',
  'LIKE', 'IS', 'NULL', 'TRUE', 'FALSE', 'AS', 'ON', 'JOIN',
  'LEFT', 'RIGHT', 'INNER', 'OUTER', 'FULL', 'CROSS', 'NATURAL',
  'GROUP', 'BY', 'HAVING', 'ORDER', 'ASC', 'DESC', 'LIMIT',
  'OFFSET', 'UNION', 'ALL', 'INTERSECT', 'EXCEPT', 'DISTINCT',
  'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE',
  'TABLE', 'VIEW', 'INDEX', 'DROP', 'ALTER', 'ADD', 'COLUMN',
  'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES', 'UNIQUE', 'CHECK',
  'DEFAULT', 'CONSTRAINT', 'CASCADE', 'RESTRICT', 'TRUNCATE',
  'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'CAST', 'CONVERT',
  'COALESCE', 'NULLIF', 'EXISTS', 'ANY', 'SOME', 'WITH', 'RECURSIVE',
  'OVER', 'PARTITION', 'ROW', 'ROWS', 'RANGE', 'UNBOUNDED',
  'PRECEDING', 'FOLLOWING', 'CURRENT', 'FIRST', 'LAST', 'NULLS',
]

// SQL Functions
const SQL_FUNCTIONS = [
  'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'GROUP_CONCAT',
  'CONCAT', 'SUBSTRING', 'LENGTH', 'UPPER', 'LOWER', 'TRIM',
  'LTRIM', 'RTRIM', 'REPLACE', 'REVERSE', 'SPLIT',
  'NOW', 'CURRENT_DATE', 'CURRENT_TIMESTAMP', 'DATE_ADD', 'DATE_SUB',
  'DATEDIFF', 'DATE_FORMAT', 'YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE', 'SECOND',
  'ABS', 'CEIL', 'FLOOR', 'ROUND', 'MOD', 'POWER', 'SQRT', 'LOG', 'EXP', 'RAND',
  'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'NTILE', 'LAG', 'LEAD',
  'FIRST_VALUE', 'LAST_VALUE', 'IF', 'IFNULL', 'NVL', 'DECODE',
]

// SparkSQL specific
const SPARK_KEYWORDS = [
  'LATERAL', 'EXPLODE', 'POSEXPLODE', 'INLINE', 'STACK',
  'COLLECT_LIST', 'COLLECT_SET', 'ARRAY', 'MAP', 'STRUCT',
  'NAMED_STRUCT', 'GET_JSON_OBJECT', 'FROM_JSON', 'TO_JSON',
  'TRANSFORM', 'FILTER', 'AGGREGATE', 'DISTRIBUTE', 'CLUSTER',
  'SORT', 'TABLESAMPLE', 'PIVOT', 'UNPIVOT',
]

// HiveSQL specific
const HIVE_KEYWORDS = [
  'PARTITIONED', 'CLUSTERED', 'BUCKETS', 'STORED', 'LOCATION',
  'TBLPROPERTIES', 'SERDEPROPERTIES', 'DELIMITED', 'FIELDS',
  'COLLECTION', 'LINES', 'EXTERNAL', 'TEMPORARY', 'MSCK',
  'ANALYZE', 'COMPUTE', 'DESCRIBE', 'SHOW', 'USE', 'OVERWRITE',
  'DIRECTORY', 'PARSE_URL', 'REFLECT', 'XPATH', 'XPATH_STRING',
]

// Data types
const DATA_TYPES = [
  'INT', 'INTEGER', 'BIGINT', 'SMALLINT', 'TINYINT',
  'FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC',
  'VARCHAR', 'CHAR', 'STRING', 'TEXT',
  'DATE', 'DATETIME', 'TIMESTAMP', 'TIME',
  'BOOLEAN', 'BOOL', 'BINARY', 'VARBINARY', 'BLOB',
  'ARRAY', 'MAP', 'STRUCT', 'JSON',
]

export function registerSqlLanguage(): void {
  // Register SQL language with custom tokens
  monaco.languages.register({ id: 'sql' })

  monaco.languages.setMonarchTokensProvider('sql', {
    defaultToken: '',
    tokenPostfix: '.sql',
    ignoreCase: true,

    keywords: [...SQL_KEYWORDS, ...SPARK_KEYWORDS, ...HIVE_KEYWORDS],
    functions: SQL_FUNCTIONS,
    typeKeywords: DATA_TYPES,

    operators: [
      '=', '>', '<', '!', '~', '?', ':',
      '==', '<=', '>=', '!=', '<>', '&&', '||',
      '+', '-', '*', '/', '%', '&', '|', '^',
    ],

    symbols: /[=><!~?:&|+\-*\/\^%]+/,

    escapes: /\\(?:[abfnrtv\\"']|x[0-9A-Fa-f]{1,4}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8})/,

    tokenizer: {
      root: [
        // Identifiers and keywords
        [/[a-zA-Z_$][\w$]*/, {
          cases: {
            '@keywords': 'keyword',
            '@functions': 'function',
            '@typeKeywords': 'type',
            '@default': 'identifier',
          },
        }],

        // Whitespace
        { include: '@whitespace' },

        // Delimiters and operators
        [/[{}()\[\]]/, '@brackets'],
        [/[<>](?!@symbols)/, '@brackets'],
        [/@symbols/, {
          cases: {
            '@operators': 'operator',
            '@default': '',
          },
        }],

        // Numbers
        [/\d*\.\d+([eE][\-+]?\d+)?/, 'number.float'],
        [/\d+/, 'number'],

        // Delimiter
        [/[;,.]/, 'delimiter'],

        // Strings
        [/'([^'\\]|\\.)*$/, 'string.invalid'],
        [/'/, { token: 'string.quote', bracket: '@open', next: '@string_single' }],
        [/"([^"\\]|\\.)*$/, 'string.invalid'],
        [/"/, { token: 'string.quote', bracket: '@open', next: '@string_double' }],

        // Backtick identifiers
        [/`/, { token: 'identifier.quote', bracket: '@open', next: '@identifier' }],
      ],

      string_single: [
        [/[^\\']+/, 'string'],
        [/@escapes/, 'string.escape'],
        [/\\./, 'string.escape.invalid'],
        [/'/, { token: 'string.quote', bracket: '@close', next: '@pop' }],
      ],

      string_double: [
        [/[^\\"]+/, 'string'],
        [/@escapes/, 'string.escape'],
        [/\\./, 'string.escape.invalid'],
        [/"/, { token: 'string.quote', bracket: '@close', next: '@pop' }],
      ],

      identifier: [
        [/[^`]+/, 'identifier'],
        [/`/, { token: 'identifier.quote', bracket: '@close', next: '@pop' }],
      ],

      whitespace: [
        [/[ \t\r\n]+/, 'white'],
        [/--.*$/, 'comment'],
        [/\/\*/, 'comment', '@comment'],
      ],

      comment: [
        [/[^\/*]+/, 'comment'],
        [/\/\*/, 'comment', '@push'],
        [/\*\//, 'comment', '@pop'],
        [/[\/*]/, 'comment'],
      ],
    },
  })

  // Set language configuration
  monaco.languages.setLanguageConfiguration('sql', {
    comments: {
      lineComment: '--',
      blockComment: ['/*', '*/'],
    },
    brackets: [
      ['{', '}'],
      ['[', ']'],
      ['(', ')'],
    ],
    autoClosingPairs: [
      { open: '{', close: '}' },
      { open: '[', close: ']' },
      { open: '(', close: ')' },
      { open: '"', close: '"' },
      { open: "'", close: "'" },
      { open: '`', close: '`' },
    ],
    surroundingPairs: [
      { open: '{', close: '}' },
      { open: '[', close: ']' },
      { open: '(', close: ')' },
      { open: '"', close: '"' },
      { open: "'", close: "'" },
      { open: '`', close: '`' },
    ],
  })
}

export function createEditorOptions(): monaco.editor.IStandaloneEditorConstructionOptions {
  return {
    language: 'sql',
    theme: 'vs-dark',
    fontSize: 14,
    fontFamily: "'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace",
    lineHeight: 22,
    minimap: { enabled: true },
    scrollBeyondLastLine: false,
    automaticLayout: true,
    tabSize: 2,
    insertSpaces: true,
    wordWrap: 'on',
    lineNumbers: 'on',
    renderLineHighlight: 'all',
    selectOnLineNumbers: true,
    roundedSelection: true,
    cursorStyle: 'line',
    cursorBlinking: 'smooth',
    smoothScrolling: true,
    contextmenu: true,
    folding: true,
    foldingStrategy: 'indentation',
    showFoldingControls: 'mouseover',
    matchBrackets: 'always',
    autoIndent: 'full',
    formatOnPaste: true,
    formatOnType: true,
    suggestOnTriggerCharacters: true,
    acceptSuggestionOnEnter: 'on',
    snippetSuggestions: 'inline',
    wordBasedSuggestions: 'currentDocument',
    quickSuggestions: {
      other: true,
      comments: false,
      strings: false,
    },
    parameterHints: {
      enabled: true,
    },
    suggest: {
      showKeywords: true,
      showSnippets: true,
      showFunctions: true,
      showVariables: true,
    },
  }
}

export function getSeverityClass(severity: number): monaco.MarkerSeverity {
  switch (severity) {
    case 1:
      return monaco.MarkerSeverity.Error
    case 2:
      return monaco.MarkerSeverity.Warning
    case 3:
      return monaco.MarkerSeverity.Info
    case 4:
      return monaco.MarkerSeverity.Hint
    default:
      return monaco.MarkerSeverity.Info
  }
}
