"""
Syntax highlighting for tk.Text using Pygments.
Applies VS Code Dark+ inspired colours as text tags.
"""
import tkinter as tk

from pygments import lex
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.token import Token
from pygments.util import ClassNotFound

# ── VS Code Dark+ colour map ───────────────────────────────────────────────────
# Maps Pygments token categories -> hex colour
_COLOURS: dict[object, str] = {
    Token.Keyword:                  '#569CD6',   # blue       — if, class, def
    Token.Keyword.Namespace:        '#C586C0',   # pink       — import, from
    Token.Keyword.Type:             '#4EC9B0',   # teal       — type names
    Token.Keyword.Constant:         '#569CD6',   # blue       — True/False/None
    Token.Name.Builtin:             '#DCDCAA',   # yellow     — print, len, range
    Token.Name.Builtin.Pseudo:      '#569CD6',   # blue       — self, cls
    Token.Name.Class:               '#4EC9B0',   # teal       — class names
    Token.Name.Function:            '#DCDCAA',   # yellow     — function names
    Token.Name.Function.Magic:      '#DCDCAA',   # yellow     — __init__ etc
    Token.Name.Decorator:           '#DCDCAA',   # yellow     — @decorator
    Token.Name.Namespace:           '#4EC9B0',   # teal       — module names
    Token.Name.Exception:           '#4EC9B0',   # teal       — Exception
    Token.Name.Tag:                 '#569CD6',   # blue       — HTML tags
    Token.Name.Attribute:           '#9CDCFE',   # light blue — HTML attrs
    Token.String:                   '#CE9178',   # orange     — strings
    Token.String.Doc:               '#6A9955',   # green      — docstrings
    Token.String.Interpol:          '#CE9178',   # orange
    Token.Number:                   '#B5CEA8',   # light green— numbers
    Token.Number.Integer:           '#B5CEA8',
    Token.Number.Float:             '#B5CEA8',
    Token.Number.Hex:               '#B5CEA8',
    Token.Comment:                  '#6A9955',   # green      — comments
    Token.Comment.Single:           '#6A9955',
    Token.Comment.Multiline:        '#6A9955',
    Token.Comment.Preproc:          '#C586C0',   # pink       — preprocessor
    Token.Operator:                 '#D4D4D4',   # white
    Token.Operator.Word:            '#569CD6',   # blue       — and, or, not
    Token.Punctuation:              '#D4D4D4',   # white
    Token.Name:                     '#9CDCFE',   # light blue — variables
    Token.Text:                     '#D4D4D4',   # default
    Token.Literal:                  '#CE9178',
    Token.Error:                    '#F44747',   # red
}

_DEFAULT_FG = '#D4D4D4'
_REGISTERED: set[str] = set()  # widgets that already have tags configured


def _tag_for(ttype) -> str:
    """Walk up the token hierarchy until we find a colour mapping."""
    while ttype is not Token:
        if ttype in _COLOURS:
            return str(ttype)
        ttype = ttype.parent
    return 'hl_default'


def configure_tags(widget: tk.Text) -> None:
    """Register all highlight tags on a tk.Text widget (call once per widget)."""
    wid = str(widget)
    if wid in _REGISTERED:
        return
    _REGISTERED.add(wid)

    widget.tag_configure('hl_default', foreground=_DEFAULT_FG)
    for ttype, colour in _COLOURS.items():
        widget.tag_configure(str(ttype), foreground=colour)


def highlight_block(widget: tk.Text, start_index: str, code: str, filename: str) -> None:
    """
    Apply syntax highlighting to a block of `code` already inserted into
    `widget` starting at `start_index` (e.g. '3.0').

    Call AFTER inserting the text so existing content is preserved.
    """
    configure_tags(widget)

    try:
        lexer = get_lexer_for_filename(filename, stripall=False)
    except ClassNotFound:
        lexer = TextLexer()

    # Walk tokens and apply tags character-by-character via index arithmetic
    line, col = _parse_index(start_index)

    for ttype, value in lex(code, lexer):
        tag = _tag_for(ttype)
        end_line, end_col = _advance(line, col, value)
        s = f'{line}.{col}'
        e = f'{end_line}.{end_col}'
        if tag != 'hl_default':
            widget.tag_add(tag, s, e)
        line, col = end_line, end_col


def _parse_index(index: str) -> tuple[int, int]:
    parts = index.split('.')
    return int(parts[0]), int(parts[1])


def _advance(line: int, col: int, text: str) -> tuple[int, int]:
    for ch in text:
        if ch == '\n':
            line += 1
            col = 0
        else:
            col += 1
    return line, col