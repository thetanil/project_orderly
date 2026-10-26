"""Stored text is Markdown. Detect raw HTML (R22) and convert it (quick fix)."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import List

MARKDOWN_FIELDS = ("description", "acceptanceCriteria", "localNotes")

_FENCE = re.compile(r"(```|~~~).*?(\1|\Z)", re.S)
_CODE = re.compile(r"`[^`\n]*`")
_TAG = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9-]*)((?:\s[^<>]*)?)(/?)>|<!--.*?-->", re.S)


def has_html(text: str) -> bool:
    text = _CODE.sub("", _FENCE.sub("", text))
    return _TAG.search(text) is not None


class _ToMarkdown(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: List[str] = []
        self.lists: List[List] = []  # [ordered?, counter]
        self.href: List[str] = []

    def w(self, s: str) -> None:
        self.out.append(s)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("b", "strong"):
            self.w("**")
        elif tag in ("i", "em"):
            self.w("*")
        elif tag == "code":
            self.w("`")
        elif tag == "pre":
            self.w("\n```\n")
        elif tag == "br":
            self.w("  \n")
        elif tag in ("p", "div"):
            self.w("\n\n")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.w("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in ("ul", "ol"):
            self.lists.append([tag == "ol", 0])
            self.w("\n")
        elif tag == "li":
            depth = max(len(self.lists) - 1, 0)
            if self.lists and self.lists[-1][0]:
                self.lists[-1][1] += 1
                mark = f"{self.lists[-1][1]}. "
            else:
                mark = "- "
            self.w("\n" + "  " * depth + mark)
        elif tag == "a":
            self.href.append(a.get("href") or "")
            self.w("[")

    def handle_endtag(self, tag):
        if tag in ("b", "strong"):
            self.w("**")
        elif tag in ("i", "em"):
            self.w("*")
        elif tag == "code":
            self.w("`")
        elif tag == "pre":
            self.w("\n```\n")
        elif tag in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.w("\n\n")
        elif tag in ("ul", "ol"):
            if self.lists:
                self.lists.pop()
            self.w("\n")
        elif tag == "a" and self.href:
            self.w(f"]({self.href.pop()})")

    def handle_data(self, data):
        self.w(data)


def html_to_markdown(text: str) -> str:
    """Best-effort HTML -> GFM Markdown (lossy; unknown tags are dropped, text kept)."""
    p = _ToMarkdown()
    p.feed(text)
    p.close()
    out = "".join(p.out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()
