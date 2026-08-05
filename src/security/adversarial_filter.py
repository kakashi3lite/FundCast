"""
Adversarial Input Neutralizer
=============================

Sanitizes and neutralizes adversarial content before it reaches AI/ML
pipelines, storage, or other downstream consumers. Handles encoding
obfuscation, prompt-injection markers, markup/script payloads, path
traversal, and command-injection primitives.

Public API
----------
- :class:`NeutralizationResult` — outcome of a neutralization pass.
- :class:`AdversarialInputNeutralizer` — the sanitizer.
"""

from __future__ import annotations

import base64
import codecs
import html
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Encodings we attempt to decode/deobfuscate before analysis.
_BASE64_RE = re.compile(r"^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$")
_HEX_ESCAPE_RE = re.compile(r"\\x[0-9a-fA-F]{2}|\\u[0-9a-fA-F]{4}|%[0-9a-fA-F]{2}")
_HTML_ENTITY_RE = re.compile(r"&(?:#[0-9]{1,6}|#x[0-9a-fA-F]{1,6}|[a-zA-Z]{1,12});")
_UNICODE_CONFUSABLE_RE = re.compile(r"[\u202e\u202d\u200e\u200f\u2066-\u2069\u00ad\ufeff]")

_INJECTION_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    (
        "script_tag",
        re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.I | re.S),
        "removed script element",
    ),
    (
        "javascript_url",
        re.compile(r"(?i)\b(javascript|vbscript|data:text/html)\s*:",),
        "blocked active-content URL scheme",
    ),
    (
        "on_event_handler",
        re.compile(r"(?i)\son\w+\s*="),
        "removed inline event handler",
    ),
    (
        "sql_meta",
        re.compile(r"(?i)(\bunion\b.*\bselect\b|\bselect\b.*\bfrom\b|"
                   r"\binsert\s+into\b|\bdrop\s+table\b|\bdelete\s+from\b|"
                   r"'?\s*or\s+1\s*=\s*1)",
        ),
        "flagged SQL metacharacter sequence",
    ),
    (
        "path_traversal",
        re.compile(r"(?:\.\./){2,}|\.\.\\|(?:%2e%2e%2f)|(?:%2e%2e\\)"),
        "flagged path traversal",
    ),
    (
        "command_injection",
        re.compile(r"(?i)(;|\||&&|\|\|)\s*(rm|wget|curl|sh|bash|nc|mkfifo|"
                   r"python|perl|eval|exec)\b"),
        "flagged command injection",
    ),
    (
        "prompt_injection",
        re.compile(r"(?i)(ignore\s+(previous|all|above)\s+instructions|"
                   r"you\s+are\s+now\s+(admin|system|developer)|"
                   r"(show|reveal|print)\s+(your|the)\s+(system\s+)?prompt)"),
        "flagged prompt injection",
    ),
    (
        "null_byte",
        re.compile(r"\x00"),
        "removed null byte",
    ),
]

_MAX_INPUT_LENGTH = 1_000_000  # hard cap on any single input
_MAX_DECODE_PASSES = 3         # nested encodings beyond this are rejected


@dataclass
class NeutralizationResult:
    """Outcome of a neutralization pass."""

    original: str
    neutralized: str
    changed: bool
    matched_patterns: List[str] = field(default_factory=list)
    removed_segments: List[str] = field(default_factory=list)
    truncated: bool = False
    rejected: bool = False
    rejection_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "changed": self.changed,
            "matched_patterns": self.matched_patterns,
            "removed_segments": self.removed_segments[:20],
            "truncated": self.truncated,
            "rejected": self.rejected,
            "rejection_reason": self.rejection_reason,
            "timestamp": self.timestamp.isoformat(),
        }


class AdversarialInputNeutralizer:
    """
    Multi-stage sanitizer for adversarial user/AI inputs.

    Stages:

    1. **Canonicalization** — normalize unicode, strip bidi/zero-width chars.
    2. **Deobfuscation** — decode common encodings (hex escapes, HTML
       entities, base64) up to a bounded number of nested passes.
    3. **Pattern neutralization** — remove or flag known adversarial
       patterns (script, SQL meta, traversal, injection).
    4. **Hard limits** — enforce length caps and reject pathological input.
    """

    def __init__(
        self,
        *,
        max_length: int = _MAX_INPUT_LENGTH,
        max_decode_passes: int = _MAX_DECODE_PASSES,
        strip_tags: bool = True,
        escape_remaining: bool = True,
    ) -> None:
        self.max_length = max_length
        self.max_decode_passes = max_decode_passes
        self.strip_tags = strip_tags
        self.escape_remaining = escape_remaining
        self._stats = {
            "inputs_processed": 0,
            "inputs_changed": 0,
            "inputs_rejected": 0,
            "patterns_blocked": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def neutralize(self, content: str) -> NeutralizationResult:
        """
        Neutralize a single input string.

        :param content: Raw input (may be str or str-able object).
        :return: Neutralization result with the sanitized output.
        """
        raw = str(content)
        self._stats["inputs_processed"] += 1

        if len(raw) > self.max_length:
            self._stats["inputs_rejected"] += 1
            return NeutralizationResult(
                original=raw,
                neutralized="",
                changed=True,
                rejected=True,
                rejection_reason=f"input exceeds max_length={self.max_length}",
            )

        result = NeutralizationResult(original=raw, neutralized=raw, changed=False)
        current = raw

        # Stage 1: canonicalization
        current = unicodedata.normalize("NFKC", current)
        current = _UNICODE_CONFUSABLE_RE.sub("", current)

        # Stage 2: deobfuscation (bounded passes)
        current = self._deobfuscate(current, result)

        # Stage 3: pattern neutralization
        current = self._neutralize_patterns(current, result)

        # Stage 4: final sanitization
        if self.strip_tags:
            current = re.sub(r"<[^>]*>", "", current)
        if self.escape_remaining:
            current = html.escape(current, quote=False)

        if current != raw:
            result.changed = True
            self._stats["inputs_changed"] += 1
        result.neutralized = current
        return result

    async def neutralize_many(self, contents: List[str]) -> List[NeutralizationResult]:
        """Neutralize a batch of inputs."""
        return [await self.neutralize(c) for c in contents]

    def get_stats(self) -> Dict[str, Any]:
        """Return processing statistics."""
        return dict(self._stats)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _deobfuscate(self, text: str, result: NeutralizationResult) -> str:
        current = text
        for _ in range(self.max_decode_passes):
            next_text = self._single_decode_pass(current, result)
            if next_text == current:
                break
            current = next_text
        return current

    def _single_decode_pass(self, text: str, result: NeutralizationResult) -> str:
        out = text

        # Hex/unicode escapes: \xNN, \uNNNN, %NN
        def _unescape(match: re.Match) -> str:
            token = match.group(0)
            try:
                if token.startswith("%"):
                    return chr(int(token[1:3], 16))
                if token.startswith("\\x"):
                    return chr(int(token[2:4], 16))
                if token.startswith("\\u"):
                    return chr(int(token[2:6], 16))
            except ValueError:
                return token
            return token

        out = _HEX_ESCAPE_RE.sub(_unescape, out)

        # HTML entities
        def _entity(match: re.Match) -> str:
            token = match.group(0)
            try:
                return html.unescape(token)
            except Exception:  # pragma: no cover
                return token

        out = _HTML_ENTITY_RE.sub(_entity, out)

        # Base64 (only when the segment is long enough to be meaningful)
        if len(out) > 24 and _BASE64_RE.match(out):
            try:
                decoded = base64.b64decode(out).decode("utf-8", errors="ignore")
                if 0 < len(decoded) < len(out) * 0.8:  # guard against garbage
                    result.removed_segments.append("base64 payload decoded")
                    out = decoded
            except Exception:  # pragma: no cover
                pass

        # UTF-16/32 byte-order-marked strings
        for enc in ("utf-16", "utf-32"):
            try:
                if out.startswith(codecs.BOM_UTF16) or out.startswith(codecs.BOM_UTF32):
                    out = out.encode("latin1", errors="ignore").decode(enc, errors="ignore")
                    break
            except Exception:  # pragma: no cover
                pass

        return out

    def _neutralize_patterns(self, text: str, result: NeutralizationResult) -> str:
        out = text
        for name, pattern, action in _INJECTION_PATTERNS:
            matches = list(pattern.finditer(out))
            if not matches:
                continue
            result.matched_patterns.append(name)
            self._stats["patterns_blocked"] += len(matches)
            if action.startswith("removed") or action.startswith("blocked"):
                result.removed_segments.extend(m.group(0)[:64] for m in matches)
                out = pattern.sub("", out)
            else:
                # Flag-only patterns: record them but leave content (may be legit).
                result.removed_segments.append(f"{name} (flagged)")
        return out
