/**
 * SQL code completion provider for Monaco Editor.
 */
import * as monaco from 'monaco-editor'
import type { CompletionItem } from '@/api/websocket'

export function convertToMonacoCompletions(
  items: CompletionItem[],
  range: monaco.IRange
): monaco.languages.CompletionItem[] {
  return items.map((item, index) => ({
    label: item.label,
    kind: convertCompletionKind(item.kind),
    detail: item.detail,
    documentation: item.documentation,
    insertText: item.insertText || item.label,
    range,
    sortText: String(index).padStart(5, '0'),
  }))
}

function convertCompletionKind(kind: number): monaco.languages.CompletionItemKind {
  // Map LSP completion kinds to Monaco completion kinds
  const kindMap: Record<number, monaco.languages.CompletionItemKind> = {
    1: monaco.languages.CompletionItemKind.Text,
    2: monaco.languages.CompletionItemKind.Method,
    3: monaco.languages.CompletionItemKind.Function,
    4: monaco.languages.CompletionItemKind.Constructor,
    5: monaco.languages.CompletionItemKind.Field,
    6: monaco.languages.CompletionItemKind.Variable,
    7: monaco.languages.CompletionItemKind.Class,
    8: monaco.languages.CompletionItemKind.Interface,
    9: monaco.languages.CompletionItemKind.Module,
    10: monaco.languages.CompletionItemKind.Property,
    11: monaco.languages.CompletionItemKind.Unit,
    12: monaco.languages.CompletionItemKind.Value,
    13: monaco.languages.CompletionItemKind.Enum,
    14: monaco.languages.CompletionItemKind.Keyword,
    15: monaco.languages.CompletionItemKind.Snippet,
    16: monaco.languages.CompletionItemKind.Color,
    17: monaco.languages.CompletionItemKind.File,
    18: monaco.languages.CompletionItemKind.Reference,
    19: monaco.languages.CompletionItemKind.Folder,
    20: monaco.languages.CompletionItemKind.EnumMember,
    21: monaco.languages.CompletionItemKind.Constant,
    22: monaco.languages.CompletionItemKind.Struct,
    23: monaco.languages.CompletionItemKind.Event,
    24: monaco.languages.CompletionItemKind.Operator,
    25: monaco.languages.CompletionItemKind.TypeParameter,
  }

  return kindMap[kind] || monaco.languages.CompletionItemKind.Text
}

export function getWordRange(
  model: monaco.editor.ITextModel,
  position: monaco.Position
): monaco.IRange {
  const word = model.getWordUntilPosition(position)
  return {
    startLineNumber: position.lineNumber,
    endLineNumber: position.lineNumber,
    startColumn: word.startColumn,
    endColumn: word.endColumn,
  }
}

export function createCompletionProvider(
  requestCompletion: (line: number, character: number) => Promise<CompletionItem[]>
): monaco.languages.CompletionItemProvider {
  return {
    triggerCharacters: ['.', ' ', '('],

    provideCompletionItems: async (
      model: monaco.editor.ITextModel,
      position: monaco.Position
    ): Promise<monaco.languages.CompletionList> => {
      try {
        // Convert Monaco position to LSP position (0-indexed)
        const line = position.lineNumber - 1
        const character = position.column - 1

        const items = await requestCompletion(line, character)
        const range = getWordRange(model, position)

        return {
          suggestions: convertToMonacoCompletions(items, range),
        }
      } catch (error) {
        console.error('Completion error:', error)
        return { suggestions: [] }
      }
    },
  }
}
