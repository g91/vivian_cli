"""
WebAuditTool — Comprehensive web application vulnerability scanner.

Scans live web applications for OWASP Top 10 vulnerabilities including
SQL injection, XSS, CSRF, SSRF, path traversal, authentication issues,
and misconfigurations. Produces detailed reports with remediation steps.
"""
from __future__ import annotations

import asyncio
import os
import re
import json
import urllib.request
import urllib.parse
import urllib.error
import ssl
import socket
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TOOL_NAME = "WebAudit"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["command"],
    "properties": {
        "command": {
            "type": "string",
            "description": (
                "The web audit operation. One of:\n"
                "- 'full_scan <url>' — Comprehensive OWASP Top 10 scan of a web app\n"
                "- 'sqli_test <url> [param]' — Test for SQL injection vulnerabilities\n"
                "- 'xss_test <url> [param]' — Test for Cross-Site Scripting vulnerabilities\n"
                "- 'csrf_check <url>' — Check for CSRF protection on forms\n"
                "- 'ssrf_test <url>' — Test for Server-Side Request Forgery\n"
                "- 'path_traversal <url>' — Test for path traversal / LFI vulnerabilities\n"
                "- 'auth_check <url>' — Check authentication and session security\n"
                "- 'headers_check <url>' — Audit security headers (CSP, HSTS, X-Frame, etc.)\n"
                "- 'cors_check <url>' — Check CORS configuration\n"
                "- 'ssl_check <host>' — Check SSL/TLS configuration\n"
                "- 'info_disclosure <url>' — Check for information disclosure\n"
                "- 'dir_enum <url> [wordlist]' — Discover hidden directories and files\n"
                "- 'form_fuzz <url>' — Find and analyze all forms on a page\n"
                "- 'cookie_audit <url>' — Audit cookie security attributes\n"
                "- 'api_scan <url>' — Scan REST/GraphQL API endpoints for vulnerabilities\n"
                "- 'report' — Generate consolidated audit report"
            ),
        },
        "url": {
            "type": "string",
            "description": "Target URL to audit (include https://).",
        },
        "param": {
            "type": "string",
            "description": "Specific parameter to test for injection.",
        },
        "wordlist": {
            "type": "string",
            "description": "Path to wordlist for directory enumeration.",
        },
        "timeout": {
            "type": "number",
            "description": "Request timeout in milliseconds (default: 30000).",
            "default": 30000,
        },
        "description": {
            "type": "string",
            "description": "Description of what this audit targets.",
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string"},
                    "type": {"type": "string"},
                    "endpoint": {"type": "string"},
                    "detail": {"type": "string"},
                    "evidence": {"type": "string"},
                    "remediation": {"type": "string"},
                    "cwe": {"type": "string"},
                },
            },
        },
        "summary": {"type": "string"},
        "total_findings": {"type": "integer"},
        "checks_performed": {"type": "integer"},
        "scan_duration_ms": {"type": "number"},
        "interrupted": {"type": "boolean"},
    },
}

# ── Session state ───────────────────────────────────────────────────────────
_all_findings: List[Dict[str, Any]] = []
_last_url: Optional[str] = None

# ── HTTP helpers ────────────────────────────────────────────────────────────

# Create an unverified SSL context for testing (users should be aware)
_SSL_CONTEXT = ssl.create_default_context()
_SSL_CONTEXT.check_hostname = False
_SSL_CONTEXT.verify_mode = ssl.CERT_NONE

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _http_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[bytes] = None,
    timeout: int = 15,
    follow_redirects: bool = True,
) -> Tuple[int, Dict[str, str], str]:
    """Make an HTTP request and return (status_code, headers_dict, body)."""
    req_headers = {"User-Agent": _USER_AGENT}
    if headers:
        req_headers.update(headers)

    try:
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        resp = urllib.request.urlopen(req, timeout=timeout, context=_SSL_CONTEXT)
        body = resp.read().decode("utf-8", errors="replace")
        headers_dict = dict(resp.headers)
        return resp.status, headers_dict, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, dict(e.headers), body
    except urllib.error.URLError as e:
        return 0, {}, f"Connection error: {str(e)}"
    except Exception as e:
        return 0, {}, f"Error: {str(e)}"


def _add_finding(
    severity: str,
    finding_type: str,
    endpoint: str,
    detail: str,
    evidence: str,
    remediation: str,
    cwe: str,
) -> None:
    """Add a finding to the global list."""
    _all_findings.append({
        "severity": severity,
        "type": finding_type,
        "endpoint": endpoint,
        "detail": detail,
        "evidence": evidence,
        "remediation": remediation,
        "cwe": cwe,
    })


# ── SQL Injection tests ─────────────────────────────────────────────────────

_SQLI_PAYLOADS = [
    ("'", "SQL syntax error / unescaped quote"),
    ('"', "SQL syntax error / unescaped double quote"),
    ("' OR '1'='1", "SQL injection - OR 1=1 bypass"),
    ("' OR '1'='1' --", "SQL injection - OR 1=1 with comment"),
    ("' OR 1=1 --", "SQL injection - numeric OR 1=1"),
    ("admin' --", "SQL injection - admin bypass"),
    ("' UNION SELECT NULL--", "SQL injection - UNION SELECT"),
    ("' UNION SELECT NULL,NULL--", "SQL injection - UNION SELECT 2 cols"),
    ("' UNION SELECT NULL,NULL,NULL--", "SQL injection - UNION SELECT 3 cols"),
    ("1' AND '1'='1", "SQL injection - AND true (blind)"),
    ("1' AND '1'='2", "SQL injection - AND false (blind)"),
    ("' OR SLEEP(5) --", "SQL injection - time-based (MySQL)"),
    ("'; WAITFOR DELAY '00:00:05'--", "SQL injection - time-based (MSSQL)"),
    ("' OR pg_sleep(5)--", "SQL injection - time-based (PostgreSQL)"),
    ("1; DROP TABLE users--", "SQL injection - DROP TABLE"),
]

_SQLI_ERRORS = [
    r"SQL syntax.*MySQL",
    r"Warning.*mysql_",
    r"MySQLSyntaxErrorException",
    r"valid MySQL result",
    r"PostgreSQL.*ERROR",
    r"Warning.*\Wpg_",
    r"valid PostgreSQL result",
    r"SQLite.*error",
    r"SQLite3::",
    r"Oracle error",
    r"ORA-[0-9]{5}",
    r"Microsoft OLE DB.*SQL Server",
    r"SQLServer JDBC",
    r"Unclosed quotation mark",
    r"com\.mysql\.jdbc",
    r"org\.postgresql",
    r"SQLite/JDBCDriver",
    r"System\.Data\.SqlClient\.SqlException",
    r"PDOException",
    r"sqlsrv",
]


async def _test_sqli(url: str, param: Optional[str] = None) -> List[Dict[str, Any]]:
    """Test for SQL injection vulnerabilities."""
    findings = []

    # First, fetch the page and find parameters
    status, headers, body = _http_request(url)
    if status == 0:
        return [{"severity": "info", "type": "Connection Error", "endpoint": url,
                 "detail": "Could not connect to target.", "evidence": body,
                 "remediation": "Verify the URL is correct and the server is running.", "cwe": "N/A"}]

    # Find forms and query parameters
    params_to_test = []

    # Extract query parameters from URL
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    for pname in query_params:
        params_to_test.append(("query", pname, query_params[pname][0]))

    # Find forms in HTML
    form_pattern = re.compile(
        r'<form[^>]*action\s*=\s*["\']([^"\']*)["\'][^>]*>.*?</form>',
        re.IGNORECASE | re.DOTALL,
    )
    input_pattern = re.compile(
        r'<input[^>]*name\s*=\s*["\']([^"\']+)["\'][^>]*>',
        re.IGNORECASE,
    )

    for form_match in form_pattern.finditer(body):
        form_action = form_match.group(1)
        form_body = form_match.group(0)
        for input_match in input_pattern.finditer(form_body):
            input_name = input_match.group(1)
            if input_name.lower() not in ("submit", "reset", "button", "csrf", "token"):
                params_to_test.append(("form", input_name, form_action))

    # If specific param requested, filter
    if param:
        params_to_test = [p for p in params_to_test if p[1] == param]

    if not params_to_test:
        # Test URL itself with appended payloads
        base_url = url.split("?")[0]
        for payload, desc in _SQLI_PAYLOADS[:5]:
            test_url = f"{base_url}?test={urllib.parse.quote(payload)}"
            status, headers, body = _http_request(test_url)
            for error_pattern in _SQLI_ERRORS:
                if re.search(error_pattern, body, re.IGNORECASE):
                    findings.append({
                        "severity": "critical", "type": "SQL Injection",
                        "endpoint": test_url,
                        "detail": f"SQL error detected with payload: {payload}",
                        "evidence": re.search(error_pattern, body, re.IGNORECASE).group(0)[:200],
                        "remediation": "Use parameterized queries / prepared statements. Never concatenate user input into SQL.",
                        "cwe": "CWE-89",
                    })
                    break
        return findings

    # Test each parameter
    for source, pname, context in params_to_test:
        for payload, desc in _SQLI_PAYLOADS:
            if source == "query":
                # Modify query parameter
                new_query = re.sub(
                    f'({re.escape(pname)})=[^&]*',
                    f'\\1={urllib.parse.quote(payload)}',
                    parsed.query,
                )
                test_url = urllib.parse.urlunparse(parsed._replace(query=new_query))
            else:
                # POST to form action
                test_url = urllib.parse.urljoin(url, context)
                data = urllib.parse.urlencode({pname: payload}).encode()
                status, headers, body = _http_request(test_url, method="POST", data=data)

            if source == "query":
                status, headers, body = _http_request(test_url)

            # Check for SQL errors
            for error_pattern in _SQLI_ERRORS:
                if re.search(error_pattern, body, re.IGNORECASE):
                    findings.append({
                        "severity": "critical", "type": "SQL Injection",
                        "endpoint": test_url if source == "query" else f"{test_url} (POST {pname})",
                        "detail": f"SQL error detected in parameter '{pname}' with payload: {payload}",
                        "evidence": re.search(error_pattern, body, re.IGNORECASE).group(0)[:200],
                        "remediation": "Use parameterized queries / prepared statements. Apply input validation.",
                        "cwe": "CWE-89",
                    })
                    break

            # Check for boolean-based differences
            if "' AND '1'='1" in payload:
                true_body = body
            elif "' AND '1'='2" in payload and true_body:
                if abs(len(body) - len(true_body)) > 50:
                    findings.append({
                        "severity": "high", "type": "SQL Injection (Boolean-based)",
                        "endpoint": test_url,
                        "detail": f"Boolean-based SQLi detected in parameter '{pname}'. Response length differs.",
                        "evidence": f"True response: {len(true_body)} bytes, False response: {len(body)} bytes",
                        "remediation": "Use parameterized queries. Apply input validation and WAF rules.",
                        "cwe": "CWE-89",
                    })

    return findings


# ── XSS tests ───────────────────────────────────────────────────────────────

_XSS_PAYLOADS = [
    ("<script>alert('XSS')</script>", "Basic script tag"),
    ('"><script>alert(document.cookie)</script>', "Attribute breakout + script"),
    ("<img src=x onerror=alert('XSS')>", "IMG onerror handler"),
    ("<svg onload=alert('XSS')>", "SVG onload handler"),
    ("<body onload=alert('XSS')>", "Body onload handler"),
    ("javascript:alert('XSS')", "JavaScript protocol handler"),
    ("'-alert('XSS')-'", "Single quote breakout"),
    ('"-alert(\'XSS\')-"', "Double quote breakout"),
    ("<iframe src=javascript:alert('XSS')>", "IFrame javascript URI"),
    ("<details open ontoggle=alert('XSS')>", "Details ontoggle handler"),
]


async def _test_xss(url: str, param: Optional[str] = None) -> List[Dict[str, Any]]:
    """Test for Cross-Site Scripting vulnerabilities."""
    findings = []

    status, headers, body = _http_request(url)
    if status == 0:
        return [{"severity": "info", "type": "Connection Error", "endpoint": url,
                 "detail": "Could not connect.", "evidence": body,
                 "remediation": "Verify URL.", "cwe": "N/A"}]

    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)

    params_to_test = [(pname, pvalue[0]) for pname, pvalue in query_params.items()]
    if param:
        params_to_test = [p for p in params_to_test if p[0] == param]

    for pname, pvalue in params_to_test:
        for payload, desc in _XSS_PAYLOADS:
            new_query = re.sub(
                f'({re.escape(pname)})=[^&]*',
                f'\\1={urllib.parse.quote(payload)}',
                parsed.query,
            )
            test_url = urllib.parse.urlunparse(parsed._replace(query=new_query))
            status, headers, body = _http_request(test_url)

            # Check if payload is reflected without sanitization
            if payload in body:
                findings.append({
                    "severity": "high", "type": "Reflected XSS",
                    "endpoint": test_url,
                    "detail": f"XSS payload reflected in response via parameter '{pname}': {desc}",
                    "evidence": f"Payload '{payload}' appears unescaped in response body.",
                    "remediation": "HTML-encode all user input before output. Use Content-Security-Policy header. Apply context-appropriate escaping.",
                    "cwe": "CWE-79",
                })
                break

    return findings


# ── CSRF check ──────────────────────────────────────────────────────────────

async def _check_csrf(url: str) -> List[Dict[str, Any]]:
    """Check for CSRF protection on forms."""
    findings = []
    status, headers, body = _http_request(url)
    if status == 0:
        return findings

    # Find all forms
    form_pattern = re.compile(
        r'<form[^>]*method\s*=\s*["\']?(post|POST)["\']?[^>]*>',
        re.IGNORECASE,
    )
    csrf_pattern = re.compile(
        r'(?:csrf|_token|nonce|authenticity_token|__RequestVerificationToken)',
        re.IGNORECASE,
    )

    for form_match in form_pattern.finditer(body):
        # Get form context (next 2000 chars)
        form_start = form_match.start()
        form_context = body[form_start:form_start + 3000]

        if not csrf_pattern.search(form_context):
            findings.append({
                "severity": "high", "type": "Missing CSRF Protection",
                "endpoint": url,
                "detail": "A POST form was found without CSRF token protection.",
                "evidence": form_context[:300],
                "remediation": "Add CSRF tokens to all state-changing forms. Use SameSite=Strict/Lax cookies. Validate Origin/Referer headers.",
                "cwe": "CWE-352",
            })

    if not findings:
        findings.append({
            "severity": "info", "type": "CSRF Check",
            "endpoint": url,
            "detail": "No unprotected POST forms found, or no forms detected.",
            "evidence": "",
            "remediation": "Ensure all state-changing endpoints have CSRF protection.",
            "cwe": "CWE-352",
        })

    return findings


# ── SSRF test ───────────────────────────────────────────────────────────────

_SSRF_PAYLOADS = [
    "http://127.0.0.1/",
    "http://localhost/",
    "http://[::1]/",
    "http://169.254.169.254/latest/meta-data/",  # AWS metadata
    "http://metadata.google.internal/",  # GCP metadata
    "file:///etc/passwd",
    "http://0.0.0.0/",
    "http://10.0.0.1/",
    "http://192.168.1.1/",
]


async def _test_ssrf(url: str) -> List[Dict[str, Any]]:
    """Test for SSRF vulnerabilities."""
    findings = []
    status, headers, body = _http_request(url)
    if status == 0:
        return findings

    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)

    # Look for URL-like parameters
    url_params = []
    for pname, pvalues in query_params.items():
        for pval in pvalues:
            if pval.startswith(("http://", "https://")) or "url" in pname.lower() or "link" in pname.lower() or "redirect" in pname.lower() or "path" in pname.lower() or "file" in pname.lower():
                url_params.append((pname, pval))

    for pname, _ in url_params:
        for ssrf_payload in _SSRF_PAYLOADS[:5]:
            new_query = re.sub(
                f'({re.escape(pname)})=[^&]*',
                f'\\1={urllib.parse.quote(ssrf_payload)}',
                parsed.query,
            )
            test_url = urllib.parse.urlunparse(parsed._replace(query=new_query))
            status, headers, body = _http_request(test_url)

            # Check for signs of SSRF
            if "root:" in body or "ami-id" in body or "security-credentials" in body:
                findings.append({
                    "severity": "critical", "type": "Server-Side Request Forgery (SSRF)",
                    "endpoint": test_url,
                    "detail": f"SSRF confirmed: parameter '{pname}' allows internal resource access.",
                    "evidence": body[:300],
                    "remediation": "Whitelist allowed URLs/hosts. Block internal IP ranges. Validate and sanitize URL inputs.",
                    "cwe": "CWE-918",
                })
                break

    # Also check for open redirects
    for pname, _ in url_params:
        new_query = re.sub(
            f'({re.escape(pname)})=[^&]*',
            f'\\1={urllib.parse.quote("https://evil.com")}',
            parsed.query,
        )
        test_url = urllib.parse.urlunparse(parsed._replace(query=new_query))
        status, headers, body = _http_request(test_url)
        if status in (301, 302, 303, 307, 308) and "evil.com" in headers.get("Location", ""):
            findings.append({
                "severity": "medium", "type": "Open Redirect",
                "endpoint": url,
                "detail": f"Open redirect via parameter '{pname}'.",
                "evidence": f"Redirects to: {headers.get('Location', '')}",
                "remediation": "Use a whitelist of allowed redirect URLs. Use relative redirects or validate against allowed domains.",
                "cwe": "CWE-601",
            })

    return findings


# ── Path Traversal / LFI test ───────────────────────────────────────────────

_LFI_PAYLOADS = [
    "../../../etc/passwd",
    "....//....//....//etc/passwd",
    "..%2F..%2F..%2Fetc%2Fpasswd",
    "..%252F..%252F..%252Fetc%252Fpasswd",
    "/etc/passwd",
    "C:\\Windows\\System32\\drivers\\etc\\hosts",
    "..\\..\\..\\windows\\win.ini",
    "file:///etc/passwd",
    "php://filter/convert.base64-encode/resource=index.php",
    "php://input",
    "data://text/plain;base64,PD9waHAgcGhwaW5mbygpOyA/Pg==",
]


async def _test_path_traversal(url: str) -> List[Dict[str, Any]]:
    """Test for path traversal and LFI vulnerabilities."""
    findings = []
    status, headers, body = _http_request(url)
    if status == 0:
        return findings

    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)

    # Find file/path parameters
    file_params = []
    for pname, pvalues in query_params.items():
        if any(kw in pname.lower() for kw in ("file", "path", "page", "include", "template", "doc", "view", "load", "read", "dir", "folder")):
            file_params.append((pname, pvalues[0]))

    for pname, _ in file_params:
        for payload in _LFI_PAYLOADS:
            new_query = re.sub(
                f'({re.escape(pname)})=[^&]*',
                f'\\1={urllib.parse.quote(payload)}',
                parsed.query,
            )
            test_url = urllib.parse.urlunparse(parsed._replace(query=new_query))
            status, headers, body = _http_request(test_url)

            # Check for signs of LFI
            if "root:" in body and ("/bin/bash" in body or "/bin/sh" in body):
                findings.append({
                    "severity": "critical", "type": "Local File Inclusion (LFI)",
                    "endpoint": test_url,
                    "detail": f"LFI confirmed via parameter '{pname}'. /etc/passwd exposed.",
                    "evidence": body[:300],
                    "remediation": "Use a whitelist of allowed files. Sanitize file paths with basename() and realpath(). Never pass user input to include/require.",
                    "cwe": "CWE-98",
                })
                break

            if "phpinfo()" in body or "PHP Version" in body:
                findings.append({
                    "severity": "critical", "type": "PHP Code Execution (LFI to RCE)",
                    "endpoint": test_url,
                    "detail": f"PHP filter wrapper accepted via parameter '{pname}'.",
                    "evidence": body[:300],
                    "remediation": "Disable dangerous PHP wrappers (php://, data://, expect://). Use allow_url_include=Off.",
                    "cwe": "CWE-98",
                })
                break

    return findings


# ── Security headers check ──────────────────────────────────────────────────

_SECURITY_HEADERS = {
    "Content-Security-Policy": {
        "severity": "medium", "cwe": "CWE-1021",
        "detail": "Missing Content-Security-Policy header.",
        "remediation": "Add a strict CSP header: default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self';",
    },
    "X-Content-Type-Options": {
        "severity": "low", "cwe": "CWE-693",
        "detail": "Missing X-Content-Type-Options header.",
        "remediation": "Add: X-Content-Type-Options: nosniff",
    },
    "X-Frame-Options": {
        "severity": "medium", "cwe": "CWE-1021",
        "detail": "Missing X-Frame-Options header (clickjacking risk).",
        "remediation": "Add: X-Frame-Options: DENY or SAMEORIGIN",
    },
    "Strict-Transport-Security": {
        "severity": "medium", "cwe": "CWE-319",
        "detail": "Missing HSTS header.",
        "remediation": "Add: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload",
    },
    "X-XSS-Protection": {
        "severity": "low", "cwe": "CWE-79",
        "detail": "Missing X-XSS-Protection header.",
        "remediation": "Add: X-XSS-Protection: 1; mode=block (legacy; CSP is preferred)",
    },
    "Referrer-Policy": {
        "severity": "low", "cwe": "CWE-200",
        "detail": "Missing Referrer-Policy header.",
        "remediation": "Add: Referrer-Policy: strict-origin-when-cross-origin",
    },
    "Permissions-Policy": {
        "severity": "low", "cwe": "CWE-693",
        "detail": "Missing Permissions-Policy header.",
        "remediation": "Add: Permissions-Policy: camera=(), microphone=(), geolocation=()",
    },
}


async def _check_headers(url: str) -> List[Dict[str, Any]]:
    """Audit security headers."""
    findings = []
    status, headers, body = _http_request(url)
    if status == 0:
        return findings

    for header_name, info in _SECURITY_HEADERS.items():
        if header_name not in headers:
            findings.append({
                "severity": info["severity"],
                "type": f"Missing Security Header: {header_name}",
                "endpoint": url,
                "detail": info["detail"],
                "evidence": f"Header '{header_name}' not present in response.",
                "remediation": info["remediation"],
                "cwe": info["cwe"],
            })

    # Check for server version disclosure
    if "Server" in headers:
        server_value = headers["Server"]
        if re.search(r'\d+\.\d+', server_value):
            findings.append({
                "severity": "low", "type": "Server Version Disclosure",
                "endpoint": url,
                "detail": f"Server header reveals version: {server_value}",
                "evidence": f"Server: {server_value}",
                "remediation": "Configure server to suppress version information in headers.",
                "cwe": "CWE-200",
            })

    if "X-Powered-By" in headers:
        findings.append({
            "severity": "low", "type": "Technology Disclosure",
            "endpoint": url,
            "detail": f"X-Powered-By header reveals: {headers['X-Powered-By']}",
            "evidence": f"X-Powered-By: {headers['X-Powered-By']}",
            "remediation": "Remove X-Powered-By header to avoid revealing technology stack.",
            "cwe": "CWE-200",
        })

    return findings


# ── CORS check ──────────────────────────────────────────────────────────────

async def _check_cors(url: str) -> List[Dict[str, Any]]:
    """Check CORS configuration."""
    findings = []

    # Test with a malicious origin
    test_headers = {"Origin": "https://evil.com"}
    status, headers, body = _http_request(url, headers=test_headers)

    acao = headers.get("Access-Control-Allow-Origin", "")
    acac = headers.get("Access-Control-Allow-Credentials", "")

    if acao == "*" and acac.lower() == "true":
        findings.append({
            "severity": "high", "type": "Insecure CORS (Wildcard + Credentials)",
            "endpoint": url,
            "detail": "CORS allows any origin with credentials. This is a critical misconfiguration.",
            "evidence": f"Access-Control-Allow-Origin: {acao}, Access-Control-Allow-Credentials: {acac}",
            "remediation": "Never use '*' with credentials. Specify exact allowed origins. Validate Origin header server-side.",
            "cwe": "CWE-942",
        })
    elif acao == "*":
        findings.append({
            "severity": "medium", "type": "Permissive CORS (Wildcard)",
            "endpoint": url,
            "detail": "CORS allows any origin (wildcard). May be intentional for public APIs.",
            "evidence": f"Access-Control-Allow-Origin: {acao}",
            "remediation": "If not a public API, restrict to specific origins. Never use '*' with credentials.",
            "cwe": "CWE-942",
        })
    elif "evil.com" in acao:
        findings.append({
            "severity": "critical", "type": "CORS Origin Reflection",
            "endpoint": url,
            "detail": "CORS reflects arbitrary Origin headers. Any website can make authenticated requests.",
            "evidence": f"Origin: https://evil.com -> Access-Control-Allow-Origin: {acao}",
            "remediation": "Validate Origin against a whitelist. Never echo back the Origin header without validation.",
            "cwe": "CWE-942",
        })

    return findings


# ── SSL/TLS check ───────────────────────────────────────────────────────────

async def _check_ssl(host: str) -> List[Dict[str, Any]]:
    """Check SSL/TLS configuration."""
    findings = []

    # Remove protocol prefix
    host = re.sub(r'^https?://', '', host).split('/')[0].split(':')[0]

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
                version = ssock.version()

                # Check TLS version
                if version and "1.0" in version or "1.1" in version:
                    findings.append({
                        "severity": "high", "type": "Outdated TLS Version",
                        "endpoint": f"https://{host}",
                        "detail": f"Server supports {version}. TLS 1.0/1.1 are deprecated.",
                        "evidence": f"TLS Version: {version}",
                        "remediation": "Disable TLS 1.0 and 1.1. Enable only TLS 1.2 and TLS 1.3.",
                        "cwe": "CWE-326",
                    })

                # Check certificate expiry
                if cert:
                    not_after = cert.get("notAfter", "")
                    findings.append({
                        "severity": "info", "type": "SSL Certificate Info",
                        "endpoint": f"https://{host}",
                        "detail": f"Certificate expires: {not_after}. Issuer: {cert.get('issuer', 'Unknown')}",
                        "evidence": f"Subject: {cert.get('subject', 'Unknown')}",
                        "remediation": "Ensure certificate auto-renewal is configured.",
                        "cwe": "CWE-295",
                    })

    except ssl.SSLError as e:
        findings.append({
            "severity": "high", "type": "SSL Certificate Error",
            "endpoint": f"https://{host}",
            "detail": f"SSL verification failed: {str(e)[:200]}",
            "evidence": str(e)[:300],
            "remediation": "Install a valid SSL certificate from a trusted CA.",
            "cwe": "CWE-295",
        })
    except Exception as e:
        findings.append({
            "severity": "info", "type": "SSL Check Failed",
            "endpoint": f"https://{host}",
            "detail": f"Could not complete SSL check: {str(e)[:200]}",
            "evidence": str(e)[:200],
            "remediation": "Ensure the server is reachable on port 443.",
            "cwe": "N/A",
        })

    return findings


# ── Information disclosure check ────────────────────────────────────────────

_INFO_DISCLOSURE_PATTERNS = [
    (r'phpinfo\(\)', "PHP Info Page", "high", "CWE-200", "Remove phpinfo() pages from production."),
    (r'DEBUG\s*=\s*True', "Django Debug Mode", "high", "CWE-489", "Set DEBUG=False in production."),
    (r'ASP\.NET.*error.*detailed', "ASP.NET Detailed Errors", "medium", "CWE-209", "Set customErrors mode='On' in web.config."),
    (r'stack trace:|at\s+\w+\.\w+\(\w+\.\w+:\d+\)', "Stack Trace Disclosure", "medium", "CWE-209", "Configure custom error pages. Never show stack traces to users."),
    (r'SQLSTATE\[|mysql_fetch|pg_query', "Database Error Disclosure", "high", "CWE-209", "Catch database exceptions. Show generic error messages to users."),
    (r'\.git/HEAD|\.svn/entries|\.DS_Store', "VCS Files Exposed", "high", "CWE-538", "Block access to .git, .svn, and other VCS directories in web server config."),
    (r'\.env|\.aws/credentials', "Sensitive File Exposure", "critical", "CWE-538", "Block access to dotfiles and config files. Move secrets out of webroot."),
    (r'wp-config\.php|configuration\.php', "Config File Exposure", "critical", "CWE-538", "Restrict access to configuration files. Place them outside webroot."),
    (r'phpMyAdmin|phpinfo|server-status|server-info', "Admin Interface Exposed", "high", "CWE-200", "Restrict admin interfaces by IP. Use strong authentication."),
    (r'Swagger\s*UI|api-docs|openapi\.json', "API Documentation Exposed", "medium", "CWE-200", "Restrict API docs to development environments or authenticated users."),
]


async def _check_info_disclosure(url: str) -> List[Dict[str, Any]]:
    """Check for information disclosure."""
    findings = []

    # Check common sensitive paths
    sensitive_paths = [
        "/.git/HEAD", "/.env", "/.aws/credentials", "/phpinfo.php",
        "/wp-config.php", "/.DS_Store", "/server-status", "/server-info",
        "/phpMyAdmin/", "/admin/", "/.svn/entries", "/backup/",
        "/api-docs/", "/swagger-ui.html", "/actuator/", "/debug/",
        "/.vscode/", "/.idea/", "/node_modules/", "/package.json",
    ]

    base_url = url.rstrip("/")
    for path in sensitive_paths:
        test_url = f"{base_url}{path}"
        status, headers, body = _http_request(test_url)
        if status == 200:
            for pattern, vtype, severity, cwe, remediation in _INFO_DISCLOSURE_PATTERNS:
                if re.search(pattern, body, re.IGNORECASE) or path in str(pattern):
                    findings.append({
                        "severity": severity, "type": vtype,
                        "endpoint": test_url,
                        "detail": f"Sensitive resource accessible: {path}",
                        "evidence": body[:300],
                        "remediation": remediation,
                        "cwe": cwe,
                    })
                    break

    # Check main page for info disclosure
    status, headers, body = _http_request(url)
    for pattern, vtype, severity, cwe, remediation in _INFO_DISCLOSURE_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            findings.append({
                "severity": severity, "type": vtype,
                "endpoint": url,
                "detail": f"Information disclosure detected on main page.",
                "evidence": re.search(pattern, body, re.IGNORECASE).group(0)[:200] if re.search(pattern, body, re.IGNORECASE) else "",
                "remediation": remediation,
                "cwe": cwe,
            })

    return findings


# ── Directory enumeration ───────────────────────────────────────────────────

_COMMON_DIRS = [
    "admin", "backup", "backups", "config", "css", "db", "debug",
    "dev", "docs", "download", "files", "images", "img", "inc",
    "includes", "js", "lib", "login", "logs", "old", "phpmyadmin",
    "scripts", "secret", "src", "static", "temp", "test", "tests",
    "tmp", "upload", "uploads", "vendor", "wp-admin", "wp-content",
    "wp-includes", "api", "v1", "v2", "graphql", "rest", ".git",
    ".svn", ".env", ".htaccess", "robots.txt", "sitemap.xml",
    "crossdomain.xml", "web.config", "package.json", "composer.json",
    "Gemfile", "Dockerfile", "docker-compose.yml", ".gitignore",
]


async def _dir_enum(url: str, wordlist: Optional[str] = None) -> List[Dict[str, Any]]:
    """Enumerate directories and files."""
    findings = []
    base_url = url.rstrip("/")

    dirs_to_check = list(_COMMON_DIRS)
    if wordlist and os.path.exists(wordlist):
        try:
            with open(wordlist, "r", encoding="utf-8", errors="replace") as f:
                dirs_to_check.extend(line.strip() for line in f if line.strip() and not line.startswith("#"))
        except Exception:
            pass

    discovered = []
    for d in dirs_to_check[:200]:  # Limit to avoid excessive requests
        test_url = f"{base_url}/{d}"
        status, headers, body = _http_request(test_url)
        if status in (200, 301, 302, 403):
            discovered.append(f"  [{status}] {test_url}")

    if discovered:
        findings.append({
            "severity": "info", "type": "Directory Enumeration Results",
            "endpoint": base_url,
            "detail": f"Found {len(discovered)} accessible paths.",
            "evidence": "\n".join(discovered[:50]),
            "remediation": "Review exposed directories. Restrict access to sensitive paths. Use proper access controls.",
            "cwe": "CWE-538",
        })

    return findings


# ── Cookie audit ────────────────────────────────────────────────────────────

async def _cookie_audit(url: str) -> List[Dict[str, Any]]:
    """Audit cookie security attributes."""
    findings = []
    status, headers, body = _http_request(url)
    if status == 0:
        return findings

    set_cookies = headers.get_all("Set-Cookie") if hasattr(headers, "get_all") else [headers.get("Set-Cookie", "")]

    if not set_cookies or not any(set_cookies):
        findings.append({
            "severity": "info", "type": "No Cookies Set",
            "endpoint": url,
            "detail": "No Set-Cookie headers found in response.",
            "evidence": "",
            "remediation": "N/A",
            "cwe": "N/A",
        })
        return findings

    for cookie_str in set_cookies:
        if not cookie_str:
            continue
        cookie_lower = cookie_str.lower()

        issues = []
        if "httponly" not in cookie_lower:
            issues.append("Missing HttpOnly flag (accessible to JavaScript)")
        if "secure" not in cookie_lower:
            issues.append("Missing Secure flag (sent over HTTP)")
        if "samesite" not in cookie_lower:
            issues.append("Missing SameSite attribute (CSRF risk)")

        if issues:
            findings.append({
                "severity": "high" if len(issues) >= 2 else "medium",
                "type": "Insecure Cookie Configuration",
                "endpoint": url,
                "detail": "; ".join(issues),
                "evidence": cookie_str[:200],
                "remediation": "Set HttpOnly, Secure, and SameSite=Strict/Lax on all sensitive cookies.",
                "cwe": "CWE-614",
            })

    return findings


# ── Form analysis ───────────────────────────────────────────────────────────

async def _form_fuzz(url: str) -> List[Dict[str, Any]]:
    """Find and analyze all forms on a page."""
    findings = []
    status, headers, body = _http_request(url)
    if status == 0:
        return findings

    form_pattern = re.compile(
        r'<form[^>]*>(.*?)</form>',
        re.IGNORECASE | re.DOTALL,
    )
    input_pattern = re.compile(
        r'<input[^>]*name\s*=\s*["\']([^"\']+)["\'][^>]*type\s*=\s*["\']([^"\']+)["\'][^>]*>',
        re.IGNORECASE,
    )
    action_pattern = re.compile(r'action\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    method_pattern = re.compile(r'method\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)

    forms_found = []
    for form_match in form_pattern.finditer(body):
        form_html = form_match.group(0)
        action = action_pattern.search(form_html)
        method = method_pattern.search(form_html)
        inputs = input_pattern.findall(form_html)

        forms_found.append({
            "action": action.group(1) if action else "(none)",
            "method": method.group(1).upper() if method else "GET",
            "inputs": [{"name": name, "type": itype} for name, itype in inputs],
        })

    if forms_found:
        summary = f"Found {len(forms_found)} form(s) on {url}:\n"
        for i, form in enumerate(forms_found, 1):
            summary += f"\nForm {i}: {form['method']} {form['action']}\n"
            for inp in form["inputs"]:
                summary += f"  - {inp['name']} (type={inp['type']})\n"

        findings.append({
            "severity": "info", "type": "Form Analysis",
            "endpoint": url,
            "detail": f"Found {len(forms_found)} form(s). Review for injection points.",
            "evidence": summary,
            "remediation": "Test each form input for injection vulnerabilities. Ensure proper validation and sanitization.",
            "cwe": "CWE-20",
        })

    return findings


# ── API scan ────────────────────────────────────────────────────────────────

async def _api_scan(url: str) -> List[Dict[str, Any]]:
    """Scan API endpoints for vulnerabilities."""
    findings = []

    # Test common API paths
    api_paths = [
        "/api/", "/api/v1/", "/graphql", "/rest/", "/v1/", "/v2/",
        "/api/users", "/api/admin", "/api/auth", "/api/login",
    ]

    base_url = url.rstrip("/")
    for path in api_paths:
        test_url = f"{base_url}{path}"
        status, headers, body = _http_request(test_url)

        if status == 200:
            # Check for API documentation exposure
            if any(kw in body.lower() for kw in ("swagger", "openapi", "graphql", "endpoint", "api documentation")):
                findings.append({
                    "severity": "medium", "type": "API Documentation Exposed",
                    "endpoint": test_url,
                    "detail": "API documentation is publicly accessible.",
                    "evidence": body[:300],
                    "remediation": "Restrict API documentation to authenticated users or internal networks.",
                    "cwe": "CWE-200",
                })

            # Check for excessive data exposure
            if len(body) > 10000:
                findings.append({
                    "severity": "medium", "type": "Excessive Data Exposure",
                    "endpoint": test_url,
                    "detail": f"API endpoint returns large response ({len(body)} bytes). May expose too much data.",
                    "evidence": f"Response size: {len(body)} bytes. First 200 chars: {body[:200]}",
                    "remediation": "Implement field-level filtering. Only return data the client needs.",
                    "cwe": "CWE-213",
                })

        # Check for missing authentication
        if status == 200 and "login" not in path.lower() and "auth" not in path.lower():
            # Try to detect if this is an unauthenticated admin endpoint
            if any(kw in path.lower() for kw in ("admin", "users", "config", "debug")):
                findings.append({
                    "severity": "high", "type": "Unauthenticated API Access",
                    "endpoint": test_url,
                    "detail": f"Potentially sensitive API endpoint accessible without authentication.",
                    "evidence": f"Status: {status}, Response: {body[:200]}",
                    "remediation": "Require authentication for all sensitive API endpoints. Use API keys or OAuth tokens.",
                    "cwe": "CWE-306",
                })

    return findings


# ── Auth check ──────────────────────────────────────────────────────────────

async def _auth_check(url: str) -> List[Dict[str, Any]]:
    """Check authentication and session security."""
    findings = []
    status, headers, body = _http_request(url)
    if status == 0:
        return findings

    # Check for login page
    has_login = bool(re.search(r'(?:login|signin|sign-in|log-in)', body, re.IGNORECASE))

    # Check for password autocomplete
    if re.search(r'autocomplete\s*=\s*["\'](?:on|off)["\'].*password', body, re.IGNORECASE):
        findings.append({
            "severity": "low", "type": "Password Autocomplete",
            "endpoint": url,
            "detail": "Password field has autocomplete enabled.",
            "evidence": "autocomplete attribute found on password field.",
            "remediation": "Set autocomplete='off' on sensitive fields, or use autocomplete='new-password'.",
            "cwe": "CWE-200",
        })

    # Check for rate limiting headers
    rate_limit_headers = [h for h in headers if "rate" in h.lower() or "limit" in h.lower()]
    if has_login and not rate_limit_headers:
        findings.append({
            "severity": "medium", "type": "Missing Rate Limiting",
            "endpoint": url,
            "detail": "No rate limiting headers detected. Login may be vulnerable to brute force.",
            "evidence": "No X-RateLimit-* or similar headers found.",
            "remediation": "Implement rate limiting on login endpoints. Use account lockout after N failed attempts.",
            "cwe": "CWE-307",
        })

    # Check session cookie security
    set_cookies = headers.get_all("Set-Cookie") if hasattr(headers, "get_all") else [headers.get("Set-Cookie", "")]
    for cookie_str in set_cookies:
        if cookie_str and "session" in cookie_str.lower():
            if "httponly" not in cookie_str.lower():
                findings.append({
                    "severity": "high", "type": "Session Cookie Missing HttpOnly",
                    "endpoint": url,
                    "detail": "Session cookie lacks HttpOnly flag. Vulnerable to XSS-based session theft.",
                    "evidence": cookie_str[:200],
                    "remediation": "Set HttpOnly flag on all session cookies.",
                    "cwe": "CWE-614",
                })
            if "secure" not in cookie_str.lower():
                findings.append({
                    "severity": "high", "type": "Session Cookie Missing Secure Flag",
                    "endpoint": url,
                    "detail": "Session cookie lacks Secure flag. May be transmitted over HTTP.",
                    "evidence": cookie_str[:200],
                    "remediation": "Set Secure flag on all cookies. Use HTTPS exclusively.",
                    "cwe": "CWE-614",
                })

    return findings


# ── Full scan ───────────────────────────────────────────────────────────────

async def _full_scan(url: str) -> Dict[str, Any]:
    """Run a comprehensive OWASP Top 10 scan."""
    global _all_findings
    _all_findings = []
    start = time.time()

    checks = [
        ("Security Headers", _check_headers(url)),
        ("Information Disclosure", _check_info_disclosure(url)),
        ("CORS Configuration", _check_cors(url)),
        ("CSRF Protection", _check_csrf(url)),
        ("Cookie Security", _cookie_audit(url)),
        ("Authentication", _auth_check(url)),
        ("SQL Injection", _test_sqli(url)),
        ("XSS", _test_xss(url)),
        ("SSRF", _test_ssrf(url)),
        ("Path Traversal", _test_path_traversal(url)),
        ("Form Analysis", _form_fuzz(url)),
        ("API Security", _api_scan(url)),
        ("Directory Enumeration", _dir_enum(url)),
    ]

    # Extract host for SSL check
    host = re.sub(r'^https?://', '', url).split('/')[0]
    checks.append(("SSL/TLS", _check_ssl(host)))

    all_findings = []
    for check_name, check_results in checks:
        if isinstance(check_results, list):
            all_findings.extend(check_results)

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    all_findings.sort(key=lambda f: severity_order.get(f["severity"], 5))

    _all_findings = all_findings

    # Build summary
    sev_counts = {}
    for f in all_findings:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1

    summary = [
        "=" * 60,
        "WEB APPLICATION AUDIT REPORT",
        "=" * 60,
        f"Target: {url}",
        f"Scan time: {time.time() - start:.1f}s",
        f"Total findings: {len(all_findings)}",
        "",
        "--- Severity Breakdown ---",
    ]
    for sev in ["critical", "high", "medium", "low", "info"]:
        if sev in sev_counts:
            summary.append(f"  {sev.upper()}: {sev_counts[sev]}")

    summary.append("")
    summary.append("--- Critical & High Priority Findings ---")
    for f in all_findings:
        if f["severity"] in ("critical", "high"):
            summary.append(f"\n[{f['severity'].upper()}] {f['type']} ({f['cwe']})")
            summary.append(f"  Endpoint: {f['endpoint']}")
            summary.append(f"  Detail: {f['detail']}")
            summary.append(f"  Fix: {f['remediation']}")

    return {
        "findings": all_findings,
        "summary": "\n".join(summary),
        "total_findings": len(all_findings),
        "checks_performed": len(checks),
        "scan_duration_ms": (time.time() - start) * 1000,
        "interrupted": False,
    }


# ── Report ──────────────────────────────────────────────────────────────────

async def _report(args: Dict[str, Any]) -> Dict[str, Any]:
    """Generate consolidated report."""
    global _all_findings, _last_url

    if not _all_findings:
        return {"findings": [], "summary": "No audit has been run yet. Run full_scan or individual checks first.",
                "total_findings": 0, "checks_performed": 0, "scan_duration_ms": 0, "interrupted": False}

    sev_counts = {}
    type_counts = {}
    for f in _all_findings:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1
        type_counts[f["type"]] = type_counts.get(f["type"], 0) + 1

    report = [
        "=" * 60,
        "CONSOLIDATED WEB AUDIT REPORT",
        "=" * 60,
        f"Target: {_last_url}",
        f"Total findings: {len(_all_findings)}",
        "",
        "--- By Severity ---",
    ]
    for sev in ["critical", "high", "medium", "low", "info"]:
        if sev in sev_counts:
            report.append(f"  {sev.upper()}: {sev_counts[sev]}")

    report.append("")
    report.append("--- By Type ---")
    for vtype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        report.append(f"  {vtype}: {count}")

    report.append("")
    report.append("--- All Findings ---")
    for i, f in enumerate(_all_findings, 1):
        report.append(f"\n{i}. [{f['severity'].upper()}] {f['type']} ({f['cwe']})")
        report.append(f"   Endpoint: {f['endpoint']}")
        report.append(f"   Detail: {f['detail']}")
        report.append(f"   Fix: {f['remediation']}")

    return {
        "findings": _all_findings,
        "summary": "\n".join(report),
        "total_findings": len(_all_findings),
        "checks_performed": 0,
        "scan_duration_ms": 0,
        "interrupted": False,
    }


# ── Command dispatch ────────────────────────────────────────────────────────

async def call(args: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
    """Main entry point for WebAudit."""
    global _all_findings, _last_url

    command = (args.get("command") or "").strip()
    if not command:
        return {"findings": [], "summary": "No command specified. Use 'full_scan <url>' for comprehensive audit.",
                "total_findings": 0, "checks_performed": 0, "scan_duration_ms": 0, "interrupted": False}

    parts = command.split(None, 1)
    sub_cmd = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""

    url = args.get("url", "")
    if not url and rest:
        # Extract URL from command
        url = rest.split()[0] if rest else ""

    if not url and sub_cmd not in ("report",):
        return {"findings": [], "summary": "No URL specified. Provide a target URL.",
                "total_findings": 0, "checks_performed": 0, "scan_duration_ms": 0, "interrupted": False}

    _last_url = url

    if sub_cmd == "full_scan":
        result = await _full_scan(url)
    elif sub_cmd == "sqli_test":
        param = args.get("param", "")
        findings = await _test_sqli(url, param if param else None)
        result = {"findings": findings, "summary": f"SQLi test: {len(findings)} finding(s)", "total_findings": len(findings), "checks_performed": 1, "scan_duration_ms": 0, "interrupted": False}
    elif sub_cmd == "xss_test":
        param = args.get("param", "")
        findings = await _test_xss(url, param if param else None)
        result = {"findings": findings, "summary": f"XSS test: {len(findings)} finding(s)", "total_findings": len(findings), "checks_performed": 1, "scan_duration_ms": 0, "interrupted": False}
    elif sub_cmd == "csrf_check":
        findings = await _check_csrf(url)
        result = {"findings": findings, "summary": f"CSRF check: {len(findings)} finding(s)", "total_findings": len(findings), "checks_performed": 1, "scan_duration_ms": 0, "interrupted": False}
    elif sub_cmd == "ssrf_test":
        findings = await _test_ssrf(url)
        result = {"findings": findings, "summary": f"SSRF test: {len(findings)} finding(s)", "total_findings": len(findings), "checks_performed": 1, "scan_duration_ms": 0, "interrupted": False}
    elif sub_cmd == "path_traversal":
        findings = await _test_path_traversal(url)
        result = {"findings": findings, "summary": f"Path traversal test: {len(findings)} finding(s)", "total_findings": len(findings), "checks_performed": 1, "scan_duration_ms": 0, "interrupted": False}
    elif sub_cmd == "auth_check":
        findings = await _auth_check(url)
        result = {"findings": findings, "summary": f"Auth check: {len(findings)} finding(s)", "total_findings": len(findings), "checks_performed": 1, "scan_duration_ms": 0, "interrupted": False}
    elif sub_cmd == "headers_check":
        findings = await _check_headers(url)
        result = {"findings": findings, "summary": f"Headers check: {len(findings)} finding(s)", "total_findings": len(findings), "checks_performed": 1, "scan_duration_ms": 0, "interrupted": False}
    elif sub_cmd == "cors_check":
        findings = await _check_cors(url)
        result = {"findings": findings, "summary": f"CORS check: {len(findings)} finding(s)", "total_findings": len(findings), "checks_performed": 1, "scan_duration_ms": 0, "interrupted": False}
    elif sub_cmd == "ssl_check":
        host = re.sub(r'^https?://', '', url).split('/')[0]
        findings = await _check_ssl(host)
        result = {"findings": findings, "summary": f"SSL check: {len(findings)} finding(s)", "total_findings": len(findings), "checks_performed": 1, "scan_duration_ms": 0, "interrupted": False}
    elif sub_cmd == "info_disclosure":
        findings = await _check_info_disclosure(url)
        result = {"findings": findings, "summary": f"Info disclosure: {len(findings)} finding(s)", "total_findings": len(findings), "checks_performed": 1, "scan_duration_ms": 0, "interrupted": False}
    elif sub_cmd == "dir_enum":
        wordlist = args.get("wordlist", "")
        findings = await _dir_enum(url, wordlist if wordlist else None)
        result = {"findings": findings, "summary": f"Dir enum: {len(findings)} finding(s)", "total_findings": len(findings), "checks_performed": 1, "scan_duration_ms": 0, "interrupted": False}
    elif sub_cmd == "form_fuzz":
        findings = await _form_fuzz(url)
        result = {"findings": findings, "summary": f"Form analysis: {len(findings)} finding(s)", "total_findings": len(findings), "checks_performed": 1, "scan_duration_ms": 0, "interrupted": False}
    elif sub_cmd == "cookie_audit":
        findings = await _cookie_audit(url)
        result = {"findings": findings, "summary": f"Cookie audit: {len(findings)} finding(s)", "total_findings": len(findings), "checks_performed": 1, "scan_duration_ms": 0, "interrupted": False}
    elif sub_cmd == "api_scan":
        findings = await _api_scan(url)
        result = {"findings": findings, "summary": f"API scan: {len(findings)} finding(s)", "total_findings": len(findings), "checks_performed": 1, "scan_duration_ms": 0, "interrupted": False}
    elif sub_cmd == "report":
        result = await _report(args)
    else:
        result = {"findings": [], "summary": f"Unknown command: '{sub_cmd}'. Use 'full_scan <url>' for comprehensive audit.",
                  "total_findings": 0, "checks_performed": 0, "scan_duration_ms": 0, "interrupted": False}

    return result


async def description() -> str:
    return "Comprehensive web application vulnerability scanner covering OWASP Top 10."


async def prompt() -> str:
    return (
        "Use this tool to audit live web applications for security vulnerabilities. "
        "It covers the OWASP Top 10 including SQL injection, XSS, CSRF, SSRF, path traversal, "
        "security headers, CORS, SSL/TLS, information disclosure, authentication issues, and more.\n"
        "- full_scan <url> — Comprehensive OWASP Top 10 audit\n"
        "- sqli_test <url> — SQL injection testing with 15+ payloads\n"
        "- xss_test <url> — XSS testing with 10+ payloads\n"
        "- headers_check <url> — Security headers audit\n"
        "- ssl_check <host> — SSL/TLS configuration check\n"
        "- dir_enum <url> — Directory and file enumeration\n"
        "Each finding includes severity, CWE ID, evidence, and specific remediation steps."
    )


def userFacingName() -> str:
    return "WebAudit"


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    cmd = input_data.get("command", "")
    url = input_data.get("url", "")
    if cmd.startswith("full_scan"):
        return f"WebAudit full scan: {url}"
    return f"WebAudit: {cmd[:60]}"
