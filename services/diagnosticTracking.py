"""Diagnostic tracking service — mirrors src/services/diagnosticTracking.ts."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class DiagnosticRange:
    start: dict  # {line, character}
    end: dict    # {line, character}


@dataclass
class Diagnostic:
    message: str
    severity: str  # 'Error' | 'Warning' | 'Info' | 'Hint'
    range: dict
    source: Optional[str] = None
    code: Optional[str] = None


@dataclass
class DiagnosticFile:
    uri: str
    diagnostics: list[Diagnostic]


MAX_DIAGNOSTICS_SUMMARY_CHARS = 4000


class DiagnosticTrackingService:
    """Tracks LSP diagnostics for changed files.

    Mirrors DiagnosticTrackingService from diagnosticTracking.ts.
    """

    _instance: Optional["DiagnosticTrackingService"] = None

    def __init__(self) -> None:
        self._baseline: dict[str, list[Diagnostic]] = {}
        self._initialized = False
        self._mcp_client: Any = None
        self._last_processed_timestamps: dict[str, float] = {}
        self._right_file_diagnostics_state: dict[str, list[Diagnostic]] = {}

    @classmethod
    def getInstance(cls) -> "DiagnosticTrackingService":
        """Get the singleton instance.

        Mirrors DiagnosticTrackingService.getInstance() from diagnosticTracking.ts.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self, mcp_client: Any = None) -> None:
        """Initialize with an MCP client connection.

        Mirrors initialize() from DiagnosticTrackingService.
        """
        if self._initialized:
            return
        self._mcp_client = mcp_client
        self._initialized = True

    async def shutdown(self) -> None:
        """Shut down the service."""
        self._initialized = False
        self._baseline.clear()
        self._right_file_diagnostics_state.clear()
        self._last_processed_timestamps.clear()

    def reset(self) -> None:
        """Reset tracking state while keeping the service initialized."""
        self._baseline.clear()
        self._right_file_diagnostics_state.clear()
        self._last_processed_timestamps.clear()

    def _normalize_file_uri(self, file_uri: str) -> str:
        protocol_prefixes = ["file://", "_vivian_fs_right:", "_vivian_fs_left:"]
        normalized = file_uri
        for prefix in protocol_prefixes:
            if file_uri.startswith(prefix):
                normalized = file_uri[len(prefix):]
                break
        normalized = normalized.replace("\\", "/")
        if len(normalized) >= 2 and normalized[1] == ":":
            normalized = normalized[0].lower() + normalized[1:]
        return normalized

    def _paths_equal(self, left: str, right: str) -> bool:
        return self._normalize_file_uri(left) == self._normalize_file_uri(right)

    async def _call_ide_rpc(self, method: str, params: dict) -> Any:
        client = self._mcp_client
        if client is None:
            return None

        for attr in ("call_ide_rpc", "callIdeRpc", "call_rpc", "callRpc", "request"):
            fn = getattr(client, attr, None)
            if callable(fn):
                result = fn(method, params)
                return await result if hasattr(result, "__await__") else result

        for attr in ("call_tool", "callTool"):
            fn = getattr(client, attr, None)
            if callable(fn):
                result = fn(method, params)
                return await result if hasattr(result, "__await__") else result
        return None

    async def get_diagnostics_for_file(self, file_uri: str) -> list[Diagnostic]:
        """Get current diagnostics for a file."""
        if not self._initialized or self._mcp_client is None:
            return []
        result = await self._call_ide_rpc("getDiagnostics", {"uri": file_uri})
        parsed = self._parse_diagnostic_result(result)
        if not parsed:
            return []
        return parsed[0].diagnostics

    async def set_baseline(self, files: list[str]) -> None:
        """Set the diagnostic baseline for the given files."""
        for file_path in files:
            file_uri = file_path if "://" in file_path or file_path.startswith("_") else f"file://{file_path}"
            diagnostics = await self.get_diagnostics_for_file(file_uri)
            normalized = self._normalize_file_uri(file_uri)
            self._baseline[normalized] = diagnostics

    async def get_new_diagnostics(self, files: list[str]) -> list[DiagnosticFile]:
        """Get diagnostics that appeared since the baseline was set."""
        results: list[DiagnosticFile] = []
        for file_path in files:
            file_uri = file_path if "://" in file_path or file_path.startswith("_") else f"file://{file_path}"
            current = await self.get_diagnostics_for_file(file_uri)
            normalized = self._normalize_file_uri(file_uri)
            baseline = self._baseline.get(normalized, [])
            new_items = [item for item in current if not any(self._diagnostics_equal(item, old) for old in baseline)]
            if new_items:
                results.append(DiagnosticFile(uri=file_uri, diagnostics=new_items))
            self._baseline[normalized] = current
        return results

    async def ensureFileOpened(self, file_uri: str) -> None:
        if not self._initialized or self._mcp_client is None:
            return
        try:
            await self._call_ide_rpc(
                "openFile",
                {
                    "filePath": file_uri,
                    "preview": False,
                    "startText": "",
                    "endText": "",
                    "selectToEndOfLine": False,
                    "makeFrontmost": False,
                },
            )
        except Exception:
            return

    async def beforeFileEdited(self, file_path: str) -> None:
        file_uri = file_path if file_path.startswith("file://") else f"file://{file_path}"
        diagnostics = await self.get_diagnostics_for_file(file_uri)
        self._baseline[self._normalize_file_uri(file_uri)] = diagnostics

    async def getNewDiagnostics(self) -> list[DiagnosticFile]:
        if not self._initialized or self._mcp_client is None:
            return []
        result = await self._call_ide_rpc("getDiagnostics", {})
        all_files = self._parse_diagnostic_result(result)
        output: list[DiagnosticFile] = []
        for diagnostic_file in all_files:
            normalized = self._normalize_file_uri(diagnostic_file.uri)
            if normalized not in self._baseline:
                continue
            baseline = self._baseline.get(normalized, [])
            new_items = [
                item
                for item in diagnostic_file.diagnostics
                if not any(self._diagnostics_equal(item, old) for old in baseline)
            ]
            if new_items:
                output.append(DiagnosticFile(uri=diagnostic_file.uri, diagnostics=new_items))
            self._baseline[normalized] = list(diagnostic_file.diagnostics)
        return output

    def _parse_diagnostic_result(self, result: Any) -> list[DiagnosticFile]:
        payload = result
        if isinstance(result, list):
            text_block = next(
                (
                    block.get("text")
                    for block in result
                    if isinstance(block, dict) and block.get("type") == "text"
                ),
                None,
            )
            if isinstance(text_block, str):
                try:
                    payload = json.loads(text_block)
                except Exception:
                    payload = []

        if not isinstance(payload, list):
            return []

        parsed: list[DiagnosticFile] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            diagnostics_raw = item.get("diagnostics", [])
            diagnostics: list[Diagnostic] = []
            if isinstance(diagnostics_raw, list):
                for diagnostic in diagnostics_raw:
                    if not isinstance(diagnostic, dict):
                        continue
                    diagnostics.append(
                        Diagnostic(
                            message=str(diagnostic.get("message", "")),
                            severity=str(diagnostic.get("severity", "Info")),
                            range=diagnostic.get("range", {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}}),
                            source=diagnostic.get("source"),
                            code=str(diagnostic.get("code")) if diagnostic.get("code") is not None else None,
                        )
                    )
            parsed.append(DiagnosticFile(uri=str(item.get("uri", "")), diagnostics=diagnostics))
        return parsed

    def _diagnostics_equal(self, left: Diagnostic, right: Diagnostic) -> bool:
        left_start = left.range.get("start", {}) if isinstance(left.range, dict) else {}
        left_end = left.range.get("end", {}) if isinstance(left.range, dict) else {}
        right_start = right.range.get("start", {}) if isinstance(right.range, dict) else {}
        right_end = right.range.get("end", {}) if isinstance(right.range, dict) else {}
        return (
            left.message == right.message
            and left.severity == right.severity
            and left.source == right.source
            and left.code == right.code
            and left_start.get("line") == right_start.get("line")
            and left_start.get("character") == right_start.get("character")
            and left_end.get("line") == right_end.get("line")
            and left_end.get("character") == right_end.get("character")
        )

    async def handleQueryStart(self, clients: list[Any]) -> None:
        if not self._initialized:
            connected = next((client for client in clients if getattr(client, "type", None) in (None, "connected")), None)
            if connected is not None:
                self.initialize(connected)
        else:
            self.reset()

    @staticmethod
    def getSeveritySymbol(severity: str) -> str:
        return {
            "Error": "x",
            "Warning": "!",
            "Info": "i",
            "Hint": "*",
        }.get(severity, "-")

    @staticmethod
    def formatDiagnosticsSummary(files: list[DiagnosticFile]) -> str:
        truncation_marker = "...[truncated]"
        chunks: list[str] = []
        for file in files:
            filename = Path(file.uri).name or file.uri
            entries = []
            for diagnostic in file.diagnostics:
                start = diagnostic.range.get("start", {}) if isinstance(diagnostic.range, dict) else {}
                line = int(start.get("line", 0)) + 1
                character = int(start.get("character", 0)) + 1
                code = f" [{diagnostic.code}]" if diagnostic.code else ""
                source = f" ({diagnostic.source})" if diagnostic.source else ""
                entries.append(
                    f"  {DiagnosticTrackingService.getSeveritySymbol(diagnostic.severity)} [Line {line}:{character}] {diagnostic.message}{code}{source}"
                )
            chunks.append(f"{filename}:\n" + "\n".join(entries))
        result = "\n\n".join(chunks)
        if len(result) > MAX_DIAGNOSTICS_SUMMARY_CHARS:
            return result[: MAX_DIAGNOSTICS_SUMMARY_CHARS - len(truncation_marker)] + truncation_marker
        return result


# Singleton export
diagnosticTracker = DiagnosticTrackingService.getInstance()

diagnostic_tracker = diagnosticTracker
