"""Port of src/utils/permissions/dangerousPatterns.ts"""
from __future__ import annotations
import os
from typing import List

CROSS_PLATFORM_CODE_EXEC: List[str] = [
    # Interpreters
    'python', 'python3', 'python2',
    'node', 'deno', 'tsx',
    'ruby', 'perl', 'php', 'lua',
    # Package runners
    'npx', 'bunx', 'npm run', 'yarn run', 'pnpm run', 'bun run',
    # Shells
    'bash', 'sh',
    # Remote
    'ssh',
]

_ANT_PATTERNS: List[str] = []
if os.environ.get('USER_TYPE') == 'ant':
    _ANT_PATTERNS = [
        'fa run', 'coo',
        'gh', 'gh api',
        'curl', 'wget',
        'git',
        'kubectl', 'aws', 'gcloud', 'gsutil',
    ]

DANGEROUS_BASH_PATTERNS: List[str] = [
    *CROSS_PLATFORM_CODE_EXEC,
    'zsh', 'fish',
    'eval', 'exec', 'env',
    'xargs', 'sudo',
    *_ANT_PATTERNS,
]

DANGEROUS_POWERSHELL_PATTERNS: List[str] = [
    *CROSS_PLATFORM_CODE_EXEC,
    'Invoke-Expression', 'iex',
    'Invoke-Command',
    'Start-Process',
    'Set-ExecutionPolicy',
]
