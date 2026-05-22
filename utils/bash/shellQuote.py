"""
Port of src/utils/bash/shellQuote.ts
Real Python implementation using shlex for shell parsing/quoting.
"""
from __future__ import annotations

import re
import shlex
from typing import Any, Optional, Union

ParseEntry = Any

OPERATORS_2 = {'||', '&&', '>>', '<<', '|&', '&>'}
OPERATORS_1 = {'|', ';', '&', '>', '<'}


def _parse_shell_tokens(cmd, env=None):
    tokens = []
    i = 0
    n = len(cmd)
    current_word = []

    def flush_word():
        if current_word:
            word = ''.join(current_word)
            if env is not None:
                if callable(env):
                    word = re.sub(r'\$([A-Za-z_][A-Za-z0-9_]*)',
                                  lambda m: str(env(m.group(1)) or '$' + m.group(1)), word)
                elif isinstance(env, dict):
                    word = re.sub(r'\$([A-Za-z_][A-Za-z0-9_]*)',
                                  lambda m: str(env.get(m.group(1), '$' + m.group(1))), word)
            tokens.append(word)
            current_word.clear()

    while i < n:
        c = cmd[i]
        if c in (' ', '\t'):
            flush_word()
            i += 1
            continue
        if c == '\n':
            flush_word()
            tokens.append({'op': ';'})
            i += 1
            continue
        if c == "'":
            end = cmd.find("'", i + 1)
            if end == -1:
                current_word.append(cmd[i + 1:])
                i = n
            else:
                current_word.append(cmd[i + 1:end])
                i = end + 1
            continue
        if c == '"':
            i += 1
            while i < n and cmd[i] != '"':
                if cmd[i] == '\\' and i + 1 < n and cmd[i + 1] in ('"', '\\', '$', '`'):
                    current_word.append(cmd[i + 1])
                    i += 2
                else:
                    current_word.append(cmd[i])
                    i += 1
            if i < n:
                i += 1
            continue
        if c == '\\':
            if i + 1 < n:
                next_c = cmd[i + 1]
                if next_c == '\n':
                    i += 2
                else:
                    current_word.append(next_c)
                    i += 2
            else:
                i += 1
            continue
        if c == '#' and not current_word:
            comment_end = cmd.find('\n', i)
            if comment_end == -1:
                comment_end = n
            tokens.append({'comment': cmd[i + 1:comment_end]})
            i = comment_end
            continue
        two = cmd[i:i + 2]
        if two in OPERATORS_2 and not current_word:
            flush_word()
            tokens.append({'op': two})
            i += 2
            continue
        if c in OPERATORS_1 and not current_word:
            flush_word()
            tokens.append({'op': c})
            i += 1
            continue
        if c in ('*', '?') and not current_word:
            flush_word()
            tokens.append({'op': 'glob', 'pattern': c})
            i += 1
            continue
        current_word.append(c)
        i += 1

    flush_word()
    return tokens


def tryParseShellCommand(cmd, env=None):
    try:
        tokens = _parse_shell_tokens(cmd, env)
        return {'success': True, 'tokens': tokens}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def tryQuoteShellArgs(args):
    try:
        validated = []
        for idx, arg in enumerate(args):
            if arg is None:
                validated.append('None')
            elif isinstance(arg, str):
                validated.append(arg)
            elif isinstance(arg, (int, float, bool)):
                validated.append(str(arg))
            elif isinstance(arg, (list, dict)):
                raise ValueError(
                    'Cannot quote argument at index %d: object values are not supported' % idx
                )
            else:
                validated.append(str(arg))
        quoted = shlex.join(validated)
        return {'success': True, 'quoted': quoted}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def hasMalformedTokens(command, parsed):
    in_single = False
    in_double = False
    double_count = 0
    single_count = 0
    i = 0
    while i < len(command):
        c = command[i]
        if c == '\\' and not in_single:
            i += 2
            continue
        if c == '"' and not in_single:
            double_count += 1
            in_double = not in_double
        elif c == "'" and not in_double:
            single_count += 1
            in_single = not in_single
        i += 1

    if double_count % 2 != 0 or single_count % 2 != 0:
        return True

    for entry in parsed:
        if not isinstance(entry, str):
            continue
        if entry.count('{') != entry.count('}'):
            return True

    return False


def hasShellQuoteSingleQuoteBug(command: str) -> bool:
    """Detects commands with backslash patterns that exploit shell-quote's
    incorrect handling of backslashes inside single quotes.

    In bash, single quotes preserve ALL characters literally — backslash has no
    special meaning. So '\\'' is just \\ (opens, contains \\, closes). But
    shell-quote incorrectly treats \\ as an escape inside single quotes, causing
    '\\\'' to NOT close the quoted string.
    """
    in_single_quote = False
    in_double_quote = False
    i = 0
    while i < len(command):
        char = command[i]

        # Backslash escaping outside of single quotes
        if char == '\\' and not in_single_quote:
            i += 2  # skip escaped char
            continue

        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            i += 1
            continue

        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote

            if not in_single_quote:
                # Just closed a single quote — check trailing backslashes
                backslash_count = 0
                j = i - 1
                while j >= 0 and command[j] == '\\':
                    backslash_count += 1
                    j -= 1

                if backslash_count > 0 and backslash_count % 2 == 1:
                    return True

                # Even trailing backslashes: bug only when a later ' exists
                if (
                    backslash_count > 0
                    and backslash_count % 2 == 0
                    and command.find("'", i + 1) != -1
                ):
                    return True

            i += 1
            continue

        i += 1

    return False


def quote(args):
    if not args:
        return ''
    redirect_ops = {'<', '>', '>>', '<<', '2>', '2>>', '&>', '|', '||', '&&', ';'}
    result_parts = []
    for arg in args:
        if isinstance(arg, str) and arg in redirect_ops:
            result_parts.append(arg)
        elif isinstance(arg, str):
            result_parts.append(shlex.quote(arg))
        else:
            result_parts.append(shlex.quote(str(arg)))
    return ' '.join(result_parts)
