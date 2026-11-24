"""Resumo de um arquivo C#: nome do arquivo, classe principal e comentários associados.

Análise léxica (não regex única): comentários, strings regulares/verbatim/
interpoladas/raw e caracteres são reconhecidos antes de procurar declarações, então
`"class"` dentro de uma string não vira classe. Corpos de métodos e comentários
internos não entram no resumo.

Limites conhecidos (heurística, sem parser completo): interpolação com strings
aninhadas em vários níveis, diretivas #if que duplicam declarações e sintaxe
incompleta durante a edição podem deslocar a classe escolhida; nesses casos o
arquivo continua indexado pelo nome.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

TYPE_KEYWORDS = {"class", "struct", "interface", "record", "enum"}
MODIFIERS = {
    "public", "internal", "private", "protected", "sealed", "abstract", "static", "partial", "unsafe",
    "new", "file", "readonly", "ref",
}
NOT_NAMES = {"where", "new", "class", "struct"}


@dataclass
class Comment:
    text: str
    doc: bool
    line: int
    next_token: int  # índice do próximo token significativo


@dataclass
class Token:
    text: str
    line: int
    depth: int


@dataclass
class TypeDecl:
    kind: str
    name: str
    line: int
    top_level: bool
    start_token: int
    comments: list[Comment] = field(default_factory=list)


@dataclass
class CSharpSummary:
    filename: str
    main_class: str | None
    header: str
    class_doc: str
    types: list[TypeDecl]

    @property
    def description(self) -> str:
        parts = [p for p in (self.header, self.class_doc) if p]
        if len(parts) == 2 and (parts[0] in parts[1] or parts[1] in parts[0]):
            parts = [max(parts, key=len)]
        return " ".join(parts)

    def text(self, description: str | None = None) -> str:
        desc = self.description if description is None else description
        base = f"Arquivo: {self.filename}. Classe: {self.main_class or 'nenhuma classe encontrada'}."
        return f"{base} Descrição: {desc}" if desc else base


def _skip_string(src: str, i: int) -> int:
    """i aponta para o primeiro caractere do literal ($, @ ou aspas). Retorna o índice após ele."""
    n = len(src)
    j = i
    dollars = 0
    verbatim = False
    while j < n and src[j] in "$@":
        if src[j] == "$":
            dollars += 1
        else:
            verbatim = True
        j += 1
    if j >= n or src[j] != '"':
        return i + 1
    quotes = 0
    while j + quotes < n and src[j + quotes] == '"':
        quotes += 1
    if quotes >= 3:  # raw string literal: termina com a mesma quantidade de aspas
        end = src.find('"' * quotes, j + quotes)
        return n if end < 0 else end + quotes
    if quotes == 2 and not verbatim:  # "" vazio
        return j + 2
    j += 1
    while j < n:
        ch = src[j]
        if verbatim:
            if ch == '"':
                if j + 1 < n and src[j + 1] == '"':
                    j += 2
                    continue
                return j + 1
        else:
            if ch == "\\":
                j += 2
                continue
            if ch == '"':
                return j + 1
            if ch == "\n":  # literal incompleto durante a edição
                return j
        if dollars and ch == "{":
            if j + 1 < n and src[j + 1] == "{":
                j += 2
                continue
            j = _skip_hole(src, j + 1)
            continue
        j += 1
    return n


def _skip_hole(src: str, i: int) -> int:
    depth = 1
    n = len(src)
    while i < n and depth:
        ch = src[i]
        if ch in "$@\"":
            if ch == '"' or (i + 1 < n and src[i + 1] in '"$@'):
                i = _skip_string(src, i)
                continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif ch == "\n":
            return i
        i += 1
    return i


def tokenize(src: str) -> tuple[list[Token], list[Comment]]:
    tokens: list[Token] = []
    comments: list[Comment] = []
    pending: list[tuple[str, bool, int]] = []
    i, n, line, depth = 0, len(src), 1, 0
    at_line_start = True

    def flush() -> None:
        for text, doc, ln in pending:
            comments.append(Comment(text, doc, ln, len(tokens)))
        pending.clear()

    while i < n:
        ch = src[i]
        if ch == "\n":
            line += 1
            i += 1
            at_line_start = True
            continue
        if ch in " \t\r\f﻿":
            i += 1
            continue
        if ch == "#" and at_line_start:  # diretiva de pré-processador
            end = src.find("\n", i)
            i = n if end < 0 else end
            continue
        at_line_start = False
        if src.startswith("//", i):
            end = src.find("\n", i)
            end = n if end < 0 else end
            raw = src[i:end]
            pending.append((raw, raw.startswith("///") and not raw.startswith("////"), line))
            i = end
            continue
        if src.startswith("/*", i):
            end = src.find("*/", i + 2)
            end = n if end < 0 else end + 2
            raw = src[i:end]
            pending.append((raw, raw.startswith("/**") and not raw.startswith("/**/"), line))
            line += raw.count("\n")
            i = end
            continue
        if ch == '"' or (ch in "$@" and i + 1 < n and src[i + 1] in '"$@'):
            end = _skip_string(src, i)
            line += src.count("\n", i, end)
            if pending:
                flush()
            tokens.append(Token('""', line, depth))
            i = end
            continue
        if ch == "'":
            match = re.match(r"'(?:\\.[^'\n]{0,8}|[^'\\\n])'", src[i:i + 12])
            i += match.end() if match else 1
            if pending:
                flush()
            tokens.append(Token("''", line, depth))
            continue
        if ch.isalpha() or ch == "_" or (ch == "@" and i + 1 < n and (src[i + 1].isalpha() or src[i + 1] == "_")):
            j = i + 1
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            if pending:
                flush()
            tokens.append(Token(src[i:j].lstrip("@"), line, depth))
            i = j
            continue
        if pending:
            flush()
        if ch == "}":
            depth = max(0, depth - 1)
        tokens.append(Token(ch, line, depth))
        if ch == "{":
            depth += 1
        i += 1
    flush()
    return tokens, comments


def _clean_comment(raw: str) -> str:
    text = raw
    if text.startswith("/*"):
        text = text[2:-2] if text.endswith("*/") else text[2:]
        text = "\n".join(re.sub(r"^\s*\*+ ?", "", ln) for ln in text.split("\n"))
    else:
        text = re.sub(r"^/{2,}\s?", "", text)
    text = re.sub(r'<(?:see|seealso|paramref|typeparamref)\s+(?:cref|name|langword)="([^"]+)"\s*/>', r"\1", text)
    text = re.sub(r'<param\s+name="([^"]+)">', r"\1: ", text)
    text = re.sub(r"</?[a-zA-Z][^>]*>", " ", text)
    return " ".join(text.split())


def _decl_start(tokens: list[Token], keyword_index: int) -> int:
    k = keyword_index - 1
    while k >= 0:
        text = tokens[k].text
        if text in MODIFIERS:
            k -= 1
            continue
        if text == "]":  # grupo de atributos: volta até o [ correspondente
            depth = 0
            while k >= 0:
                if tokens[k].text == "]":
                    depth += 1
                elif tokens[k].text == "[":
                    depth -= 1
                    if depth == 0:
                        break
                k -= 1
            k -= 1
            continue
        break
    return k + 1


def summarize(src: str, filename: str) -> CSharpSummary:
    tokens, comments = tokenize(src)
    stack: list[str] = []  # tipo de cada { aberto: namespace | type | other
    pending_brace: str | None = None
    types: list[TypeDecl] = []
    for index, token in enumerate(tokens):
        text = token.text
        if text == "namespace":
            pending_brace = "namespace"
        elif text in TYPE_KEYWORDS and index + 1 < len(tokens):
            name_index = index + 1
            if text == "record" and tokens[name_index].text in {"class", "struct"}:
                name_index += 1
            if text in {"class", "struct"} and index > 0 and tokens[index - 1].text == "record":
                continue  # já tratado por "record"
            name = tokens[name_index].text if name_index < len(tokens) else ""
            if re.match(r"^[A-Za-z_]\w*$", name) and name not in NOT_NAMES:
                top = all(kind == "namespace" for kind in stack)
                start = _decl_start(tokens, index)
                types.append(TypeDecl("class" if text == "record" else text, name, token.line, top, start))
                pending_brace = "type"
        elif text == ";" and pending_brace == "namespace":
            pending_brace = None  # namespace com escopo de arquivo
        elif text == "{":
            stack.append(pending_brace or "other")
            pending_brace = None
        elif text == "}":
            if stack:
                stack.pop()
    by_next: dict[int, list[Comment]] = {}
    for comment in comments:
        by_next.setdefault(comment.next_token, []).append(comment)
    for decl in types:
        decl.comments = by_next.get(decl.start_token, [])
    stem = Path(filename).stem
    top_level = [t for t in types if t.top_level]
    main = next((t for t in top_level if t.name == stem), None)
    main = main or next((t for t in top_level if t.kind == "class"), None) or (top_level[0] if top_level else None)
    header_comments = by_next.get(0, []) if not (main and main.start_token == 0) else []
    header = " ".join(filter(None, (_clean_comment(c.text) for c in header_comments)))
    class_doc = ""
    if main:
        docs = [c for c in main.comments if c.doc] or main.comments
        class_doc = " ".join(filter(None, (_clean_comment(c.text) for c in docs)))
    return CSharpSummary(Path(filename).name, main.name if main else None, header, class_doc, types)
