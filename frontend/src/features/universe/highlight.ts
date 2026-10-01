export type TokenKind = "comment" | "string" | "keyword" | "number" | "plain";

export interface Token {
  text: string;
  kind: TokenKind;
}

const KEYWORDS = new Set([
  "import", "from", "as", "def", "return", "if", "else", "elif", "for", "in", "not", "and", "or",
  "lambda", "None", "True", "False", "with", "while", "is",
]);

const PATTERN = /(#[^\n]*)|("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')|\b(\d+(?:\.\d+)?)\b|\b([A-Za-z_]\w*)\b/g;

export function tokenize(code: string): Token[] {
  const tokens: Token[] = [];
  let cursor = 0;
  for (const match of code.matchAll(PATTERN)) {
    const start = match.index ?? 0;
    if (start > cursor) tokens.push({ text: code.slice(cursor, start), kind: "plain" });
    const [text, comment, string, number, word] = match;
    if (comment) tokens.push({ text, kind: "comment" });
    else if (string) tokens.push({ text, kind: "string" });
    else if (number) tokens.push({ text, kind: "number" });
    else tokens.push({ text, kind: word && KEYWORDS.has(word) ? "keyword" : "plain" });
    cursor = start + text.length;
  }
  if (cursor < code.length) tokens.push({ text: code.slice(cursor), kind: "plain" });
  return tokens;
}
