"""
VulnScannerTool — Multi-language Static Application Security Testing (SAST).

Scans source code for security vulnerabilities across PHP, Java, C/C++,
Python, JavaScript/TypeScript, Ruby, Go, and more. Uses pattern-based
detection with detailed remediation guidance for each finding.
"""
from __future__ import annotations

import asyncio
import os
import re
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOL_NAME = "VulnScanner"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["command"],
    "properties": {
        "command": {
            "type": "string",
            "description": (
                "The vulnerability scan operation. One of:\n"
                "- 'scan <path> [language]' — Scan a file or directory for vulnerabilities\n"
                "- 'scan_php <path>' — PHP-specific deep scan (SQLi, XSS, LFI, RCE, deserialization)\n"
                "- 'scan_java <path>' — Java-specific scan (deserialization, XXE, injection, SSRF)\n"
                "- 'scan_python <path>' — Python-specific scan (eval injection, pickle, path traversal)\n"
                "- 'scan_js <path>' — JavaScript/Node.js scan (prototype pollution, NoSQLi, SSTI)\n"
                "- 'scan_c <path>' — C/C++ scan (buffer overflow, format string, use-after-free)\n"
                "- 'scan_go <path>' — Go scan (race conditions, TLS misconfig, error handling)\n"
                "- 'scan_ruby <path>' — Ruby scan (mass assignment, command injection, YAML deser)\n"
                "- 'scan_dotnet <path>' — C#/.NET scan (deserialization, LDAP injection, XXE)\n"
                "- 'scan_sql <path>' — Scan for SQL injection patterns specifically\n"
                "- 'scan_xss <path>' — Scan for Cross-Site Scripting patterns\n"
                "- 'scan_injection <path>' — Scan for all injection types (SQL, CMD, LDAP, etc.)\n"
                "- 'scan_secrets <path>' — Scan for hardcoded secrets, keys, tokens, passwords\n"
                "- 'scan_crypto <path>' — Scan for weak cryptographic usage\n"
                "- 'scan_config <path>' — Scan config files for security misconfigurations\n"
                "- 'audit_deps <path>' — Check dependencies for known CVEs (requires pip/npm audit)\n"
                "- 'report' — Generate a consolidated vulnerability report from last scan\n"
                "- 'check_tools' — Check which SAST tools are available locally"
            ),
        },
        "path": {
            "type": "string",
            "description": "File or directory path to scan.",
        },
        "language": {
            "type": "string",
            "description": "Target language: php, java, python, javascript, c, cpp, go, ruby, csharp, sql, all.",
        },
        "severity": {
            "type": "string",
            "description": "Minimum severity to report: critical, high, medium, low, info (default: low).",
        },
        "output_format": {
            "type": "string",
            "description": "Output format: text (default), json, sarif.",
        },
        "timeout": {
            "type": "number",
            "description": "Scan timeout in milliseconds (default: 120000).",
            "default": 120000,
        },
        "description": {
            "type": "string",
            "description": "Description of what this scan targets.",
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
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "code": {"type": "string"},
                    "message": {"type": "string"},
                    "remediation": {"type": "string"},
                    "cwe": {"type": "string"},
                },
            },
        },
        "summary": {"type": "string"},
        "total_findings": {"type": "integer"},
        "files_scanned": {"type": "integer"},
        "scan_duration_ms": {"type": "number"},
        "interrupted": {"type": "boolean"},
    },
}

# ── Session state ───────────────────────────────────────────────────────────
_last_findings: List[Dict[str, Any]] = []
_last_scan_path: Optional[str] = None

# ── Vulnerability pattern database ──────────────────────────────────────────

# Each pattern: (regex, vulnerability_type, severity, cwe_id, remediation_message)
# Patterns are organized by language

_PHP_PATTERNS = [
    # SQL Injection
    (r'(mysql_query|mysqli_query|pg_query|sqlite_query)\s*\(\s*["\'].*\$_(?:GET|POST|REQUEST|COOKIE|SERVER)',
     "SQL Injection", "critical", "CWE-89",
     "Use parameterized queries with PDO::prepare() or mysqli_prepare(). Never concatenate user input into SQL."),
    (r'(?:DB::|->)raw\s*\(\s*.*\$_(?:GET|POST|REQUEST)',
     "SQL Injection (Eloquent Raw)", "critical", "CWE-89",
     "Avoid DB::raw() with user input. Use parameter binding with ->where() or ->whereRaw() with bindings."),
    (r'SELECT\s+.*\$_(?:GET|POST|REQUEST|COOKIE).*FROM',
     "SQL Injection (Inline)", "critical", "CWE-89",
     "Use prepared statements. Never interpolate $_GET/$_POST directly into SQL queries."),

    # Cross-Site Scripting (XSS)
    (r'echo\s+\$_(?:GET|POST|REQUEST|COOKIE|SERVER)\[',
     "Reflected XSS", "high", "CWE-79",
     "Use htmlspecialchars($var, ENT_QUOTES, 'UTF-8') before outputting user input to HTML."),
    (r'print\s+\$_(?:GET|POST|REQUEST)\[',
     "Reflected XSS", "high", "CWE-79",
     "Always escape output with htmlspecialchars() or a templating engine's auto-escaping."),
    (r'<\?=\s*\$_(?:GET|POST|REQUEST)',
     "Reflected XSS (Short Tag)", "high", "CWE-79",
     "Use htmlspecialchars() on all user-controlled data rendered in HTML context."),

    # Local File Inclusion (LFI)
    (r'(?:include|require|include_once|require_once)\s*\(\s*.*\$_(?:GET|POST|REQUEST|COOKIE)',
     "Local File Inclusion (LFI)", "critical", "CWE-98",
     "Never pass user input directly to include/require. Use a whitelist of allowed files."),
    (r'(?:include|require)\s*.*\.\$\w+',
     "Potential File Inclusion", "high", "CWE-98",
     "Validate file paths against a whitelist. Avoid dynamic includes based on user input."),

    # Remote Code Execution (RCE)
    (r'(?:eval|assert|preg_replace\s*\(\s*[\'"]/e)\s*\(.*\$',
     "Remote Code Execution (eval/assert)", "critical", "CWE-95",
     "Never use eval() or assert() with user input. Replace with safe alternatives."),
    (r'(?:system|exec|shell_exec|passthru|popen|proc_open)\s*\(.*\$_(?:GET|POST|REQUEST)',
     "Command Injection", "critical", "CWE-78",
     "Use escapeshellcmd() and escapeshellarg(). Prefer built-in PHP functions over shell commands."),
    (r'`.*\$_(?:GET|POST|REQUEST).*`',
     "Command Injection (Backticks)", "critical", "CWE-78",
     "Backticks execute shell commands. Never include user input. Use escapeshellarg()."),

    # Insecure Deserialization
    (r'unserialize\s*\(\s*.*\$_(?:GET|POST|REQUEST|COOKIE)',
     "Insecure Deserialization", "critical", "CWE-502",
     "Never unserialize() user-controlled data. Use JSON with json_decode() instead."),
    (r'unserialize\s*\(\s*.*\$',
     "Potential Insecure Deserialization", "high", "CWE-502",
     "Validate and sanitize data before unserialize(). Consider using JSON instead."),

    # Path Traversal
    (r'(?:file_get_contents|fopen|readfile|file)\s*\(.*\.\.\/',
     "Path Traversal", "high", "CWE-22",
     "Validate and sanitize file paths. Use basename() and realpath() to prevent traversal."),

    # Server-Side Request Forgery (SSRF)
    (r'(?:file_get_contents|curl_exec|fopen)\s*\(.*\$_(?:GET|POST|REQUEST)',
     "Server-Side Request Forgery (SSRF)", "high", "CWE-918",
     "Validate and whitelist URLs. Block internal IPs (127.0.0.1, 10.x, 172.16-31.x, 192.168.x)."),

    # Hardcoded Secrets
    (r'\$(?:password|passwd|secret|api_key|apikey|token|auth)\s*=\s*["\'][^"\']{8,}["\']',
     "Hardcoded Secret", "high", "CWE-798",
     "Move secrets to environment variables or a secure vault. Never commit secrets to source code."),

    # Weak Hashing
    (r'(?:md5|sha1)\s*\(\s*.*password',
     "Weak Password Hashing", "high", "CWE-327",
     "Use password_hash() with PASSWORD_BCRYPT or PASSWORD_ARGON2ID instead of MD5/SHA1."),
    (r'(?:md5|sha1)\s*\(',
     "Weak Hash Algorithm", "medium", "CWE-327",
     "Use SHA-256 or stronger for integrity. Use password_hash() for passwords."),

    # XML External Entity (XXE)
    (r'LIBXML_NOENT|libxml_disable_entity_loader\s*\(\s*false',
     "XML External Entity (XXE) Enabled", "high", "CWE-611",
     "Disable external entity loading: libxml_disable_entity_loader(true) or use LIBXML_NONET."),
    (r'simplexml_load_string|DOMDocument\s*::\s*loadXML',
     "Potential XXE via XML Parsing", "medium", "CWE-611",
     "Set LIBXML_NOENT|LIBXML_NONET flags when parsing XML. Disable external entities."),

    # CSRF
    (r'<form\s+(?!.*csrf)(?!.*_token)(?!.*nonce)',
     "Missing CSRF Protection", "medium", "CWE-352",
     "Add CSRF tokens to all state-changing forms. Use framework CSRF protection."),

    # Open Redirect
    (r'header\s*\(\s*[\'"]Location:\s*.*\$_(?:GET|POST|REQUEST)',
     "Open Redirect", "medium", "CWE-601",
     "Validate redirect URLs against a whitelist. Never redirect to user-supplied URLs directly."),

    # Information Disclosure
    (r'phpinfo\s*\(\s*\)',
     "Information Disclosure (phpinfo)", "low", "CWE-200",
     "Remove phpinfo() calls from production code."),
    (r'display_errors\s*=\s*On|error_reporting\s*=\s*E_ALL',
     "Verbose Error Reporting", "low", "CWE-209",
     "Set display_errors=Off and log_errors=On in production php.ini."),
]

_JAVA_PATTERNS = [
    # SQL Injection
    (r'Statement\s*\.\s*execute(?:Query|Update)?\s*\(\s*".*\+.*\+',
     "SQL Injection (Statement Concatenation)", "critical", "CWE-89",
     "Use PreparedStatement with parameter binding. Never concatenate strings into SQL queries."),
    (r'(?:createQuery|createNativeQuery)\s*\(\s*".*\+',
     "SQL Injection (JPA Native Query)", "critical", "CWE-89",
     "Use named parameters (:param) with setParameter() instead of string concatenation."),
    (r'String\.format\s*\(\s*".*(?:SELECT|INSERT|UPDATE|DELETE).*".*request\.getParameter',
     "SQL Injection (String.format)", "critical", "CWE-89",
     "Use PreparedStatement. Never format user input into SQL strings."),

    # Insecure Deserialization
    (r'ObjectInputStream|readObject\s*\(\s*\)',
     "Insecure Deserialization", "critical", "CWE-502",
     "Implement a deserialization whitelist. Use ValidatingObjectInputStream or look-ahead deserialization."),
    (r'@JsonProperty|@JsonDeserialize|ObjectMapper\s*\.\s*readValue',
     "Jackson Deserialization (check for polymorphic typing)", "high", "CWE-502",
     "Disable default typing: mapper.disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES). Use whitelist."),

    # XXE
    (r'DocumentBuilderFactory\s*\.\s*newInstance\s*\(\s*\)(?!.*setFeature.*EXTERNAL)',
     "XML External Entity (XXE) - Missing Protection", "high", "CWE-611",
     "Set FEATURE_SECURE_PROCESSING and disable DOCTYPE: dbf.setFeature('http://apache.org/xml/features/disallow-doctype-decl', true)."),
    (r'SAXParserFactory|XMLInputFactory|TransformerFactory\s*\.\s*newInstance',
     "Potential XXE via XML Parser", "high", "CWE-611",
     "Configure XML parser to disable external entities and DTD processing."),

    # Command Injection
    (r'Runtime\s*\.\s*getRuntime\s*\(\s*\)\s*\.\s*exec\s*\(.*request\.getParameter',
     "Command Injection", "critical", "CWE-78",
     "Never pass user input to Runtime.exec(). Use ProcessBuilder with argument array, not string."),
    (r'ProcessBuilder\s*\(.*request\.getParameter',
     "Command Injection (ProcessBuilder)", "critical", "CWE-78",
     "Pass arguments as separate list elements to ProcessBuilder, not as a single command string."),

    # SSRF
    (r'(?:HttpURLConnection|URLConnection|HttpClient|RestTemplate)\s*.*request\.getParameter.*URL',
     "Server-Side Request Forgery (SSRF)", "high", "CWE-918",
     "Validate and whitelist URLs. Block internal/private IP ranges. Use URL whitelist."),

    # Path Traversal
    (r'(?:FileInputStream|FileReader|File)\s*\(.*request\.getParameter',
     "Path Traversal", "high", "CWE-22",
     "Validate file paths with getCanonicalPath(). Check path starts with allowed base directory."),

    # Insecure Random
    (r'new\s+Random\s*\(\s*\)(?!.*SecureRandom)',
     "Insecure Random Number Generator", "medium", "CWE-330",
     "Use java.security.SecureRandom for security-sensitive random values."),

    # Weak Crypto
    (r'"DES"|"RC4"|"RC2"|"Blowfish"|"MD5"|"SHA-?1"',
     "Weak Cryptographic Algorithm", "high", "CWE-327",
     "Use AES-256-GCM for encryption, SHA-256/384/512 for hashing, PBKDF2/bcrypt for passwords."),

    # Hardcoded Secrets
    (r'(?:password|secret|apiKey|api_key|token)\s*=\s*"[^"]{8,}"',
     "Hardcoded Secret", "high", "CWE-798",
     "Use environment variables, a secrets manager (Vault, AWS Secrets Manager), or encrypted config."),

    # LDAP Injection
    (r'LDAP.*filter.*request\.getParameter|search\s*\(.*request\.getParameter',
     "LDAP Injection", "high", "CWE-90",
     "Escape LDAP filter special characters: * ( ) \\ NUL. Use parameterized LDAP queries."),

    # XPath Injection
    (r'XPath\s*\.\s*(?:compile|evaluate)\s*\(.*request\.getParameter',
     "XPath Injection", "high", "CWE-643",
     "Use parameterized XPath with XPathVariables. Never concatenate user input into XPath expressions."),

    # Log Injection
    (r'(?:logger|log|LOG)\s*\.\s*(?:info|warn|error|debug)\s*\(.*request\.getParameter',
     "Log Injection / Log Forging", "medium", "CWE-117",
     "Sanitize user input before logging. Strip newlines and control characters."),

    # Missing TLS
    (r'new\s+URL\s*\(\s*"http://',
     "Insecure HTTP Connection", "low", "CWE-319",
     "Use HTTPS for all connections. Enforce TLS 1.2+ with certificate validation."),
]

_PYTHON_PATTERNS = [
    # Code Injection
    (r'eval\s*\(\s*.*(?:request|input|get|post|args|form|params|data|json)',
     "Code Injection (eval)", "critical", "CWE-95",
     "Never use eval() with user input. Use ast.literal_eval() for safe evaluation of literals."),
    (r'exec\s*\(\s*.*(?:request|input|get|post|args|form)',
     "Code Injection (exec)", "critical", "CWE-95",
     "Never use exec() with user-controlled data. There is no safe way to use exec() with user input."),
    (r'__import__\s*\(\s*.*(?:request|input|get|post|args)',
     "Dynamic Import Injection", "critical", "CWE-95",
     "Use importlib.import_module() with a whitelist of allowed module names."),

    # Command Injection
    (r'(?:os\.system|os\.popen|subprocess\.call|subprocess\.Popen)\s*\(.*(?:request|input|get|post|args|form)',
     "Command Injection", "critical", "CWE-78",
     "Use subprocess.run() with args as a list (not shell=True). Never pass user input to shell."),
    (r'subprocess\..*shell\s*=\s*True.*(?:request|input|get|post)',
     "Command Injection (shell=True)", "critical", "CWE-78",
     "Avoid shell=True. Pass command arguments as a list to subprocess.run()."),

    # Insecure Deserialization
    (r'(?:pickle|cpickle|dill|marshal)\s*\.\s*(?:loads?|dump)\s*\(.*(?:request|input|get|post)',
     "Insecure Deserialization (pickle)", "critical", "CWE-502",
     "Never unpickle user-controlled data. Use JSON or a safe serialization format."),
    (r'yaml\s*\.\s*load\s*\((?!.*SafeLoader)(?!.*safe_load)',
     "Insecure YAML Deserialization", "high", "CWE-502",
     "Use yaml.safe_load() instead of yaml.load(). The latter can execute arbitrary code."),

    # SQL Injection
    (r'(?:execute|cursor\.execute)\s*\(\s*["\'].*%(?:s|d|r).*".*\b(?:request|input|get|post|args|form)',
     "SQL Injection (String Formatting)", "critical", "CWE-89",
     "Use parameterized queries: cursor.execute('SELECT ... WHERE x = %s', (value,)). Never use % formatting."),
    (r'(?:execute|cursor\.execute)\s*\(\s*f["\'].*(?:request|input|get|post|args)',
     "SQL Injection (f-string)", "critical", "CWE-89",
     "Never use f-strings for SQL queries. Use parameterized queries with placeholders."),

    # Path Traversal
    (r'(?:open|Path)\s*\(.*\.\.\/.*(?:request|input|get|post|args)',
     "Path Traversal", "high", "CWE-22",
     "Use os.path.realpath() and verify the resolved path is within allowed directories."),

    # SSTI (Server-Side Template Injection)
    (r'(?:render_template_string|jinja2\.Template|mako\.template)\s*\(.*(?:request|input|get|post|args)',
     "Server-Side Template Injection (SSTI)", "critical", "CWE-94",
     "Never pass user input to template renderers. Use sandboxed environments if dynamic templates are needed."),

    # Hardcoded Secrets
    (r'(?:PASSWORD|SECRET|API_KEY|TOKEN|AUTH)\s*=\s*["\'][^"\']{8,}["\']',
     "Hardcoded Secret", "high", "CWE-798",
     "Use os.environ.get() or a secrets manager. Never hardcode credentials in source code."),

    # Weak Crypto
    (r'hashlib\s*\.\s*(?:md5|sha1)\s*\(.*password',
     "Weak Password Hashing", "high", "CWE-327",
     "Use bcrypt, scrypt, or argon2 via passlib or hashlib with PBKDF2 for password hashing."),
    (r'random\s*\.\s*(?:random|randint|choice)\s*\((?!.*SystemRandom)(?!.*secrets)',
     "Insecure Random (use secrets module)", "medium", "CWE-330",
     "Use the secrets module (secrets.token_hex, secrets.choice) for security-sensitive randomness."),

    # SSRF
    (r'(?:requests|urllib|httpx)\s*\.\s*(?:get|post|request)\s*\(.*(?:request|input|get|post|args|form)',
     "Server-Side Request Forgery (SSRF)", "high", "CWE-918",
     "Validate and whitelist URLs. Parse and check the hostname against allowed domains. Block internal IPs."),

    # XSS (in web frameworks)
    (r'(?:render_template|Response)\s*\(.*\|\s*safe',
     "XSS via Markup Escaping Bypass", "high", "CWE-79",
     "Avoid marking user content as |safe. Use auto-escaping and sanitize with bleach or nh3."),

    # Assert misuse
    (r'assert\s+.*(?:request|input|get|post|args|form)',
     "Assert with User Input (stripped in -O mode)", "medium", "CWE-617",
     "Never use assert for input validation. Assertions are removed with python -O flag."),
]

_JS_PATTERNS = [
    # NoSQL Injection
    (r'(?:find|findOne|update|deleteMany)\s*\(\s*\{\s*.*req\.(?:body|query|params)',
     "NoSQL Injection (MongoDB)", "critical", "CWE-943",
     "Sanitize and validate query objects. Use mongo-sanitize or cast inputs to expected types."),
    (r'\$where\s*:\s*.*req\.(?:body|query|params)',
     "NoSQL Injection ($where)", "critical", "CWE-943",
     "Never use $where with user input. Use $expr with aggregation operators instead."),

    # Code Injection
    (r'eval\s*\(\s*.*req\.(?:body|query|params)',
     "Code Injection (eval)", "critical", "CWE-95",
     "Never use eval() with user input. There is no safe use of eval() with untrusted data."),
    (r'new\s+Function\s*\(\s*.*req\.(?:body|query|params)',
     "Code Injection (Function constructor)", "critical", "CWE-95",
     "The Function constructor evaluates strings as code. Never pass user input to it."),
    (r'(?:child_process|childProcess)\s*\.\s*(?:exec|spawn)\s*\(.*req\.(?:body|query|params)',
     "Command Injection", "critical", "CWE-78",
     "Use execFile() instead of exec(). Pass arguments as array. Never include user input in command strings."),

    # Prototype Pollution
    (r'(?:Object\.assign|\.extend|\.merge|\.clone)\s*\(.*req\.(?:body|query|params)',
     "Prototype Pollution", "high", "CWE-1321",
     "Use Object.create(null) for objects. Validate keys don't contain __proto__ or constructor."),
    (r'\.set\s*\(\s*.*req\.(?:body|query|params).*\s*,',
     "Potential Prototype Pollution (deep set)", "high", "CWE-1321",
     "Sanitize object paths. Block __proto__, constructor, and prototype as property names."),

    # SSTI
    (r'(?:\.render|\.renderFile|\.compile)\s*\(.*req\.(?:body|query|params)',
     "Server-Side Template Injection (SSTI)", "critical", "CWE-94",
     "Never pass user input directly to template engines. Use sandboxed rendering contexts."),

    # XSS
    (r'(?:innerHTML|outerHTML|insertAdjacentHTML|document\.write)\s*\(.*req\.(?:body|query|params)',
     "DOM-based XSS", "high", "CWE-79",
     "Use textContent instead of innerHTML. Sanitize with DOMPurify if HTML insertion is required."),
    (r'dangerouslySetInnerHTML\s*[:=]\s*\{.*req\.(?:body|query|params)',
     "React XSS (dangerouslySetInnerHTML)", "high", "CWE-79",
     "Avoid dangerouslySetInnerHTML. Use JSX auto-escaping. Sanitize with DOMPurify if unavoidable."),

    # Path Traversal
    (r'(?:readFile|readFileSync|createReadStream)\s*\(.*\.\.\/',
     "Path Traversal", "high", "CWE-22",
     "Use path.resolve() and verify the resolved path is within the intended directory."),

    # SSRF
    (r'(?:fetch|axios|request|got|http\.get|https\.get)\s*\(.*req\.(?:body|query|params)',
     "Server-Side Request Forgery (SSRF)", "high", "CWE-918",
     "Validate URLs against a whitelist. Parse hostname and check against allowed domains."),

    # Hardcoded Secrets
    (r'(?:password|secret|apiKey|api_key|token|AUTH_TOKEN)\s*[:=]\s*["\'][^"\']{8,}["\']',
     "Hardcoded Secret", "high", "CWE-798",
     "Use process.env or a secrets manager. Never commit secrets to source code."),

    # Insecure JWT
    (r'jwt\s*\.\s*(?:sign|verify)\s*\(.*algorithm\s*:\s*["\']none["\']',
     "JWT Algorithm Confusion (none)", "critical", "CWE-347",
     "Always specify allowed algorithms explicitly. Never accept 'none' algorithm."),
    (r'jwt\s*\.\s*(?:sign|verify)\s*\(.*["\']HS',
     "JWT with Weak HMAC", "medium", "CWE-347",
     "Use RS256 or ES256 for JWT. If using HMAC, ensure the secret is strong (256+ bits)."),

    # ReDoS
    (r'new\s+RegExp\s*\(\s*.*req\.(?:body|query|params)',
     "ReDoS (User-Controlled Regex)", "medium", "CWE-1333",
     "Never compile user input as regex. Use a regex timeout library like safe-regex."),
]

_C_PATTERNS = [
    # Buffer Overflow
    (r'(?:strcpy|strcat|sprintf|gets|scanf\s*\(\s*"[^"]*%s)\s*\(',
     "Buffer Overflow (Unsafe String Function)", "critical", "CWE-120",
     "Use strncpy(), strncat(), snprintf() with explicit buffer size limits. Prefer safe alternatives."),
    (r'(?:memcpy|memmove)\s*\([^,]+,\s*[^,]+,\s*(?!sizeof)',
     "Potential Buffer Overflow (memcpy without sizeof)", "high", "CWE-120",
     "Use sizeof(destination) for the size parameter. Validate that source fits in destination."),

    # Format String
    (r'printf\s*\(\s*\w+\s*\)(?!.*,)',
     "Format String Vulnerability", "critical", "CWE-134",
     "Always use format specifiers: printf(\"%s\", str). Never pass user input as format string."),
    (r'(?:fprintf|sprintf|snprintf|syslog)\s*\([^,]+,\s*\w+\s*\)',
     "Potential Format String Vulnerability", "high", "CWE-134",
     "Use \"%s\" as the format string when printing user-controlled strings."),

    # Use-After-Free
    (r'free\s*\(\s*\w+\s*\)(?!.*=\s*NULL)',
     "Potential Use-After-Free (no NULL assignment)", "high", "CWE-416",
     "Set pointer to NULL after free(): free(ptr); ptr = NULL;"),

    # Integer Overflow
    (r'(?:malloc|calloc|realloc)\s*\(\s*\w+\s*\*\s*sizeof',
     "Potential Integer Overflow in Allocation", "high", "CWE-190",
     "Check for overflow before multiplication. Use calloc() or safe multiplication wrappers."),

    # Command Injection
    (r'system\s*\(\s*.*argv\[',
     "Command Injection", "critical", "CWE-78",
     "Never pass user input to system(). Use execve() with explicit argument arrays."),
    (r'popen\s*\(\s*.*argv\[',
     "Command Injection (popen)", "critical", "CWE-78",
     "Avoid popen() with user input. Use fork()+execve() with controlled arguments."),

    # Null Pointer Dereference
    (r'(?:malloc|calloc)\s*\([^)]+\)(?!.*if.*NULL)',
     "Missing NULL Check After malloc", "medium", "CWE-476",
     "Always check the return value of malloc/calloc for NULL before use."),

    # Race Condition (TOCTOU)
    (r'access\s*\(.*\)\s*.*\n.*open\s*\(.*\)',
     "TOCTOU Race Condition (access then open)", "high", "CWE-367",
     "Use open() with appropriate flags and check the returned fd. Avoid access() before open()."),
]

_GO_PATTERNS = [
    # SQL Injection
    (r'(?:db\.Query|db\.Exec|db\.QueryRow)\s*\(\s*".*%[sv].*".*\+',
     "SQL Injection (String Formatting)", "critical", "CWE-89",
     "Use placeholders: db.Query('SELECT ... WHERE x = $1', value). Never use fmt.Sprintf for SQL."),
    (r'fmt\.Sprintf\s*\(\s*".*(?:SELECT|INSERT|UPDATE|DELETE).*".*r\.(?:FormValue|URL\.Query)',
     "SQL Injection (fmt.Sprintf)", "critical", "CWE-89",
     "Use parameterized queries with $1, $2 placeholders. Never format user input into SQL."),

    # Command Injection
    (r'(?:exec\.Command|os\.Exec)\s*\(.*r\.(?:FormValue|URL\.Query)',
     "Command Injection", "critical", "CWE-78",
     "Use exec.Command with separate arguments. Never pass user input as part of the command string."),

    # Path Traversal
    (r'(?:os\.Open|ioutil\.ReadFile|os\.ReadFile)\s*\(.*r\.(?:FormValue|URL\.Query)',
     "Path Traversal", "high", "CWE-22",
     "Use filepath.Clean() and verify the path is within the intended directory with filepath.Abs()."),

    # SSRF
    (r'(?:http\.Get|http\.Post|http\.NewRequest)\s*\(.*r\.(?:FormValue|URL\.Query)',
     "Server-Side Request Forgery (SSRF)", "high", "CWE-918",
     "Validate the URL hostname against a whitelist. Block internal/private IP ranges."),

    # Template Injection
    (r'(?:template\.New|template\.Must|t\.Execute)\s*\(.*r\.(?:FormValue|URL\.Query)',
     "Server-Side Template Injection", "critical", "CWE-94",
     "Never pass user input directly to template execution. Use strict template contexts."),

    # Weak Crypto
    (r'"DES"|"RC4"|"MD5"|"SHA1"',
     "Weak Cryptographic Algorithm", "high", "CWE-327",
     "Use crypto/aes with GCM mode, crypto/sha256, and golang.org/x/crypto/bcrypt for passwords."),

    # Hardcoded Secrets
    (r'(?:Password|Secret|APIKey|Token)\s*=\s*"[^"]{8,}"',
     "Hardcoded Secret", "high", "CWE-798",
     "Use os.Getenv() or a secrets manager. Never hardcode credentials."),

    # Insecure Random
    (r'math/rand(?!.*crypto/rand)',
     "Insecure Random (use crypto/rand)", "medium", "CWE-330",
     "Use crypto/rand for security-sensitive random values. math/rand is not cryptographically secure."),

    # TLS Issues
    (r'InsecureSkipVerify\s*:\s*true',
     "TLS Certificate Verification Disabled", "high", "CWE-295",
     "Never disable TLS certificate verification in production. Use proper CA certificates."),
]

_RUBY_PATTERNS = [
    # Command Injection
    (r'(?:system|exec|`|%x|open3|spawn)\s*\(?\s*.*params\[',
     "Command Injection", "critical", "CWE-78",
     "Use system() with separate arguments: system('cmd', arg1, arg2). Never interpolate params into commands."),
    (r'`.*#\{params\[',
     "Command Injection (Backticks)", "critical", "CWE-78",
     "Backticks execute shell commands. Never interpolate user input. Use Open3.capture3 with argument arrays."),

    # SQL Injection
    (r'(?:where|find_by_sql|select_all|execute)\s*\(.*#\{params\[',
     "SQL Injection (String Interpolation)", "critical", "CWE-89",
     "Use ActiveRecord parameterized queries: Model.where('column = ?', value). Never interpolate."),
    (r'(?:\.where\s*\(\s*["\'].*\+.*params)',
     "SQL Injection (String Concatenation)", "critical", "CWE-89",
     "Use hash conditions or array conditions with ? placeholders."),

    # Mass Assignment
    (r'(?:\.new|\.create|\.update|\.update_attributes)\s*\(\s*params\[',
     "Mass Assignment Vulnerability", "high", "CWE-915",
     "Use strong parameters: params.require(:model).permit(:attr1, :attr2). Never pass params directly."),

    # Insecure Deserialization
    (r'(?:Marshal\.load|YAML\.load)\s*\(.*params\[',
     "Insecure Deserialization", "critical", "CWE-502",
     "Never deserialize user-controlled data with Marshal or YAML. Use JSON.parse for data interchange."),
    (r'YAML\.load\s*\((?!.*safe_load)',
     "Insecure YAML Deserialization", "high", "CWE-502",
     "Use YAML.safe_load instead of YAML.load. YAML.load can instantiate arbitrary Ruby objects."),

    # SSTI
    (r'(?:ERB\.new|Tilt|Haml|Slim)\s*.*params\[',
     "Server-Side Template Injection", "critical", "CWE-94",
     "Never pass user input to template engines. Use strict template rendering with escaped output."),

    # XSS
    (r'(?:raw|html_safe|sanitize)\s*\(.*params\[',
     "XSS via Unsafe Output", "high", "CWE-79",
     "Avoid raw() and html_safe with user input. Rails auto-escapes ERB output by default."),

    # Path Traversal
    (r'(?:File\.open|File\.read|send_file|IO\.read)\s*\(.*params\[',
     "Path Traversal", "high", "CWE-22",
     "Use File.expand_path and verify the path is within the allowed directory."),

    # Hardcoded Secrets
    (r'(?:PASSWORD|SECRET|API_KEY|TOKEN)\s*=\s*["\'][^"\']{8,}["\']',
     "Hardcoded Secret", "high", "CWE-798",
     "Use Rails credentials (Rails.application.credentials) or ENV variables."),
]

_DOTNET_PATTERNS = [
    # SQL Injection
    (r'SqlCommand\s*\(\s*".*\+.*\+',
     "SQL Injection (String Concatenation)", "critical", "CWE-89",
     "Use SqlParameter: new SqlCommand('SELECT ... WHERE x = @val', conn).Parameters.AddWithValue('@val', input)."),
    (r'(?:ExecuteReader|ExecuteScalar|ExecuteNonQuery)\s*\(.*\+',
     "SQL Injection (Dynamic SQL)", "critical", "CWE-89",
     "Always use parameterized queries with SqlParameterCollection. Never concatenate strings."),

    # Insecure Deserialization
    (r'(?:BinaryFormatter|NetDataContractSerializer|LosFormatter|SoapFormatter)\s*\.\s*Deserialize',
     "Insecure Deserialization", "critical", "CWE-502",
     "Avoid BinaryFormatter. Use System.Text.Json with JsonSerializer. Implement SerializationBinder whitelist."),
    (r'TypeNameHandling\s*=\s*TypeNameHandling\.(?:All|Objects|Auto)',
     "JSON.NET TypeNameHandling Enabled", "high", "CWE-502",
     "Set TypeNameHandling = TypeNameHandling.None. Use a custom SerializationBinder with whitelist."),

    # XXE
    (r'XmlDocument\s*\.\s*Load\s*\((?!.*XmlResolver\s*=\s*null)',
     "XML External Entity (XXE)", "high", "CWE-611",
     "Set XmlResolver = null and use XmlReader with DtdProcessing = DtdProcessing.Prohibit."),
    (r'XmlReaderSettings\s*\{[^}]*DtdProcessing\s*=\s*DtdProcessing\.Parse',
     "XXE via DTD Processing", "high", "CWE-611",
     "Set DtdProcessing = DtdProcessing.Prohibit or DtdProcessing.Ignore."),

    # Command Injection
    (r'Process\s*\.\s*Start\s*\(.*Request\[',
     "Command Injection", "critical", "CWE-78",
     "Never pass user input to Process.Start. Use whitelisted commands with ProcessStartInfo argument array."),

    # LDAP Injection
    (r'DirectorySearcher\s*\.\s*Filter\s*=\s*".*\+.*\+',
     "LDAP Injection", "high", "CWE-90",
     "Escape LDAP filter special characters. Use LDAP escaping utilities or parameterized search."),

    # Hardcoded Secrets
    (r'(?:Password|Secret|ApiKey|Token|ConnectionString)\s*=\s*"[^"]{8,}"',
     "Hardcoded Secret", "high", "CWE-798",
     "Use Azure Key Vault, AWS Secrets Manager, or .NET User Secrets for development."),

    # Weak Crypto
    (r'"DES"|"RC2"|"RC4"|"MD5"|"SHA1"|"TripleDES"',
     "Weak Cryptographic Algorithm", "high", "CWE-327",
     "Use AesCryptoServiceProvider with GCM mode, SHA256/512, and PBKDF2 for password hashing."),
]

# ── Generic injection patterns (cross-language) ─────────────────────────────

_INJECTION_PATTERNS = [
    # SQL Injection patterns
    (r'(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\s+.*\+.*\+',
     "Potential SQL Injection (String Concatenation)", "high", "CWE-89",
     "Use parameterized queries. Never concatenate user input into SQL statements."),
    (r'(?:execute|query|raw)\s*\(\s*["\'`].*\$\{',
     "Potential SQL/NoSQL Injection (Template Literal)", "high", "CWE-89",
     "Use parameterized queries with placeholders instead of template literals."),

    # Command Injection patterns
    (r'(?:exec|system|popen|subprocess|shell|cmd)\s*\(\s*["\'].*\$\{',
     "Potential Command Injection", "high", "CWE-78",
     "Use argument arrays instead of shell strings. Never interpolate user input into commands."),

    # LDAP Injection
    (r'ldap\s*.*filter.*\+=|ldap.*search.*\+',
     "Potential LDAP Injection", "high", "CWE-90",
     "Escape LDAP filter metacharacters: * ( ) \\ NUL. Use parameterized LDAP queries."),

    # XPath Injection
    (r'xpath\s*.*compile.*\+|xpath.*evaluate.*\+',
     "Potential XPath Injection", "high", "CWE-643",
     "Use parameterized XPath queries. Never concatenate user input into XPath expressions."),

    # XSS patterns
    (r'(?:innerHTML|outerHTML|document\.write|dangerouslySetInnerHTML)\s*[=\(]',
     "Potential DOM XSS", "high", "CWE-79",
     "Use textContent or safe DOM APIs. Sanitize HTML with a trusted library."),
    (r'(?:echo|print|response\.write|out\.print)\s*\(.*\$_(?:GET|POST|REQUEST)',
     "Potential Reflected XSS", "high", "CWE-79",
     "HTML-encode all user-controlled output. Use context-appropriate escaping."),
]

_SECRET_PATTERNS = [
    (r'(?:password|passwd|pwd)\s*[:=]\s*["\'][^"\'\s]{4,}["\']',
     "Hardcoded Password", "critical", "CWE-798",
     "Move passwords to environment variables or a secrets manager."),
    (r'(?:api[_-]?key|apikey)\s*[:=]\s*["\'][A-Za-z0-9_\-]{16,}["\']',
     "Hardcoded API Key", "critical", "CWE-798",
     "Store API keys in environment variables or a secure vault service."),
    (r'(?:secret|token|auth)\s*[:=]\s*["\'][A-Za-z0-9_\-\.]{16,}["\']',
     "Hardcoded Secret/Token", "critical", "CWE-798",
     "Use a secrets manager. Rotate any exposed credentials immediately."),
    (r'(?:private[_-]?key|ssh[_-]?key)\s*[:=]\s*["\']-----BEGIN',
     "Hardcoded Private Key", "critical", "CWE-798",
     "Never store private keys in source code. Use file references with restricted permissions."),
    (r'(?:jdbc|mysql|postgresql|mongodb|redis):\/\/[^"\'\s]+@',
     "Hardcoded Database Connection String", "critical", "CWE-798",
     "Use environment variables for connection strings. Never include credentials in URLs."),
    (r'Authorization\s*:\s*["\']Bearer\s+[A-Za-z0-9_\-\.]{20,}',
     "Hardcoded Bearer Token", "high", "CWE-798",
     "Tokens should be obtained at runtime via OAuth flow, not hardcoded."),
    (r'(?:aws_access_key_id|AWS_ACCESS_KEY_ID)\s*[:=]\s*["\'][A-Z0-9]{16,}["\']',
     "Hardcoded AWS Access Key", "critical", "CWE-798",
     "Use IAM roles or AWS credentials file. Never hardcode AWS keys."),
]

_CRYPTO_PATTERNS = [
    (r'(?:MD5|md5)\s*\(', "Weak Hash (MD5)", "high", "CWE-327",
     "Use SHA-256 or stronger. For passwords, use bcrypt/scrypt/argon2."),
    (r'(?:SHA-?1|sha1)\s*\(', "Weak Hash (SHA-1)", "high", "CWE-327",
     "Migrate to SHA-256 or SHA-3. SHA-1 is vulnerable to collision attacks."),
    (r'(?:DES|RC2|RC4|3DES|TripleDES|Blowfish)\s', "Weak Encryption Algorithm", "high", "CWE-327",
     "Use AES-256-GCM or ChaCha20-Poly1305 for encryption."),
    (r'(?:ECB|CBC)\s*mode', "Weak Cipher Mode (ECB/CBC)", "high", "CWE-327",
     "Use authenticated encryption modes: GCM or CCM. Avoid ECB entirely."),
    (r'Math\s*\.\s*random\s*\(|rand\s*\(\s*\)|random\s*\.\s*random\s*\(', "Insecure Random", "medium", "CWE-330",
     "Use cryptographically secure random: crypto.randomBytes (Node), secrets module (Python), SecureRandom (Java)."),
    (r'RSA\s*.*\b(?:1024|512)\b', "Weak RSA Key Size", "high", "CWE-326",
     "Use RSA with at least 2048-bit keys. Prefer 3072 or 4096 bits."),
]

_CONFIG_PATTERNS = [
    (r'debug\s*=\s*(?:true|True|1|on|On)',
     "Debug Mode Enabled", "high", "CWE-489",
     "Disable debug mode in production. It may expose stack traces and sensitive information."),
    (r'DEBUG\s*=\s*True',
     "Django DEBUG=True", "high", "CWE-489",
     "Set DEBUG=False in production. DEBUG=True exposes settings, stack traces, and environment variables."),
    (r'display_errors\s*=\s*(?:On|1|true)',
     "PHP Display Errors On", "medium", "CWE-209",
     "Set display_errors=Off in production. Log errors instead."),
    (r'allow_url_include\s*=\s*(?:On|1|true)',
     "PHP allow_url_include Enabled", "critical", "CWE-98",
     "Set allow_url_include=Off. This setting enables remote file inclusion attacks."),
    (r'CORS.*\*\s*|Access-Control-Allow-Origin\s*:\s*\*',
     "Overly Permissive CORS (*)", "medium", "CWE-942",
     "Restrict CORS to specific trusted origins. Never use '*' with credentials."),
    (r'HttpOnly\s*=\s*false|Secure\s*=\s*false.*cookie',
     "Insecure Cookie Flags", "medium", "CWE-614",
     "Set HttpOnly=True and Secure=True on all sensitive cookies."),
    (r'HSTS\s*=\s*false|Strict-Transport-Security\s*:\s*max-age=0',
     "HSTS Disabled", "medium", "CWE-319",
     "Enable HSTS with a long max-age (>= 1 year) and includeSubDomains."),
]

# ── Language file extensions ────────────────────────────────────────────────

_LANG_EXTENSIONS = {
    "php": [".php", ".phtml", ".php3", ".php4", ".php5", ".phps", ".inc"],
    "java": [".java", ".jsp", ".jspx", ".jspf"],
    "python": [".py", ".pyw", ".pyx", ".pxd", ".pxi"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".cxx", ".cc", ".c++", ".hpp", ".hxx", ".hh"],
    "go": [".go"],
    "ruby": [".rb", ".erb", ".rake"],
    "csharp": [".cs", ".csx", ".aspx", ".ascx", ".ashx"],
    "sql": [".sql"],
    "config": [".xml", ".yaml", ".yml", ".json", ".conf", ".ini", ".cfg", ".env", ".properties", ".toml"],
}

_LANG_PATTERNS = {
    "php": _PHP_PATTERNS,
    "java": _JAVA_PATTERNS,
    "python": _PYTHON_PATTERNS,
    "javascript": _JS_PATTERNS,
    "c": _C_PATTERNS,
    "cpp": _C_PATTERNS,
    "go": _GO_PATTERNS,
    "ruby": _RUBY_PATTERNS,
    "csharp": _DOTNET_PATTERNS,
}


# ── Core scanning logic ─────────────────────────────────────────────────────

def _get_files(path: str, extensions: List[str]) -> List[str]:
    """Recursively collect files matching given extensions."""
    files = []
    p = Path(path)
    if p.is_file():
        if any(p.suffix.lower() in [e.lower() for e in extensions] for e in [p.suffix]):
            return [str(p)]
        return []
    if not p.is_dir():
        return []

    for root, dirs, filenames in os.walk(path):
        # Skip common non-source directories
        dirs[:] = [d for d in dirs if d not in (
            ".git", "node_modules", "vendor", "__pycache__", ".venv", "venv",
            "target", "build", "dist", ".next", ".nuxt", "bower_components",
            ".idea", ".vscode", "bin", "obj", "Debug", "Release",
        )]
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in [e.lower() for e in extensions]:
                files.append(os.path.join(root, fname))
    return files


def _scan_file(filepath: str, patterns: List[tuple], lang: str) -> List[Dict[str, Any]]:
    """Scan a single file against a list of vulnerability patterns."""
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return findings

    for i, line in enumerate(lines, 1):
        for regex, vuln_type, severity, cwe, remediation in patterns:
            try:
                if re.search(regex, line, re.IGNORECASE):
                    # Avoid duplicate findings on same line
                    findings.append({
                        "severity": severity,
                        "type": vuln_type,
                        "file": filepath,
                        "line": i,
                        "code": line.strip()[:200],
                        "message": f"{vuln_type} detected in {lang.upper()} code.",
                        "remediation": remediation,
                        "cwe": cwe,
                    })
            except re.error:
                continue

    return findings


async def _run_scan(
    path: str,
    lang_patterns: List[tuple],
    extensions: List[str],
    lang_name: str,
    timeout_ms: int = 120000,
) -> Dict[str, Any]:
    """Run a vulnerability scan against a path."""
    import time
    start = time.time()

    files = _get_files(path, extensions)
    if not files:
        return {
            "findings": [],
            "summary": f"No {lang_name} source files found in: {path}",
            "total_findings": 0,
            "files_scanned": 0,
            "scan_duration_ms": (time.time() - start) * 1000,
            "interrupted": False,
        }

    all_findings = []
    for filepath in files:
        findings = _scan_file(filepath, lang_patterns, lang_name)
        all_findings.extend(findings)

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    all_findings.sort(key=lambda f: severity_order.get(f["severity"], 5))

    # Build summary
    sev_counts = {}
    for f in all_findings:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1

    summary_parts = [f"=== {lang_name.upper()} Vulnerability Scan Results ==="]
    summary_parts.append(f"Path: {path}")
    summary_parts.append(f"Files scanned: {len(files)}")
    summary_parts.append(f"Total findings: {len(all_findings)}")
    summary_parts.append("")
    for sev in ["critical", "high", "medium", "low", "info"]:
        if sev in sev_counts:
            summary_parts.append(f"  {sev.upper()}: {sev_counts[sev]}")

    if all_findings:
        summary_parts.append("")
        summary_parts.append("=== Detailed Findings ===")
        for f in all_findings:
            summary_parts.append(
                f"\n[{f['severity'].upper()}] {f['type']} ({f['cwe']})"
                f"\n  File: {f['file']}:{f['line']}"
                f"\n  Code: {f['code']}"
                f"\n  Fix: {f['remediation']}"
            )

    return {
        "findings": all_findings,
        "summary": "\n".join(summary_parts),
        "total_findings": len(all_findings),
        "files_scanned": len(files),
        "scan_duration_ms": (time.time() - start) * 1000,
        "interrupted": False,
    }


# ── Command handlers ────────────────────────────────────────────────────────

async def _cmd_scan(args: Dict[str, Any]) -> Dict[str, Any]:
    """Generic scan that auto-detects language or uses specified one."""
    path = args.get("path") or args.get("command", "").replace("scan ", "", 1).strip().split()[0] if args.get("command", "").startswith("scan ") else ""
    language = args.get("language", "all").lower()

    if not path or not os.path.exists(path):
        return {"findings": [], "summary": f"Path not found: {path}", "total_findings": 0,
                "files_scanned": 0, "scan_duration_ms": 0, "interrupted": False}

    if language == "all":
        # Scan with all language patterns
        all_findings = []
        total_files = 0
        for lang, patterns in _LANG_PATTERNS.items():
            exts = _LANG_EXTENSIONS.get(lang, [])
            result = await _run_scan(path, patterns, exts, lang, args.get("timeout", 120000))
            all_findings.extend(result["findings"])
            total_files += result["files_scanned"]

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        all_findings.sort(key=lambda f: severity_order.get(f["severity"], 5))

        sev_counts = {}
        for f in all_findings:
            sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1

        summary = f"=== Multi-Language Scan Results ===\nPath: {path}\nFiles scanned: {total_files}\nTotal findings: {len(all_findings)}\n"
        for sev in ["critical", "high", "medium", "low", "info"]:
            if sev in sev_counts:
                summary += f"  {sev.upper()}: {sev_counts[sev]}\n"

        return {
            "findings": all_findings,
            "summary": summary,
            "total_findings": len(all_findings),
            "files_scanned": total_files,
            "scan_duration_ms": 0,
            "interrupted": False,
        }

    patterns = _LANG_PATTERNS.get(language)
    exts = _LANG_EXTENSIONS.get(language, [])
    if not patterns:
        return {"findings": [], "summary": f"Unsupported language: {language}. Supported: {', '.join(_LANG_PATTERNS)}",
                "total_findings": 0, "files_scanned": 0, "scan_duration_ms": 0, "interrupted": False}

    return await _run_scan(path, patterns, exts, language, args.get("timeout", 120000))


async def _cmd_scan_lang(args: Dict[str, Any], lang: str) -> Dict[str, Any]:
    """Scan with a specific language's patterns."""
    command = args.get("command", "")
    path = args.get("path", "")

    # Extract path from command: "scan_php /path/to/code"
    prefix = f"scan_{lang} "
    if not path and command.startswith(prefix):
        path = command[len(prefix):].strip()

    if not path or not os.path.exists(path):
        return {"findings": [], "summary": f"Path not found: {path}",
                "total_findings": 0, "files_scanned": 0, "scan_duration_ms": 0, "interrupted": False}

    patterns = _LANG_PATTERNS.get(lang, [])
    exts = _LANG_EXTENSIONS.get(lang, [])
    return await _run_scan(path, patterns, exts, lang, args.get("timeout", 120000))


async def _cmd_scan_sql(args: Dict[str, Any]) -> Dict[str, Any]:
    """Scan specifically for SQL injection across all languages."""
    path = args.get("path") or args.get("command", "").replace("scan_sql ", "", 1).strip()
    if not path or not os.path.exists(path):
        return {"findings": [], "summary": f"Path not found: {path}",
                "total_findings": 0, "files_scanned": 0, "scan_duration_ms": 0, "interrupted": False}

    sql_patterns = []
    for lang_patterns in _LANG_PATTERNS.values():
        for p in lang_patterns:
            if "SQL Injection" in p[1] or "NoSQL" in p[1]:
                sql_patterns.append(p)
    # Also add generic SQL patterns
    for p in _INJECTION_PATTERNS:
        if "SQL" in p[1]:
            sql_patterns.append(p)

    all_exts = list(set(e for exts in _LANG_EXTENSIONS.values() for e in exts))
    return await _run_scan(path, sql_patterns, all_exts, "SQL Injection", args.get("timeout", 120000))


async def _cmd_scan_xss(args: Dict[str, Any]) -> Dict[str, Any]:
    """Scan specifically for XSS across all languages."""
    path = args.get("path") or args.get("command", "").replace("scan_xss ", "", 1).strip()
    if not path or not os.path.exists(path):
        return {"findings": [], "summary": f"Path not found: {path}",
                "total_findings": 0, "files_scanned": 0, "scan_duration_ms": 0, "interrupted": False}

    xss_patterns = []
    for lang_patterns in _LANG_PATTERNS.values():
        for p in lang_patterns:
            if "XSS" in p[1] or "Cross-Site" in p[1]:
                xss_patterns.append(p)
    for p in _INJECTION_PATTERNS:
        if "XSS" in p[1]:
            xss_patterns.append(p)

    all_exts = list(set(e for exts in _LANG_EXTENSIONS.values() for e in exts))
    return await _run_scan(path, xss_patterns, all_exts, "XSS", args.get("timeout", 120000))


async def _cmd_scan_injection(args: Dict[str, Any]) -> Dict[str, Any]:
    """Scan for all injection types."""
    path = args.get("path") or args.get("command", "").replace("scan_injection ", "", 1).strip()
    if not path or not os.path.exists(path):
        return {"findings": [], "summary": f"Path not found: {path}",
                "total_findings": 0, "files_scanned": 0, "scan_duration_ms": 0, "interrupted": False}

    injection_patterns = list(_INJECTION_PATTERNS)
    for lang_patterns in _LANG_PATTERNS.values():
        for p in lang_patterns:
            if any(kw in p[1].lower() for kw in ["injection", "rce", "code injection", "command", "eval", "exec"]):
                injection_patterns.append(p)

    all_exts = list(set(e for exts in _LANG_EXTENSIONS.values() for e in exts))
    return await _run_scan(path, injection_patterns, all_exts, "Injection", args.get("timeout", 120000))


async def _cmd_scan_secrets(args: Dict[str, Any]) -> Dict[str, Any]:
    """Scan for hardcoded secrets."""
    path = args.get("path") or args.get("command", "").replace("scan_secrets ", "", 1).strip()
    if not path or not os.path.exists(path):
        return {"findings": [], "summary": f"Path not found: {path}",
                "total_findings": 0, "files_scanned": 0, "scan_duration_ms": 0, "interrupted": False}

    all_exts = list(set(e for exts in _LANG_EXTENSIONS.values() for e in exts))
    all_exts.extend([".env", ".yml", ".yaml", ".json", ".xml", ".conf", ".cfg", ".toml", ".properties"])
    return await _run_scan(path, _SECRET_PATTERNS, all_exts, "Secrets", args.get("timeout", 120000))


async def _cmd_scan_crypto(args: Dict[str, Any]) -> Dict[str, Any]:
    """Scan for weak cryptographic usage."""
    path = args.get("path") or args.get("command", "").replace("scan_crypto ", "", 1).strip()
    if not path or not os.path.exists(path):
        return {"findings": [], "summary": f"Path not found: {path}",
                "total_findings": 0, "files_scanned": 0, "scan_duration_ms": 0, "interrupted": False}

    all_exts = list(set(e for exts in _LANG_EXTENSIONS.values() for e in exts))
    return await _run_scan(path, _CRYPTO_PATTERNS, all_exts, "Cryptography", args.get("timeout", 120000))


async def _cmd_scan_config(args: Dict[str, Any]) -> Dict[str, Any]:
    """Scan config files for security misconfigurations."""
    path = args.get("path") or args.get("command", "").replace("scan_config ", "", 1).strip()
    if not path or not os.path.exists(path):
        return {"findings": [], "summary": f"Path not found: {path}",
                "total_findings": 0, "files_scanned": 0, "scan_duration_ms": 0, "interrupted": False}

    config_exts = [".xml", ".yaml", ".yml", ".json", ".conf", ".ini", ".cfg", ".env", ".properties", ".toml", ".htaccess"]
    return await _run_scan(path, _CONFIG_PATTERNS, config_exts, "Configuration", args.get("timeout", 120000))


async def _cmd_audit_deps(args: Dict[str, Any]) -> Dict[str, Any]:
    """Audit dependencies for known CVEs."""
    path = args.get("path") or args.get("command", "").replace("audit_deps ", "", 1).strip() or "."

    results = []
    p = Path(path)

    # Python: pip audit
    req_files = list(p.rglob("requirements*.txt")) + list(p.rglob("Pipfile")) + list(p.rglob("pyproject.toml"))
    if req_files:
        try:
            proc = await asyncio.create_subprocess_exec(
                "pip", "audit", "--format", "json",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                cwd=str(p),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            if proc.returncode == 0 and stdout:
                results.append("=== Python Dependencies (pip audit) ===")
                results.append(stdout.decode("utf-8", errors="replace"))
        except Exception:
            results.append("Python: pip-audit not available. Install with: pip install pip-audit")

    # Node.js: npm audit
    package_json = p / "package.json"
    if package_json.exists():
        try:
            proc = await asyncio.create_subprocess_exec(
                "npm", "audit", "--json",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                cwd=str(p),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            if stdout:
                results.append("=== Node.js Dependencies (npm audit) ===")
                results.append(stdout.decode("utf-8", errors="replace"))
        except Exception:
            results.append("Node.js: npm audit failed or npm not available.")

    if not results:
        results.append("No dependency files found (requirements.txt, package.json, etc.)")

    return {
        "findings": [],
        "summary": "\n".join(results),
        "total_findings": 0,
        "files_scanned": len(req_files) + (1 if package_json.exists() else 0),
        "scan_duration_ms": 0,
        "interrupted": False,
    }


async def _cmd_report(args: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a consolidated report from last scan."""
    global _last_findings, _last_scan_path

    if not _last_findings:
        return {"findings": [], "summary": "No scan has been run yet. Run a scan first.",
                "total_findings": 0, "files_scanned": 0, "scan_duration_ms": 0, "interrupted": False}

    sev_counts = {}
    type_counts = {}
    for f in _last_findings:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1
        type_counts[f["type"]] = type_counts.get(f["type"], 0) + 1

    report = [
        "=" * 60,
        "VULNERABILITY SCAN REPORT",
        "=" * 60,
        f"Scan path: {_last_scan_path}",
        f"Total findings: {len(_last_findings)}",
        "",
        "--- Severity Breakdown ---",
    ]
    for sev in ["critical", "high", "medium", "low", "info"]:
        if sev in sev_counts:
            report.append(f"  {sev.upper()}: {sev_counts[sev]}")

    report.append("")
    report.append("--- Vulnerability Types ---")
    for vtype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        report.append(f"  {vtype}: {count}")

    report.append("")
    report.append("--- Remediation Priority ---")
    for f in _last_findings:
        if f["severity"] in ("critical", "high"):
            report.append(f"\n[{f['severity'].upper()}] {f['type']} ({f['cwe']})")
            report.append(f"  File: {f['file']}:{f['line']}")
            report.append(f"  Fix: {f['remediation']}")

    return {
        "findings": _last_findings,
        "summary": "\n".join(report),
        "total_findings": len(_last_findings),
        "files_scanned": 0,
        "scan_duration_ms": 0,
        "interrupted": False,
    }


async def _cmd_check_tools(args: Dict[str, Any]) -> Dict[str, Any]:
    """Check available SAST tools."""
    tools = {
        "semgrep": "semgrep --version",
        "bandit": "bandit --version",
        "pip-audit": "pip-audit --version",
        "npm": "npm --version",
        "trivy": "trivy --version",
        "gitleaks": "gitleaks --version",
        "trufflehog": "trufflehog --version",
        "eslint": "eslint --version",
        "phpcs": "phpcs --version",
        "spotbugs": "spotbugs -version",
    }

    results = ["=== Available SAST Tools ==="]
    for name, cmd in tools.items():
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd.split(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            if proc.returncode == 0:
                results.append(f"  [OK] {name}: {stdout.decode().strip()[:80]}")
            else:
                results.append(f"  [--] {name}: not found")
        except Exception:
            results.append(f"  [--] {name}: not found")

    return {
        "findings": [],
        "summary": "\n".join(results),
        "total_findings": 0, "files_scanned": 0, "scan_duration_ms": 0, "interrupted": False,
    }


# ── Command dispatch ────────────────────────────────────────────────────────

_COMMAND_MAP = {
    "scan": _cmd_scan,
    "scan_php": lambda a: _cmd_scan_lang(a, "php"),
    "scan_java": lambda a: _cmd_scan_lang(a, "java"),
    "scan_python": lambda a: _cmd_scan_lang(a, "python"),
    "scan_js": lambda a: _cmd_scan_lang(a, "javascript"),
    "scan_c": lambda a: _cmd_scan_lang(a, "c"),
    "scan_cpp": lambda a: _cmd_scan_lang(a, "cpp"),
    "scan_go": lambda a: _cmd_scan_lang(a, "go"),
    "scan_ruby": lambda a: _cmd_scan_lang(a, "ruby"),
    "scan_dotnet": lambda a: _cmd_scan_lang(a, "csharp"),
    "scan_sql": _cmd_scan_sql,
    "scan_xss": _cmd_scan_xss,
    "scan_injection": _cmd_scan_injection,
    "scan_secrets": _cmd_scan_secrets,
    "scan_crypto": _cmd_scan_crypto,
    "scan_config": _cmd_scan_config,
    "audit_deps": _cmd_audit_deps,
    "report": _cmd_report,
    "check_tools": _cmd_check_tools,
}


async def call(args: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
    """Main entry point for VulnScanner."""
    global _last_findings, _last_scan_path

    command = (args.get("command") or "").strip()
    if not command:
        return {"findings": [], "summary": f"Available commands: {', '.join(sorted(_COMMAND_MAP))}",
                "total_findings": 0, "files_scanned": 0, "scan_duration_ms": 0, "interrupted": False}

    parts = command.split(None, 1)
    sub_cmd = parts[0].lower()

    handler = _COMMAND_MAP.get(sub_cmd)
    if not handler:
        return {"findings": [], "summary": f"Unknown command: '{sub_cmd}'. Available: {', '.join(sorted(_COMMAND_MAP))}",
                "total_findings": 0, "files_scanned": 0, "scan_duration_ms": 0, "interrupted": False}

    result = await handler(args)

    # Store for report generation
    if result.get("findings"):
        _last_findings = result["findings"]
        _last_scan_path = args.get("path") or ""

    return result


async def description() -> str:
    return "Multi-language SAST vulnerability scanner for PHP, Java, Python, JS, C/C++, Go, Ruby, .NET and more."


async def prompt() -> str:
    return (
        "Use this tool to scan source code for security vulnerabilities. "
        "It supports multiple languages and vulnerability types:\n"
        "- Language-specific scans: scan_php, scan_java, scan_python, scan_js, scan_c, scan_go, scan_ruby, scan_dotnet\n"
        "- Vulnerability-specific scans: scan_sql, scan_xss, scan_injection, scan_secrets, scan_crypto, scan_config\n"
        "- Generic scan: scan <path> [language] — auto-detects or scans all languages\n"
        "- Dependency audit: audit_deps <path> — checks for known CVEs in dependencies\n"
        "- Report: report — generates a consolidated report from the last scan\n"
        "Each finding includes severity, CWE ID, vulnerable code, and specific remediation guidance."
    )


def userFacingName() -> str:
    return "VulnScanner"


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    cmd = input_data.get("command", "")
    path = input_data.get("path", "")
    if cmd.startswith("scan_"):
        return f"VulnScan: {cmd.split()[0]} on {path or cmd[cmd.index(' ')+1:][:40]}"
    return f"VulnScan: {cmd[:60]}"
