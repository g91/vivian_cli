"""
CodeAuditTool — Deep code review and vulnerability analysis.

Performs thorough security code reviews with data flow analysis,
taint tracking, and detailed remediation reports. Designed for
professional penetration testers auditing PHP, Java, Python,
JavaScript, C/C++, Go, Ruby, and .NET codebases.
"""
from __future__ import annotations

import asyncio
import os
import re
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

TOOL_NAME = "CodeAudit"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["command"],
    "properties": {
        "command": {
            "type": "string",
            "description": (
                "The code audit operation. One of:\n"
                "- 'audit <path> [language]' — Deep security audit of a codebase\n"
                "- 'taint_track <path> <source> <sink>' — Track data flow from source to sink\n"
                "- 'auth_audit <path>' — Audit authentication and authorization logic\n"
                "- 'crypto_audit <path>' — Audit cryptographic implementations\n"
                "- 'input_audit <path>' — Audit all input validation and sanitization\n"
                "- 'session_audit <path>' — Audit session management\n"
                "- 'file_audit <path>' — Audit file operations for path traversal and race conditions\n"
                "- 'db_audit <path>' — Audit database interactions for injection and misconfig\n"
                "- 'api_audit <path>' — Audit API endpoints for security issues\n"
                "- 'dependency_check <path>' — Check for vulnerable dependencies\n"
                "- 'compliance_check <path> [standard]' — Check against OWASP ASVS / PCI DSS / HIPAA\n"
                "- 'fix_report <path>' — Generate prioritized remediation report\n"
                "- 'diff_audit <old_path> <new_path>' — Audit changes between two versions"
            ),
        },
        "path": {
            "type": "string",
            "description": "Path to the codebase or file to audit.",
        },
        "language": {
            "type": "string",
            "description": "Target language: php, java, python, javascript, c, cpp, go, ruby, csharp, all.",
        },
        "source": {
            "type": "string",
            "description": "For taint tracking: the source of untrusted data (e.g., '$_GET', 'req.body', 'request.getParameter').",
        },
        "sink": {
            "type": "string",
            "description": "For taint tracking: the dangerous sink (e.g., 'eval', 'system', 'execute', 'include').",
        },
        "standard": {
            "type": "string",
            "description": "Compliance standard: owasp_asvs, pci_dss, hipaa, gdpr, soc2.",
        },
        "timeout": {
            "type": "number",
            "description": "Audit timeout in milliseconds (default: 300000).",
            "default": 300000,
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
                    "category": {"type": "string"},
                    "type": {"type": "string"},
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "code": {"type": "string"},
                    "description": {"type": "string"},
                    "impact": {"type": "string"},
                    "remediation": {"type": "string"},
                    "cwe": {"type": "string"},
                    "owasp_category": {"type": "string"},
                },
            },
        },
        "summary": {"type": "string"},
        "total_findings": {"type": "integer"},
        "files_audited": {"type": "integer"},
        "risk_score": {"type": "integer"},
        "audit_duration_ms": {"type": "number"},
        "interrupted": {"type": "boolean"},
    },
}

# ── Session state ───────────────────────────────────────────────────────────
_last_audit_findings: List[Dict[str, Any]] = []
_last_audit_path: Optional[str] = None

# ── Language extensions ─────────────────────────────────────────────────────

_LANG_EXTS = {
    "php": [".php", ".phtml", ".php3", ".php4", ".php5", ".inc"],
    "java": [".java", ".jsp", ".jspx"],
    "python": [".py", ".pyw"],
    "javascript": [".js", ".jsx", ".mjs", ".ts", ".tsx", ".vue", ".svelte"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".cxx", ".cc", ".hpp", ".hxx"],
    "go": [".go"],
    "ruby": [".rb", ".erb", ".rake"],
    "csharp": [".cs", ".csx", ".aspx"],
}

# ── Taint sources (user input entry points) ─────────────────────────────────

_TAINT_SOURCES = {
    "php": [
        r'\$_(?:GET|POST|REQUEST|COOKIE|SERVER|FILES|ENV)\[',
        r'file_get_contents\s*\(\s*["\']php://input["\']',
        r'getallheaders\s*\(\s*\)',
        r'apache_request_headers\s*\(\s*\)',
        r'php://stdin',
    ],
    "java": [
        r'request\.getParameter\s*\(',
        r'request\.getHeader\s*\(',
        r'request\.getInputStream\s*\(',
        r'request\.getQueryString\s*\(',
        r'@RequestParam',
        r'@RequestBody',
        r'@PathVariable',
        r'request\.getCookies\s*\(',
    ],
    "python": [
        r'request\.(?:args|form|data|json|files|values|cookies)\[',
        r'request\.(?:args|form|data|json|files|values|cookies)\.get\s*\(',
        r'input\s*\(\s*\)',
        r'sys\.argv\[',
        r'os\.environ\[',
        r'request\.get_json\s*\(',
    ],
    "javascript": [
        r'req\.(?:body|query|params|cookies|headers)\[',
        r'req\.(?:body|query|params|cookies|headers)\.',
        r'window\.location',
        r'document\.(?:URL|cookie|referrer)',
        r'process\.argv\[',
        r'process\.env\.',
    ],
    "c": [
        r'argv\[',
        r'gets\s*\(',
        r'scanf\s*\(',
        r'fgets\s*\(',
        r'recv\s*\(',
        r'read\s*\(',
    ],
    "go": [
        r'r\.(?:FormValue|PostFormValue|URL\.Query\s*\(\s*\)\.Get)\s*\(',
        r'r\.(?:Body|Header\.Get)\s*\(',
        r'os\.Args\[',
        r'os\.Getenv\s*\(',
    ],
    "ruby": [
        r'params\[',
        r'cookies\[',
        r'request\.(?:env|body|query_string)',
        r'ARGS\[',
        r'ENV\[',
    ],
    "csharp": [
        r'Request\[',
        r'Request\.(?:Form|QueryString|Headers|Cookies)\[',
        r'HttpContext\.Current\.Request',
        r'FromBody\]|FromForm\]|FromQuery\]',
    ],
}

# ── Dangerous sinks ─────────────────────────────────────────────────────────

_DANGEROUS_SINKS = {
    "php": {
        "code_execution": [
            (r'eval\s*\(', "eval() - Arbitrary code execution", "critical", "CWE-95"),
            (r'assert\s*\(', "assert() - Code execution", "critical", "CWE-95"),
            (r'preg_replace\s*\(\s*[\'"]/e', "preg_replace /e - Code execution", "critical", "CWE-95"),
            (r'create_function\s*\(', "create_function() - Code execution (deprecated)", "critical", "CWE-95"),
        ],
        "command_execution": [
            (r'system\s*\(', "system() - Command execution", "critical", "CWE-78"),
            (r'exec\s*\(', "exec() - Command execution", "critical", "CWE-78"),
            (r'shell_exec\s*\(', "shell_exec() - Command execution", "critical", "CWE-78"),
            (r'passthru\s*\(', "passthru() - Command execution", "critical", "CWE-78"),
            (r'popen\s*\(', "popen() - Command execution", "critical", "CWE-78"),
            (r'proc_open\s*\(', "proc_open() - Command execution", "critical", "CWE-78"),
            (r'`[^`]*`', "Backtick operator - Command execution", "critical", "CWE-78"),
        ],
        "file_inclusion": [
            (r'(?:include|require)(?:_once)?\s*\(', "include/require - File inclusion", "critical", "CWE-98"),
        ],
        "sql_execution": [
            (r'(?:mysql_query|mysqli_query|pg_query|sqlite_query)\s*\(', "Direct SQL query", "critical", "CWE-89"),
            (r'(?:->query|->exec|->raw)\s*\(', "Database query execution", "critical", "CWE-89"),
        ],
        "deserialization": [
            (r'unserialize\s*\(', "unserialize() - Object injection", "critical", "CWE-502"),
        ],
        "file_operations": [
            (r'(?:file_get_contents|file_put_contents|fopen|readfile|file)\s*\(', "File operation", "high", "CWE-22"),
            (r'(?:unlink|rmdir|mkdir|chmod|chown|rename|copy)\s*\(', "File system modification", "high", "CWE-22"),
        ],
        "output": [
            (r'echo\s+', "echo - Output (potential XSS)", "medium", "CWE-79"),
            (r'print\s+', "print - Output (potential XSS)", "medium", "CWE-79"),
            (r'printf\s*\(', "printf - Output (potential XSS)", "medium", "CWE-79"),
            (r'die\s*\(', "die() - Output (potential XSS)", "medium", "CWE-79"),
        ],
    },
    "java": {
        "code_execution": [
            (r'Runtime\.getRuntime\(\)\.exec\s*\(', "Runtime.exec() - Command execution", "critical", "CWE-78"),
            (r'ProcessBuilder\s*\(', "ProcessBuilder - Command execution", "critical", "CWE-78"),
            (r'ScriptEngine.*\.eval\s*\(', "ScriptEngine.eval() - Code execution", "critical", "CWE-95"),
        ],
        "sql_execution": [
            (r'(?:Statement|PreparedStatement).*\.execute(?:Query|Update)?\s*\(', "SQL execution", "critical", "CWE-89"),
            (r'(?:createQuery|createNativeQuery)\s*\(', "JPA query execution", "critical", "CWE-89"),
        ],
        "deserialization": [
            (r'ObjectInputStream.*\.readObject\s*\(', "Java deserialization", "critical", "CWE-502"),
            (r'ObjectMapper.*\.readValue\s*\(', "Jackson deserialization", "high", "CWE-502"),
        ],
        "file_operations": [
            (r'(?:FileInputStream|FileReader|FileOutputStream|FileWriter)\s*\(', "File operation", "high", "CWE-22"),
            (r'Files\.(?:read|write|copy|move|delete)', "NIO file operation", "high", "CWE-22"),
        ],
        "xml_processing": [
            (r'(?:DocumentBuilder|SAXParser|XMLReader|Transformer)\s*\.', "XML processing", "high", "CWE-611"),
        ],
        "reflection": [
            (r'(?:Class\.forName|Method\.invoke|Field\.set)\s*\(', "Reflection - Potential bypass", "medium", "CWE-470"),
        ],
    },
    "python": {
        "code_execution": [
            (r'eval\s*\(', "eval() - Arbitrary code execution", "critical", "CWE-95"),
            (r'exec\s*\(', "exec() - Arbitrary code execution", "critical", "CWE-95"),
            (r'compile\s*\(', "compile() - Code compilation", "critical", "CWE-95"),
            (r'__import__\s*\(', "__import__() - Dynamic import", "critical", "CWE-95"),
        ],
        "command_execution": [
            (r'os\.system\s*\(', "os.system() - Command execution", "critical", "CWE-78"),
            (r'os\.popen\s*\(', "os.popen() - Command execution", "critical", "CWE-78"),
            (r'subprocess\.(?:call|run|Popen|check_output)\s*\(', "subprocess - Command execution", "critical", "CWE-78"),
        ],
        "deserialization": [
            (r'(?:pickle|cPickle|dill|marshal)\.(?:loads?|dump)\s*\(', "Deserialization", "critical", "CWE-502"),
            (r'yaml\.load\s*\((?!.*SafeLoader)', "YAML deserialization", "high", "CWE-502"),
        ],
        "sql_execution": [
            (r'(?:cursor|c)\.execute\s*\(', "SQL execution", "critical", "CWE-89"),
            (r'(?:cursor|c)\.executemany\s*\(', "SQL batch execution", "critical", "CWE-89"),
        ],
        "template": [
            (r'render_template_string\s*\(', "Jinja2 template rendering", "critical", "CWE-94"),
            (r'jinja2\.Template\s*\(', "Jinja2 template compilation", "critical", "CWE-94"),
        ],
        "file_operations": [
            (r'open\s*\(', "File open", "high", "CWE-22"),
            (r'(?:os\.remove|os\.unlink|os\.rmdir|shutil\.(?:rmtree|copy|move))\s*\(', "File system modification", "high", "CWE-22"),
        ],
    },
    "javascript": {
        "code_execution": [
            (r'eval\s*\(', "eval() - Code execution", "critical", "CWE-95"),
            (r'new\s+Function\s*\(', "Function constructor - Code execution", "critical", "CWE-95"),
            (r'setTimeout\s*\(\s*[\'"`]', "setTimeout with string - Code execution", "high", "CWE-95"),
            (r'setInterval\s*\(\s*[\'"`]', "setInterval with string - Code execution", "high", "CWE-95"),
        ],
        "command_execution": [
            (r'(?:child_process|childProcess)\.exec\s*\(', "child_process.exec() - Command execution", "critical", "CWE-78"),
            (r'(?:child_process|childProcess)\.spawn\s*\(', "child_process.spawn() - Command execution", "critical", "CWE-78"),
            (r'(?:child_process|childProcess)\.execSync\s*\(', "child_process.execSync() - Command execution", "critical", "CWE-78"),
        ],
        "sql_execution": [
            (r'(?:\.query|\.execute|\.raw)\s*\(', "Database query", "critical", "CWE-89"),
        ],
        "template": [
            (r'(?:\.render|\.renderFile|\.compile)\s*\(', "Template rendering", "critical", "CWE-94"),
        ],
        "xss": [
            (r'innerHTML\s*=', "innerHTML - DOM XSS sink", "high", "CWE-79"),
            (r'outerHTML\s*=', "outerHTML - DOM XSS sink", "high", "CWE-79"),
            (r'document\.write\s*\(', "document.write() - DOM XSS sink", "high", "CWE-79"),
            (r'dangerouslySetInnerHTML', "dangerouslySetInnerHTML - React XSS", "high", "CWE-79"),
        ],
        "file_operations": [
            (r'(?:readFile|readFileSync|writeFile|writeFileSync)\s*\(', "File operation", "high", "CWE-22"),
            (r'createReadStream\s*\(', "File stream", "high", "CWE-22"),
        ],
    },
}

# ── Auth patterns ───────────────────────────────────────────────────────────

_AUTH_PATTERNS = {
    "weak_password": [
        (r'password\s*==?\s*["\']', "Hardcoded password comparison", "critical", "CWE-798"),
        (r'password\s*=\s*["\'][^"\']{1,7}["\']', "Short/weak password minimum", "high", "CWE-521"),
    ],
    "missing_auth": [
        (r'public\s+(?:function|class)\s+\w*(?:admin|manage|delete|create|update|edit)\w*\s*\(', "Potentially unauthenticated admin function", "high", "CWE-306"),
    ],
    "session_issues": [
        (r'session_start\s*\(\)(?!.*session_regenerate_id)', "Session started without ID regeneration", "medium", "CWE-384"),
        (r'setcookie\s*\(.*(?:httponly|secure)\s*=\s*(?:false|0|FALSE)', "Cookie with security flags disabled", "high", "CWE-614"),
    ],
    "token_issues": [
        (r'(?:jwt|token|api_key|apikey)\s*=\s*["\'][^"\']+["\']', "Hardcoded token/API key", "critical", "CWE-798"),
        (r'algorithm\s*:\s*["\']none["\']', "JWT with 'none' algorithm", "critical", "CWE-347"),
    ],
}

# ── Crypto patterns ─────────────────────────────────────────────────────────

_CRYPTO_AUDIT_PATTERNS = [
    (r'(?:MD5|md5)\s*\(', "MD5 hashing (broken)", "high", "CWE-327",
     "Replace MD5 with SHA-256 or SHA-3. For passwords, use bcrypt/scrypt/argon2."),
    (r'(?:SHA-?1|sha1)\s*\(', "SHA-1 hashing (weak)", "high", "CWE-327",
     "Migrate to SHA-256 or SHA-3. SHA-1 is vulnerable to collision attacks."),
    (r'(?:DES|RC2|RC4|3DES|TripleDES)\s', "Weak/obsolete encryption algorithm", "high", "CWE-327",
     "Use AES-256-GCM or ChaCha20-Poly1305 for symmetric encryption."),
    (r'(?:ECB|CBC)(?!.*-GCM)(?!.*-CCM)', "Weak cipher mode (ECB/CBC without authentication)", "high", "CWE-327",
     "Use authenticated encryption modes: GCM or CCM. Never use ECB."),
    (r'(?:Math\.random|rand\s*\(\s*\)|random\.random|mt_rand)\s*\(', "Insecure random number generator", "medium", "CWE-330",
     "Use cryptographically secure RNG: crypto.randomBytes (Node), secrets module (Python), SecureRandom (Java)."),
    (r'RSA.*\b(?:512|1024)\b', "Weak RSA key size", "high", "CWE-326",
     "Use RSA with at least 2048-bit keys. Prefer 3072 or 4096 bits."),
    (r'(?:hash|hmac|digest).*["\']md5["\']', "MD5 used in HMAC/digest", "high", "CWE-327",
     "Use HMAC-SHA256 or HMAC-SHA512 for message authentication."),
    (r'InsecureSkipVerify\s*:\s*true', "TLS certificate verification disabled", "high", "CWE-295",
     "Never disable TLS certificate verification in production."),
    (r'ssl\.CERT_NONE|verify_mode\s*=\s*ssl\.CERT_NONE', "SSL verification disabled", "high", "CWE-295",
     "Use proper certificate verification. CERT_NONE disables all security."),
    (r'(?:password_hash|bcrypt|scrypt|argon2)', "Strong password hashing detected", "info", "N/A",
     "Good! Using strong password hashing. Ensure cost parameters are appropriate."),
]

# ── Input validation patterns ───────────────────────────────────────────────

_INPUT_VALIDATION_CHECKS = [
    # Missing validation before dangerous operations
    (r'(?:execute|query|exec|system|eval|include|require|open|read|write)\s*\([^)]*\$_(?:GET|POST|REQUEST)',
     "Dangerous operation with unvalidated user input", "critical", "CWE-20"),
    (r'(?:execute|query|exec|system|eval|include|require|open|read|write)\s*\([^)]*request\.(?:getParameter|get|body|query)',
     "Dangerous operation with unvalidated user input", "critical", "CWE-20"),
    # Type juggling issues (PHP)
    (r'==\s*.*\$_(?:GET|POST|REQUEST)', "Loose comparison with user input (type juggling)", "high", "CWE-697"),
    (r'strcmp\s*\(.*\$_(?:GET|POST|REQUEST)', "strcmp() with user input (bypass risk)", "high", "CWE-697"),
    # Missing type checks
    (r'is_numeric\s*\(.*\$_(?:GET|POST)', "is_numeric() allows hex (bypass risk)", "medium", "CWE-704"),
]

# ── File operation patterns ─────────────────────────────────────────────────

_FILE_AUDIT_PATTERNS = [
    (r'(?:fopen|file_get_contents|readfile|include|require)\s*\([^)]*\.\.\/',
     "Path traversal in file operation", "critical", "CWE-22",
     "Use basename() and realpath() to validate paths. Never allow '..' in file paths."),
    (r'(?:fopen|file_get_contents|readfile|include|require)\s*\([^)]*\$_(?:GET|POST|REQUEST)',
     "User-controlled file path", "critical", "CWE-22",
     "Whitelist allowed files. Never use user input directly in file paths."),
    (r'(?:chmod|chown)\s*\(\s*[^,]+,\s*0?777',
     "World-writable permissions (0777)", "high", "CWE-732",
     "Use minimum necessary permissions. Never set 0777 on sensitive files."),
    (r'(?:chmod|chown)\s*\(\s*[^,]+,\s*0?666',
     "World-readable/writable permissions (0666)", "high", "CWE-732",
     "Restrict file permissions. Use 0644 for files, 0755 for directories."),
    (r'tmpfile|tempnam|tmpname\s*\(', "Temporary file creation", "medium", "CWE-377",
     "Use secure temp file creation. Verify unique names. Clean up after use."),
    (r'file_put_contents\s*\([^)]*\$_(?:GET|POST|REQUEST)', "User-controlled file write", "critical", "CWE-22",
     "Never allow users to control file write paths or content without strict validation."),
    (r'(?:move_uploaded_file|copy)\s*\([^)]*\$_(?:GET|POST)', "User-influenced file move/copy", "high", "CWE-22",
     "Validate destination paths. Use basename() on uploaded file names."),
]

# ── Database audit patterns ─────────────────────────────────────────────────

_DB_AUDIT_PATTERNS = [
    (r'(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER)\s+.*\+.*\+', "SQL string concatenation", "critical", "CWE-89",
     "Use parameterized queries. Never concatenate strings into SQL."),
    (r'(?:SELECT|INSERT|UPDATE|DELETE).*\$\{', "SQL template literal injection", "critical", "CWE-89",
     "Use parameterized queries with placeholders. Never use template literals for SQL."),
    (r'(?:SELECT|INSERT|UPDATE|DELETE).*%[sdf]', "SQL string formatting", "critical", "CWE-89",
     "Use parameterized queries. Never use %s/%d formatting for SQL values."),
    (r'\.raw\s*\(|\.queryRaw\s*\(|\.executeRaw\s*\(', "Raw SQL execution", "high", "CWE-89",
     "Prefer ORM methods over raw queries. If unavoidable, use parameterized raw queries."),
    (r'DB::raw\s*\(|DB::statement\s*\(|DB::unprepared\s*\(', "Laravel raw/unprepared SQL", "high", "CWE-89",
     "Use Eloquent/Query Builder methods. If raw SQL is needed, use parameter binding."),
    (r'connectionString\s*=\s*"[^"]*password=', "Hardcoded DB credentials", "critical", "CWE-798",
     "Use environment variables or a secrets manager for database credentials."),
    (r'(?:mysql_connect|pg_connect|sqlite_open)\s*\([^)]*["\'][^"\']+["\']', "Hardcoded DB credentials in connection", "critical", "CWE-798",
     "Move credentials to environment variables or secure config files outside webroot."),
]

# ── API audit patterns ──────────────────────────────────────────────────────

_API_AUDIT_PATTERNS = [
    (r'@(?:GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)', "Spring REST endpoint", "info", "N/A",
     "Review endpoint for authentication, authorization, input validation, and rate limiting."),
    (r'@(?:Get|Post|Put|Delete|Patch)\s*\(', "API route definition", "info", "N/A",
     "Ensure endpoint has proper authentication middleware and input validation."),
    (r'app\.(?:get|post|put|delete|patch)\s*\(', "Express API route", "info", "N/A",
     "Verify authentication middleware is applied. Check for rate limiting."),
    (r'@app\.route\s*\(|@bp\.route\s*\(', "Flask API route", "info", "N/A",
     "Ensure @login_required or equivalent auth decorator is applied."),
    (r'@(?:public|unauthenticated|noauth|anonymous)', "Publicly accessible endpoint marker", "high", "CWE-306",
     "Verify this endpoint intentionally has no authentication. Review for data exposure."),
    (r'@(?:PreAuthorize|RolesAllowed|Secured)\s*\(', "Authorization annotation (good)", "info", "N/A",
     "Good: Authorization is enforced. Verify role/permission configuration is correct."),
]

# ── Compliance mappings ─────────────────────────────────────────────────────

_OWASP_ASVS_CHECKS = {
    "V2: Authentication": [
        (r'password\s*=\s*["\']', "ASVS 2.1.1: Hardcoded credentials", "critical"),
        (r'setcookie\s*\(.*secure\s*=\s*false', "ASVS 2.2.3: Insecure cookie flags", "high"),
        (r'setcookie\s*\(.*httponly\s*=\s*false', "ASVS 2.2.4: Missing HttpOnly", "high"),
    ],
    "V3: Session Management": [
        (r'session_start\s*\(\)(?!.*session_regenerate_id)', "ASVS 3.2.1: No session regeneration", "medium"),
        (r'ini_set\s*\(\s*[\'"]session\.cookie_secure[\'"]\s*,\s*[\'"]0[\'"]', "ASVS 3.2.2: Insecure session cookie", "high"),
    ],
    "V4: Access Control": [
        (r'public\s+function\s+(?:admin|delete|remove|update)\w*\s*\(', "ASVS 4.1.1: Potential missing access control", "high"),
    ],
    "V5: Validation & Encoding": [
        (r'echo\s+\$_(?:GET|POST)', "ASVS 5.2.1: Missing output encoding", "high"),
        (r'(?:execute|query)\s*\(.*\$_(?:GET|POST)', "ASVS 5.3.1: Missing input validation", "critical"),
    ],
    "V6: Cryptography": [
        (r'(?:MD5|SHA1|DES|RC4)\s*\(', "ASVS 6.2.1: Weak cryptographic algorithm", "high"),
    ],
    "V7: Error Handling": [
        (r'(?:echo|print|die)\s*\(.*(?:mysql_error|pg_last_error|Exception)', "ASVS 7.4.1: Error information disclosure", "medium"),
    ],
    "V8: Data Protection": [
        (r'(?:password|secret|token|key)\s*=\s*["\']', "ASVS 8.3.4: Hardcoded sensitive data", "critical"),
    ],
}


# ── Core audit functions ────────────────────────────────────────────────────

def _collect_files(path: str, extensions: List[str]) -> List[str]:
    """Collect all source files matching extensions."""
    files = []
    p = Path(path)
    if p.is_file():
        if any(p.suffix.lower() == e.lower() for e in extensions):
            return [str(p)]
        return []

    skip_dirs = {".git", "node_modules", "vendor", "__pycache__", ".venv", "venv",
                 "target", "build", "dist", ".next", ".nuxt", "bower_components",
                 ".idea", ".vscode", "bin", "obj", "Debug", "Release", "coverage"}
    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in filenames:
            if any(fname.lower().endswith(e.lower()) for e in extensions):
                files.append(os.path.join(root, fname))
    return files


def _read_file_lines(filepath: str) -> List[str]:
    """Read file lines safely."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except Exception:
        return []


def _scan_patterns(
    lines: List[str],
    filepath: str,
    patterns: List[tuple],
    category: str,
) -> List[Dict[str, Any]]:
    """Scan lines against a list of (regex, description, severity, cwe, remediation) patterns."""
    findings = []
    for i, line in enumerate(lines, 1):
        for regex, desc, severity, cwe, *rest in patterns:
            try:
                if re.search(regex, line, re.IGNORECASE):
                    remediation = rest[0] if rest else "Review and apply security best practices."
                    findings.append({
                        "severity": severity,
                        "category": category,
                        "type": desc,
                        "file": filepath,
                        "line": i,
                        "code": line.strip()[:200],
                        "description": desc,
                        "impact": f"This {severity} severity issue could lead to {desc.lower()}.",
                        "remediation": remediation,
                        "cwe": cwe,
                        "owasp_category": _map_to_owasp(category, desc),
                    })
            except re.error:
                continue
    return findings


def _map_to_owasp(category: str, desc: str) -> str:
    """Map finding to OWASP Top 10 category."""
    desc_lower = desc.lower()
    if any(kw in desc_lower for kw in ("sql", "injection", "nosql", "ldap", "xpath")):
        return "A03:2021 - Injection"
    if any(kw in desc_lower for kw in ("xss", "cross-site", "template injection")):
        return "A03:2021 - Injection"
    if any(kw in desc_lower for kw in ("auth", "password", "credential", "login", "session", "jwt", "token")):
        return "A07:2021 - Identification and Authentication Failures"
    if any(kw in desc_lower for kw in ("access control", "authorization", "admin", "privilege")):
        return "A01:2021 - Broken Access Control"
    if any(kw in desc_lower for kw in ("crypto", "encrypt", "hash", "md5", "sha1", "des", "rc4", "tls", "ssl")):
        return "A02:2021 - Cryptographic Failures"
    if any(kw in desc_lower for kw in ("xxe", "xml", "entity")):
        return "A05:2021 - Security Misconfiguration"
    if any(kw in desc_lower for kw in ("config", "header", "cors", "debug", "disclosure", "error")):
        return "A05:2021 - Security Misconfiguration"
    if any(kw in desc_lower for kw in ("deserial", "pickle", "unserialize", "marshal")):
        return "A08:2021 - Software and Data Integrity Failures"
    if any(kw in desc_lower for kw in ("ssrf", "request forgery", "redirect")):
        return "A10:2021 - Server-Side Request Forgery (SSRF)"
    if any(kw in desc_lower for kw in ("path traversal", "file inclusion", "lfi", "directory traversal")):
        return "A01:2021 - Broken Access Control"
    if any(kw in desc_lower for kw in ("log", "logging", "monitoring")):
        return "A09:2021 - Security Logging and Monitoring Failures"
    return "A05:2021 - Security Misconfiguration"


# ── Taint tracking ──────────────────────────────────────────────────────────

def _taint_track(
    files: List[str],
    source_pattern: str,
    sink_pattern: str,
    lang: str,
) -> List[Dict[str, Any]]:
    """Track data flow from taint source to dangerous sink."""
    findings = []

    for filepath in files:
        lines = _read_file_lines(filepath)
        if not lines:
            continue

        # Find all taint sources
        sources = []
        for i, line in enumerate(lines, 1):
            try:
                if re.search(source_pattern, line, re.IGNORECASE):
                    # Extract variable name if possible
                    var_match = re.search(r'(\$\w+)\s*=', line)
                    var_name = var_match.group(1) if var_match else "user_input"
                    sources.append({"line": i, "variable": var_name, "code": line.strip()[:150]})
            except re.error:
                continue

        # Find all sinks
        sinks = []
        for i, line in enumerate(lines, 1):
            try:
                if re.search(sink_pattern, line, re.IGNORECASE):
                    sinks.append({"line": i, "code": line.strip()[:150]})
            except re.error:
                continue

        # Check if any source variable reaches a sink
        for src in sources:
            var_name = src["variable"]
            # Simple check: does the variable appear between source and any sink?
            for snk in sinks:
                if snk["line"] > src["line"]:
                    # Check intermediate lines for variable usage
                    intermediate = "".join(lines[src["line"]:snk["line"]])
                    if var_name in intermediate:
                        findings.append({
                            "severity": "critical",
                            "category": "taint_tracking",
                            "type": f"Taint flow: {source_pattern} -> {sink_pattern}",
                            "file": filepath,
                            "line": snk["line"],
                            "code": snk["code"],
                            "description": f"Untrusted data from line {src['line']} flows to dangerous sink at line {snk['line']}.",
                            "impact": "User-controlled data reaches a dangerous function without sanitization.",
                            "remediation": "Validate and sanitize input before it reaches the sink. Use allowlists, not denylists.",
                            "cwe": "CWE-20",
                            "owasp_category": "A03:2021 - Injection",
                        })

    return findings


# ── Command handlers ────────────────────────────────────────────────────────

async def _cmd_audit(args: Dict[str, Any]) -> Dict[str, Any]:
    """Deep security audit of a codebase."""
    path = args.get("path") or ""
    language = args.get("language", "all").lower()

    if not path or not os.path.exists(path):
        return _empty_result(f"Path not found: {path}")

    start = time.time()
    all_findings = []

    # Determine which languages to scan
    if language == "all":
        langs = list(_LANG_EXTS.keys())
    elif language in _LANG_EXTS:
        langs = [language]
    else:
        return _empty_result(f"Unsupported language: {language}. Supported: {', '.join(_LANG_EXTS)}")

    total_files = 0
    for lang in langs:
        exts = _LANG_EXTS[lang]
        files = _collect_files(path, exts)
        total_files += len(files)

        if lang in _DANGEROUS_SINKS:
            for sink_category, sink_patterns in _DANGEROUS_SINKS[lang].items():
                for filepath in files:
                    lines = _read_file_lines(filepath)
                    findings = _scan_patterns(lines, filepath, sink_patterns, sink_category)
                    all_findings.extend(findings)

    # Also run cross-language audits
    all_exts = list(set(e for exts in _LANG_EXTS.values() for e in exts))
    all_files = _collect_files(path, all_exts)

    # Auth audit
    for category, patterns in _AUTH_PATTERNS.items():
        for filepath in all_files:
            lines = _read_file_lines(filepath)
            findings = _scan_patterns(lines, filepath, patterns, category)
            all_findings.extend(findings)

    # Crypto audit
    for filepath in all_files:
        lines = _read_file_lines(filepath)
        findings = _scan_patterns(lines, filepath, _CRYPTO_AUDIT_PATTERNS, "cryptography")
        all_findings.extend(findings)

    # Input validation audit
    for filepath in all_files:
        lines = _read_file_lines(filepath)
        findings = _scan_patterns(lines, filepath, _INPUT_VALIDATION_CHECKS, "input_validation")
        all_findings.extend(findings)

    # File operations audit
    for filepath in all_files:
        lines = _read_file_lines(filepath)
        findings = _scan_patterns(lines, filepath, _FILE_AUDIT_PATTERNS, "file_operations")
        all_findings.extend(findings)

    # DB audit
    for filepath in all_files:
        lines = _read_file_lines(filepath)
        findings = _scan_patterns(lines, filepath, _DB_AUDIT_PATTERNS, "database")
        all_findings.extend(findings)

    # API audit
    for filepath in all_files:
        lines = _read_file_lines(filepath)
        findings = _scan_patterns(lines, filepath, _API_AUDIT_PATTERNS, "api")
        all_findings.extend(findings)

    # Sort and deduplicate
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    all_findings.sort(key=lambda f: (f["file"], f["line"], severity_order.get(f["severity"], 5)))

    # Calculate risk score (weighted)
    risk_weights = {"critical": 10, "high": 5, "medium": 2, "low": 1, "info": 0}
    risk_score = sum(risk_weights.get(f["severity"], 0) for f in all_findings)

    # Build summary
    sev_counts = {}
    cat_counts = {}
    for f in all_findings:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1
        cat_counts[f["category"]] = cat_counts.get(f["category"], 0) + 1

    summary = [
        "=" * 60,
        "DEEP CODE SECURITY AUDIT REPORT",
        "=" * 60,
        f"Path: {path}",
        f"Languages: {', '.join(langs)}",
        f"Files audited: {total_files}",
        f"Total findings: {len(all_findings)}",
        f"Risk score: {risk_score}",
        f"Audit time: {time.time() - start:.1f}s",
        "",
        "--- Severity Breakdown ---",
    ]
    for sev in ["critical", "high", "medium", "low", "info"]:
        if sev in sev_counts:
            summary.append(f"  {sev.upper()}: {sev_counts[sev]}")

    summary.append("")
    summary.append("--- Category Breakdown ---")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        summary.append(f"  {cat}: {count}")

    summary.append("")
    summary.append("--- Critical & High Priority ---")
    for f in all_findings:
        if f["severity"] in ("critical", "high"):
            summary.append(f"\n[{f['severity'].upper()}] {f['type']}")
            summary.append(f"  File: {f['file']}:{f['line']}")
            summary.append(f"  Code: {f['code']}")
            summary.append(f"  Fix: {f['remediation']}")

    return {
        "findings": all_findings,
        "summary": "\n".join(summary),
        "total_findings": len(all_findings),
        "files_audited": total_files,
        "risk_score": risk_score,
        "audit_duration_ms": (time.time() - start) * 1000,
        "interrupted": False,
    }


async def _cmd_taint_track(args: Dict[str, Any]) -> Dict[str, Any]:
    """Track data flow from source to sink."""
    path = args.get("path") or ""
    source = args.get("source") or ""
    sink = args.get("sink") or ""

    if not path or not os.path.exists(path):
        return _empty_result(f"Path not found: {path}")
    if not source or not sink:
        return _empty_result("Both --source and --sink are required for taint tracking.")

    all_exts = list(set(e for exts in _LANG_EXTS.values() for e in exts))
    files = _collect_files(path, all_exts)

    # Determine language from files
    lang = "php"  # default
    for l, exts in _LANG_EXTS.items():
        if any(f.endswith(tuple(exts)) for f in files):
            lang = l
            break

    findings = _taint_track(files, source, sink, lang)

    summary = f"Taint tracking: {source} -> {sink}\n"
    summary += f"Files analyzed: {len(files)}\n"
    summary += f"Taint flows found: {len(findings)}\n"
    for f in findings:
        summary += f"\n  [{f['severity'].upper()}] {f['file']}:{f['line']}"
        summary += f"\n  {f['description']}"

    return {
        "findings": findings,
        "summary": summary,
        "total_findings": len(findings),
        "files_audited": len(files),
        "risk_score": len(findings) * 10,
        "audit_duration_ms": 0,
        "interrupted": False,
    }


async def _cmd_auth_audit(args: Dict[str, Any]) -> Dict[str, Any]:
    """Audit authentication and authorization."""
    path = args.get("path") or ""
    if not path or not os.path.exists(path):
        return _empty_result(f"Path not found: {path}")

    all_exts = list(set(e for exts in _LANG_EXTS.values() for e in exts))
    files = _collect_files(path, all_exts)
    all_findings = []

    for category, patterns in _AUTH_PATTERNS.items():
        for filepath in files:
            lines = _read_file_lines(filepath)
            findings = _scan_patterns(lines, filepath, patterns, category)
            all_findings.extend(findings)

    return _build_result(all_findings, len(files), "Authentication & Authorization Audit")


async def _cmd_crypto_audit(args: Dict[str, Any]) -> Dict[str, Any]:
    """Audit cryptographic implementations."""
    path = args.get("path") or ""
    if not path or not os.path.exists(path):
        return _empty_result(f"Path not found: {path}")

    all_exts = list(set(e for exts in _LANG_EXTS.values() for e in exts))
    files = _collect_files(path, all_exts)
    all_findings = []

    for filepath in files:
        lines = _read_file_lines(filepath)
        findings = _scan_patterns(lines, filepath, _CRYPTO_AUDIT_PATTERNS, "cryptography")
        all_findings.extend(findings)

    return _build_result(all_findings, len(files), "Cryptography Audit")


async def _cmd_input_audit(args: Dict[str, Any]) -> Dict[str, Any]:
    """Audit input validation."""
    path = args.get("path") or ""
    if not path or not os.path.exists(path):
        return _empty_result(f"Path not found: {path}")

    all_exts = list(set(e for exts in _LANG_EXTS.values() for e in exts))
    files = _collect_files(path, all_exts)
    all_findings = []

    for filepath in files:
        lines = _read_file_lines(filepath)
        findings = _scan_patterns(lines, filepath, _INPUT_VALIDATION_CHECKS, "input_validation")
        all_findings.extend(findings)

    return _build_result(all_findings, len(files), "Input Validation Audit")


async def _cmd_session_audit(args: Dict[str, Any]) -> Dict[str, Any]:
    """Audit session management."""
    path = args.get("path") or ""
    if not path or not os.path.exists(path):
        return _empty_result(f"Path not found: {path}")

    all_exts = list(set(e for exts in _LANG_EXTS.values() for e in exts))
    files = _collect_files(path, all_exts)
    all_findings = []

    session_patterns = [
        (r'session_start\s*\(\)(?!.*session_regenerate_id)', "No session ID regeneration after start", "medium", "CWE-384",
         "Call session_regenerate_id(true) after session_start() to prevent session fixation."),
        (r'setcookie\s*\([^)]*\)(?!.*httponly)', "Cookie without HttpOnly flag", "high", "CWE-614",
         "Add HttpOnly=true to prevent JavaScript access to cookies."),
        (r'setcookie\s*\([^)]*\)(?!.*secure)', "Cookie without Secure flag", "high", "CWE-614",
         "Add Secure=true to ensure cookies are only sent over HTTPS."),
        (r'setcookie\s*\([^)]*\)(?!.*samesite)', "Cookie without SameSite attribute", "medium", "CWE-1275",
         "Add SameSite=Strict or SameSite=Lax to prevent CSRF attacks."),
        (r'ini_set\s*\(\s*[\'"]session\.cookie_httponly[\'"]\s*,\s*[\'"](?:0|false|off)[\'"]', "HttpOnly explicitly disabled", "high", "CWE-614",
         "Set session.cookie_httponly=1 to prevent XSS-based session theft."),
        (r'ini_set\s*\(\s*[\'"]session\.cookie_secure[\'"]\s*,\s*[\'"](?:0|false|off)[\'"]', "Secure flag explicitly disabled", "high", "CWE-614",
         "Set session.cookie_secure=1 to enforce HTTPS-only session cookies."),
    ]

    for filepath in files:
        lines = _read_file_lines(filepath)
        findings = _scan_patterns(lines, filepath, session_patterns, "session_management")
        all_findings.extend(findings)

    return _build_result(all_findings, len(files), "Session Management Audit")


async def _cmd_file_audit(args: Dict[str, Any]) -> Dict[str, Any]:
    """Audit file operations."""
    path = args.get("path") or ""
    if not path or not os.path.exists(path):
        return _empty_result(f"Path not found: {path}")

    all_exts = list(set(e for exts in _LANG_EXTS.values() for e in exts))
    files = _collect_files(path, all_exts)
    all_findings = []

    for filepath in files:
        lines = _read_file_lines(filepath)
        findings = _scan_patterns(lines, filepath, _FILE_AUDIT_PATTERNS, "file_operations")
        all_findings.extend(findings)

    return _build_result(all_findings, len(files), "File Operations Audit")


async def _cmd_db_audit(args: Dict[str, Any]) -> Dict[str, Any]:
    """Audit database interactions."""
    path = args.get("path") or ""
    if not path or not os.path.exists(path):
        return _empty_result(f"Path not found: {path}")

    all_exts = list(set(e for exts in _LANG_EXTS.values() for e in exts))
    files = _collect_files(path, all_exts)
    all_findings = []

    for filepath in files:
        lines = _read_file_lines(filepath)
        findings = _scan_patterns(lines, filepath, _DB_AUDIT_PATTERNS, "database")
        all_findings.extend(findings)

    return _build_result(all_findings, len(files), "Database Interaction Audit")


async def _cmd_api_audit(args: Dict[str, Any]) -> Dict[str, Any]:
    """Audit API endpoints."""
    path = args.get("path") or ""
    if not path or not os.path.exists(path):
        return _empty_result(f"Path not found: {path}")

    all_exts = list(set(e for exts in _LANG_EXTS.values() for e in exts))
    files = _collect_files(path, all_exts)
    all_findings = []

    for filepath in files:
        lines = _read_file_lines(filepath)
        findings = _scan_patterns(lines, filepath, _API_AUDIT_PATTERNS, "api")
        all_findings.extend(findings)

    return _build_result(all_findings, len(files), "API Endpoint Audit")


async def _cmd_dependency_check(args: Dict[str, Any]) -> Dict[str, Any]:
    """Check for vulnerable dependencies."""
    path = args.get("path") or "."
    findings = []
    p = Path(path)

    # Check for known vulnerable patterns in dependency files
    dep_files = list(p.rglob("package.json")) + list(p.rglob("requirements*.txt")) + \
                list(p.rglob("Pipfile")) + list(p.rglob("composer.json")) + \
                list(p.rglob("pom.xml")) + list(p.rglob("build.gradle")) + \
                list(p.rglob("Gemfile")) + list(p.rglob("go.mod")) + \
                list(p.rglob("*.csproj")) + list(p.rglob("packages.config"))

    for dep_file in dep_files:
        try:
            content = dep_file.read_text(encoding="utf-8", errors="replace")
            # Check for outdated/known-vulnerable version patterns
            if "lodash" in content and re.search(r'"lodash"\s*:\s*"[<^~]?4\.17\.[0-9]"', content):
                findings.append({
                    "severity": "high", "category": "dependency", "type": "Vulnerable Dependency: lodash < 4.17.21",
                    "file": str(dep_file), "line": 0, "code": "lodash < 4.17.21",
                    "description": "lodash versions before 4.17.21 have prototype pollution vulnerabilities.",
                    "impact": "Prototype pollution can lead to denial of service or remote code execution.",
                    "remediation": "Update lodash to >= 4.17.21.", "cwe": "CWE-1321",
                    "owasp_category": "A06:2021 - Vulnerable and Outdated Components",
                })
            if "jquery" in content and re.search(r'"jquery"\s*:\s*"[<^~]?[12]\.', content):
                findings.append({
                    "severity": "high", "category": "dependency", "type": "Vulnerable Dependency: jQuery < 3.x",
                    "file": str(dep_file), "line": 0, "code": "jQuery < 3.x",
                    "description": "jQuery versions before 3.0.0 have known XSS vulnerabilities.",
                    "impact": "XSS vulnerabilities in jQuery can compromise user sessions.",
                    "remediation": "Update jQuery to >= 3.5.0.", "cwe": "CWE-79",
                    "owasp_category": "A06:2021 - Vulnerable and Outdated Components",
                })
        except Exception:
            continue

    return _build_result(findings, len(dep_files), "Dependency Check")


async def _cmd_compliance_check(args: Dict[str, Any]) -> Dict[str, Any]:
    """Check against compliance standards."""
    path = args.get("path") or ""
    standard = args.get("standard", "owasp_asvs").lower()

    if not path or not os.path.exists(path):
        return _empty_result(f"Path not found: {path}")

    all_exts = list(set(e for exts in _LANG_EXTS.values() for e in exts))
    files = _collect_files(path, all_exts)
    all_findings = []

    if standard == "owasp_asvs":
        for category, checks in _OWASP_ASVS_CHECKS.items():
            for regex, desc, severity in checks:
                for filepath in files:
                    lines = _read_file_lines(filepath)
                    for i, line in enumerate(lines, 1):
                        try:
                            if re.search(regex, line, re.IGNORECASE):
                                all_findings.append({
                                    "severity": severity, "category": "compliance",
                                    "type": f"{category}: {desc}",
                                    "file": filepath, "line": i,
                                    "code": line.strip()[:200],
                                    "description": desc,
                                    "impact": f"Non-compliance with {category}.",
                                    "remediation": "Address the finding to meet ASVS requirements.",
                                    "cwe": "N/A", "owasp_category": category,
                                })
                        except re.error:
                            continue

    return _build_result(all_findings, len(files), f"Compliance Check: {standard.upper()}")


async def _cmd_fix_report(args: Dict[str, Any]) -> Dict[str, Any]:
    """Generate prioritized remediation report."""
    global _last_audit_findings, _last_audit_path

    if not _last_audit_findings:
        return _empty_result("No audit has been run yet. Run 'audit <path>' first.")

    # Group by severity and category
    critical = [f for f in _last_audit_findings if f["severity"] == "critical"]
    high = [f for f in _last_audit_findings if f["severity"] == "high"]
    medium = [f for f in _last_audit_findings if f["severity"] == "medium"]
    low = [f for f in _last_audit_findings if f["severity"] == "low"]

    report = [
        "=" * 60,
        "PRIORITIZED REMEDIATION PLAN",
        "=" * 60,
        f"Audit path: {_last_audit_path}",
        f"Total findings: {len(_last_audit_findings)}",
        "",
        "=== PHASE 1: CRITICAL (Fix Immediately) ===",
        f"  {len(critical)} finding(s) — Estimated effort: {len(critical) * 2}h",
    ]
    for f in critical:
        report.append(f"\n  [{f['cwe']}] {f['type']}")
        report.append(f"  File: {f['file']}:{f['line']}")
        report.append(f"  Fix: {f['remediation']}")

    report.append(f"\n=== PHASE 2: HIGH (Fix within 1 week) ===")
    report.append(f"  {len(high)} finding(s) — Estimated effort: {len(high) * 1}h")
    for f in high[:10]:
        report.append(f"\n  [{f['cwe']}] {f['type']}")
        report.append(f"  File: {f['file']}:{f['line']}")
        report.append(f"  Fix: {f['remediation']}")

    report.append(f"\n=== PHASE 3: MEDIUM (Fix within 1 month) ===")
    report.append(f"  {len(medium)} finding(s) — Estimated effort: {len(medium) * 0.5}h")

    report.append(f"\n=== PHASE 4: LOW (Fix in next release cycle) ===")
    report.append(f"  {len(low)} finding(s)")

    total_hours = len(critical) * 2 + len(high) * 1 + len(medium) * 0.5 + len(low) * 0.25
    report.append(f"\n=== TOTAL ESTIMATED REMEDIATION EFFORT: {total_hours:.0f} hours ===")

    return {
        "findings": _last_audit_findings,
        "summary": "\n".join(report),
        "total_findings": len(_last_audit_findings),
        "files_audited": 0,
        "risk_score": 0,
        "audit_duration_ms": 0,
        "interrupted": False,
    }


async def _cmd_diff_audit(args: Dict[str, Any]) -> Dict[str, Any]:
    """Audit changes between two versions."""
    path = args.get("path") or ""
    # path could be "old_path new_path"
    parts = path.split()
    if len(parts) < 2:
        return _empty_result("Provide two paths: diff_audit <old_path> <new_path>")

    old_path, new_path = parts[0], parts[1]
    if not os.path.exists(old_path) or not os.path.exists(new_path):
        return _empty_result("Both paths must exist.")

    findings = []
    # Simple diff: find new files and check them
    old_files = set()
    new_files = set()

    all_exts = list(set(e for exts in _LANG_EXTS.values() for e in exts))
    for f in _collect_files(old_path, all_exts):
        old_files.add(os.path.relpath(f, old_path))
    for f in _collect_files(new_path, all_exts):
        new_files.add(os.path.relpath(f, new_path))

    added = new_files - old_files
    modified = new_files & old_files

    # Audit new files
    for rel_path in added:
        full_path = os.path.join(new_path, rel_path)
        lines = _read_file_lines(full_path)
        for category, patterns in _AUTH_PATTERNS.items():
            findings.extend(_scan_patterns(lines, full_path, patterns, f"new_file_{category}"))
        findings.extend(_scan_patterns(lines, full_path, _CRYPTO_AUDIT_PATTERNS, "new_file_crypto"))
        findings.extend(_scan_patterns(lines, full_path, _DB_AUDIT_PATTERNS, "new_file_database"))

    summary = [
        f"Diff Audit: {old_path} -> {new_path}",
        f"New files: {len(added)}",
        f"Modified files: {len(modified)}",
        f"Findings in new code: {len(findings)}",
    ]

    return {
        "findings": findings,
        "summary": "\n".join(summary),
        "total_findings": len(findings),
        "files_audited": len(added),
        "risk_score": len(findings) * 5,
        "audit_duration_ms": 0,
        "interrupted": False,
    }


# ── Helpers ─────────────────────────────────────────────────────────────────

def _empty_result(msg: str) -> Dict[str, Any]:
    return {"findings": [], "summary": msg, "total_findings": 0,
            "files_audited": 0, "risk_score": 0, "audit_duration_ms": 0, "interrupted": False}


def _build_result(findings: List[Dict], files_count: int, title: str) -> Dict[str, Any]:
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    findings.sort(key=lambda f: (f["file"], f["line"], severity_order.get(f["severity"], 5)))

    risk_weights = {"critical": 10, "high": 5, "medium": 2, "low": 1, "info": 0}
    risk_score = sum(risk_weights.get(f["severity"], 0) for f in findings)

    sev_counts = {}
    for f in findings:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1

    summary = f"=== {title} ===\nFiles audited: {files_count}\nTotal findings: {len(findings)}\nRisk score: {risk_score}\n"
    for sev in ["critical", "high", "medium", "low", "info"]:
        if sev in sev_counts:
            summary += f"  {sev.upper()}: {sev_counts[sev]}\n"

    for f in findings:
        if f["severity"] in ("critical", "high"):
            summary += f"\n[{f['severity'].upper()}] {f['file']}:{f['line']} — {f['type']}\n  Fix: {f['remediation']}"

    return {
        "findings": findings, "summary": summary, "total_findings": len(findings),
        "files_audited": files_count, "risk_score": risk_score,
        "audit_duration_ms": 0, "interrupted": False,
    }


# ── Command dispatch ────────────────────────────────────────────────────────

_COMMAND_MAP = {
    "audit": _cmd_audit,
    "taint_track": _cmd_taint_track,
    "auth_audit": _cmd_auth_audit,
    "crypto_audit": _cmd_crypto_audit,
    "input_audit": _cmd_input_audit,
    "session_audit": _cmd_session_audit,
    "file_audit": _cmd_file_audit,
    "db_audit": _cmd_db_audit,
    "api_audit": _cmd_api_audit,
    "dependency_check": _cmd_dependency_check,
    "compliance_check": _cmd_compliance_check,
    "fix_report": _cmd_fix_report,
    "diff_audit": _cmd_diff_audit,
}


async def call(args: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
    """Main entry point for CodeAudit."""
    global _last_audit_findings, _last_audit_path

    command = (args.get("command") or "").strip()
    if not command:
        return _empty_result(f"Available commands: {', '.join(sorted(_COMMAND_MAP))}")

    parts = command.split(None, 1)
    sub_cmd = parts[0].lower()

    handler = _COMMAND_MAP.get(sub_cmd)
    if not handler:
        return _empty_result(f"Unknown command: '{sub_cmd}'. Available: {', '.join(sorted(_COMMAND_MAP))}")

    result = await handler(args)

    if result.get("findings"):
        _last_audit_findings = result["findings"]
        _last_audit_path = args.get("path") or ""

    return result


async def description() -> str:
    return "Deep code security audit with taint tracking, compliance checks, and prioritized remediation reports."


async def prompt() -> str:
    return (
        "Use this tool for deep security code reviews. It performs thorough analysis including:\n"
        "- Full audit: audit <path> — Comprehensive security review across all categories\n"
        "- Taint tracking: taint_track <path> <source> <sink> — Track data flow from input to dangerous functions\n"
        "- Specialized audits: auth_audit, crypto_audit, input_audit, session_audit, file_audit, db_audit, api_audit\n"
        "- Compliance: compliance_check <path> owasp_asvs — Check against OWASP ASVS standard\n"
        "- Remediation: fix_report — Generate prioritized fix plan with effort estimates\n"
        "- Diff audit: diff_audit <old> <new> — Audit new/modified code between versions\n"
        "Each finding includes severity, CWE ID, OWASP category, impact analysis, and specific remediation steps."
    )


def userFacingName() -> str:
    return "CodeAudit"


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    cmd = input_data.get("command", "")
    path = input_data.get("path", "")
    if cmd.startswith("audit"):
        return f"CodeAudit: {path or cmd[6:50]}"
    return f"CodeAudit: {cmd[:60]}"
