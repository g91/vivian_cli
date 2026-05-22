"""
Port of src/utils/generatedFiles.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import re


EXCLUDED_FILENAMES = {
    'package-lock.json',
    'yarn.lock',
    'pnpm-lock.yaml',
    'bun.lockb',
    'bun.lock',
    'composer.lock',
    'gemfile.lock',
    'cargo.lock',
    'poetry.lock',
    'pipfile.lock',
    'shrinkwrap.json',
    'npm-shrinkwrap.json',
}

EXCLUDED_EXTENSIONS = {
    '.lock',
    '.min.js',
    '.min.css',
    '.min.html',
    '.bundle.js',
    '.bundle.css',
    '.generated.ts',
    '.generated.js',
    '.d.ts',
}

EXCLUDED_DIRECTORIES = [
    '/dist/',
    '/build/',
    '/out/',
    '/output/',
    '/node_modules/',
    '/vendor/',
    '/vendored/',
    '/third_party/',
    '/third-party/',
    '/external/',
    '/.next/',
    '/.nuxt/',
    '/.svelte-kit/',
    '/coverage/',
    '/__pycache__/',
    '/.tox/',
    '/venv/',
    '/.venv/',
    '/target/release/',
    '/target/debug/',
]

EXCLUDED_FILENAME_PATTERNS = [
    re.compile(r'^.*\.min\.[a-z]+$', re.IGNORECASE),
    re.compile(r'^.*-min\.[a-z]+$', re.IGNORECASE),
    re.compile(r'^.*\.bundle\.[a-z]+$', re.IGNORECASE),
    re.compile(r'^.*\.generated\.[a-z]+$', re.IGNORECASE),
    re.compile(r'^.*\.gen\.[a-z]+$', re.IGNORECASE),
    re.compile(r'^.*\.auto\.[a-z]+$', re.IGNORECASE),
    re.compile(r'^.*_generated\.[a-z]+$', re.IGNORECASE),
    re.compile(r'^.*_gen\.[a-z]+$', re.IGNORECASE),
    re.compile(r'^.*\.pb\.(go|js|ts|py|rb)$', re.IGNORECASE),
    re.compile(r'^.*_pb2?\.py$', re.IGNORECASE),
    re.compile(r'^.*\.pb\.h$', re.IGNORECASE),
    re.compile(r'^.*\.grpc\.[a-z]+$', re.IGNORECASE),
    re.compile(r'^.*\.swagger\.[a-z]+$', re.IGNORECASE),
    re.compile(r'^.*\.openapi\.[a-z]+$', re.IGNORECASE),
]


def isGeneratedFile(filePath):
    """Check if a file should be excluded from attribution based on Linguist-style rules.

@param filePath - Relative file path from repository root
@returns true if the file should be excluded from attribution"""
    normalized_path = '/' + str(filePath).replace('\\', '/').lstrip('/')
    file_name = normalized_path.rsplit('/', 1)[-1].lower()
    parts = file_name.split('.')
    ext = f".{parts[-1]}" if len(parts) > 1 else ''

    if file_name in EXCLUDED_FILENAMES:
        return True
    if ext in EXCLUDED_EXTENSIONS:
        return True
    if len(parts) > 2:
        compound_ext = '.' + '.'.join(parts[-2:])
        if compound_ext in EXCLUDED_EXTENSIONS:
            return True
    if any(directory in normalized_path for directory in EXCLUDED_DIRECTORIES):
        return True
    return any(pattern.match(file_name) for pattern in EXCLUDED_FILENAME_PATTERNS)


def filterGeneratedFiles(files):
    """Filter a list of files to exclude generated files.

@param files - Array of file paths
@returns Array of files that are not generated"""
    return [file for file in (files or []) if not isGeneratedFile(file)]


is_generated_file = isGeneratedFile
filter_generated_files = filterGeneratedFiles

