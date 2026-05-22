"""Port of src/utils/shell/readOnlyCommandValidation.ts."""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, Literal, TypedDict

from ..platform import get_platform


FlagArgType = Literal["none", "number", "string", "char", "{}", "EOF"]


class ExternalCommandConfig(TypedDict, total=False):
    safeFlags: Dict[str, FlagArgType]
    additionalCommandIsDangerousCallback: Callable[[str, list[str]], bool]
    respectsDoubleDash: bool


GIT_REF_SELECTION_FLAGS: Dict[str, FlagArgType] = {
    "--all": "none",
    "--branches": "none",
    "--tags": "none",
    "--remotes": "none",
}

GIT_DATE_FILTER_FLAGS: Dict[str, FlagArgType] = {
    "--since": "string",
    "--after": "string",
    "--until": "string",
    "--before": "string",
}

GIT_LOG_DISPLAY_FLAGS: Dict[str, FlagArgType] = {
    "--oneline": "none",
    "--graph": "none",
    "--decorate": "none",
    "--no-decorate": "none",
    "--date": "string",
    "--relative-date": "none",
}

GIT_COUNT_FLAGS: Dict[str, FlagArgType] = {
    "--max-count": "number",
    "-n": "number",
}

GIT_STAT_FLAGS: Dict[str, FlagArgType] = {
    "--stat": "none",
    "--numstat": "none",
    "--shortstat": "none",
    "--name-only": "none",
    "--name-status": "none",
}

GIT_COLOR_FLAGS: Dict[str, FlagArgType] = {
    "--color": "none",
    "--no-color": "none",
}

GIT_PATCH_FLAGS: Dict[str, FlagArgType] = {
    "--patch": "none",
    "-p": "none",
    "--no-patch": "none",
    "--no-ext-diff": "none",
    "-s": "none",
}

GIT_AUTHOR_FILTER_FLAGS: Dict[str, FlagArgType] = {
    "--author": "string",
    "--committer": "string",
    "--grep": "string",
}


def ghIsDangerousCallback(_rawCommand: str, args: list[str]) -> bool:
    for token in args:
        if not token:
            continue
        value = token
        if token.startswith("-"):
            eq_idx = token.find("=")
            if eq_idx == -1:
                continue
            value = token[eq_idx + 1 :]
            if not value:
                continue
        if "/" not in value and "://" not in value and "@" not in value:
            continue
        if "://" in value or "@" in value:
            return True
        if value.count("/") >= 2:
            return True
    return False


def _git_reflog_is_dangerous(_raw_command: str, args: list[str]) -> bool:
    dangerous_subcommands = {"expire", "delete", "exists"}
    for token in args:
        if not token or token.startswith("-"):
            continue
        return token in dangerous_subcommands
    return False


def _git_remote_show_is_dangerous(_raw_command: str, args: list[str]) -> bool:
    positional = [arg for arg in args if arg != "-n"]
    if len(positional) != 1:
        return True
    return re.fullmatch(r"[a-zA-Z0-9_-]+", positional[0]) is None


def _git_remote_is_dangerous(_raw_command: str, args: list[str]) -> bool:
    return any(arg not in {"-v", "--verbose"} for arg in args)


GIT_READ_ONLY_COMMANDS: Dict[str, ExternalCommandConfig] = {
    "git diff": {
        "safeFlags": {
            **GIT_STAT_FLAGS,
            **GIT_COLOR_FLAGS,
            "--dirstat": "none",
            "--summary": "none",
            "--patch-with-stat": "none",
            "--word-diff": "none",
            "--word-diff-regex": "string",
            "--color-words": "none",
            "--no-renames": "none",
            "--no-ext-diff": "none",
            "--check": "none",
            "--ws-error-highlight": "string",
            "--full-index": "none",
            "--binary": "none",
            "--abbrev": "number",
            "--break-rewrites": "none",
            "--find-renames": "none",
            "--find-copies": "none",
            "--find-copies-harder": "none",
            "--irreversible-delete": "none",
            "--diff-algorithm": "string",
            "--histogram": "none",
            "--patience": "none",
            "--minimal": "none",
            "--ignore-space-at-eol": "none",
            "--ignore-space-change": "none",
            "--ignore-all-space": "none",
            "--ignore-blank-lines": "none",
            "--inter-hunk-context": "number",
            "--function-context": "none",
            "--exit-code": "none",
            "--quiet": "none",
            "--cached": "none",
            "--staged": "none",
            "--pickaxe-regex": "none",
            "--pickaxe-all": "none",
            "--no-index": "none",
            "--relative": "string",
            "--diff-filter": "string",
            "-p": "none",
            "-u": "none",
            "-s": "none",
            "-M": "none",
            "-C": "none",
            "-B": "none",
            "-D": "none",
            "-l": "none",
            "-S": "string",
            "-G": "string",
            "-O": "string",
            "-R": "none",
        }
    },
    "git log": {
        "safeFlags": {
            **GIT_LOG_DISPLAY_FLAGS,
            **GIT_REF_SELECTION_FLAGS,
            **GIT_DATE_FILTER_FLAGS,
            **GIT_COUNT_FLAGS,
            **GIT_STAT_FLAGS,
            **GIT_COLOR_FLAGS,
            **GIT_PATCH_FLAGS,
            **GIT_AUTHOR_FILTER_FLAGS,
            "--abbrev-commit": "none",
            "--full-history": "none",
            "--dense": "none",
            "--sparse": "none",
            "--simplify-merges": "none",
            "--ancestry-path": "none",
            "--source": "none",
            "--first-parent": "none",
            "--merges": "none",
            "--no-merges": "none",
            "--reverse": "none",
            "--walk-reflogs": "none",
            "--skip": "number",
            "--max-age": "number",
            "--min-age": "number",
            "--no-min-parents": "none",
            "--no-max-parents": "none",
            "--follow": "none",
            "--no-walk": "none",
            "--left-right": "none",
            "--cherry-mark": "none",
            "--cherry-pick": "none",
            "--boundary": "none",
            "--topo-order": "none",
            "--date-order": "none",
            "--author-date-order": "none",
            "--pretty": "string",
            "--format": "string",
            "--diff-filter": "string",
            "-S": "string",
            "-G": "string",
            "--pickaxe-regex": "none",
            "--pickaxe-all": "none",
        }
    },
    "git show": {
        "safeFlags": {
            **GIT_LOG_DISPLAY_FLAGS,
            **GIT_STAT_FLAGS,
            **GIT_COLOR_FLAGS,
            **GIT_PATCH_FLAGS,
            "--abbrev-commit": "none",
            "--word-diff": "none",
            "--word-diff-regex": "string",
            "--color-words": "none",
            "--pretty": "string",
            "--format": "string",
            "--first-parent": "none",
            "--raw": "none",
            "--diff-filter": "string",
            "-m": "none",
            "--quiet": "none",
        }
    },
    "git shortlog": {
        "safeFlags": {
            **GIT_REF_SELECTION_FLAGS,
            **GIT_DATE_FILTER_FLAGS,
            "-s": "none",
            "--summary": "none",
            "-n": "none",
            "--numbered": "none",
            "-e": "none",
            "--email": "none",
            "-c": "none",
            "--committer": "none",
            "--group": "string",
            "--format": "string",
            "--no-merges": "none",
            "--author": "string",
        }
    },
    "git reflog": {
        "safeFlags": {
            **GIT_LOG_DISPLAY_FLAGS,
            **GIT_REF_SELECTION_FLAGS,
            **GIT_DATE_FILTER_FLAGS,
            **GIT_COUNT_FLAGS,
            **GIT_AUTHOR_FILTER_FLAGS,
        },
        "additionalCommandIsDangerousCallback": _git_reflog_is_dangerous,
    },
    "git stash list": {
        "safeFlags": {
            **GIT_LOG_DISPLAY_FLAGS,
            **GIT_REF_SELECTION_FLAGS,
            **GIT_COUNT_FLAGS,
        }
    },
    "git ls-remote": {
        "safeFlags": {
            "--branches": "none",
            "-b": "none",
            "--tags": "none",
            "-t": "none",
            "--heads": "none",
            "-h": "none",
            "--refs": "none",
            "--quiet": "none",
            "-q": "none",
            "--exit-code": "none",
            "--get-url": "none",
            "--symref": "none",
            "--sort": "string",
        }
    },
    "git status": {
        "safeFlags": {
            "--short": "none",
            "-s": "none",
            "--branch": "none",
            "-b": "none",
            "--porcelain": "none",
            "--long": "none",
            "--verbose": "none",
            "-v": "none",
            "--untracked-files": "string",
            "-u": "string",
            "--ignored": "none",
            "--ignore-submodules": "string",
            "--column": "none",
            "--no-column": "none",
            "--ahead-behind": "none",
            "--no-ahead-behind": "none",
            "--renames": "none",
            "--no-renames": "none",
            "--find-renames": "string",
            "-M": "string",
        }
    },
    "git blame": {
        "safeFlags": {
            **GIT_COLOR_FLAGS,
            "-L": "string",
            "--porcelain": "none",
            "-p": "none",
            "--line-porcelain": "none",
            "--incremental": "none",
            "--root": "none",
            "--show-stats": "none",
            "--show-name": "none",
            "--show-number": "none",
            "-n": "none",
            "--show-email": "none",
            "-e": "none",
            "-f": "none",
            "--date": "string",
            "-w": "none",
            "--ignore-rev": "string",
            "--ignore-revs-file": "string",
            "-M": "none",
            "-C": "none",
            "--score-debug": "none",
            "--abbrev": "number",
            "-s": "none",
            "-l": "none",
            "-t": "none",
        }
    },
    "git ls-files": {
        "safeFlags": {
            "--cached": "none",
            "-c": "none",
            "--deleted": "none",
            "-d": "none",
            "--modified": "none",
            "-m": "none",
            "--others": "none",
            "-o": "none",
            "--ignored": "none",
            "-i": "none",
            "--stage": "none",
            "-s": "none",
            "--killed": "none",
            "-k": "none",
            "--unmerged": "none",
            "-u": "none",
            "--directory": "none",
            "--no-empty-directory": "none",
            "--eol": "none",
            "--full-name": "none",
            "--abbrev": "number",
            "--debug": "none",
            "-z": "none",
            "-t": "none",
            "-v": "none",
            "-f": "none",
            "--exclude": "string",
            "-x": "string",
            "--exclude-from": "string",
            "-X": "string",
            "--exclude-per-directory": "string",
            "--exclude-standard": "none",
            "--error-unmatch": "none",
            "--recurse-submodules": "none",
        }
    },
    "git config --get": {
        "safeFlags": {
            "--local": "none",
            "--global": "none",
            "--system": "none",
            "--worktree": "none",
            "--default": "string",
            "--type": "string",
            "--bool": "none",
            "--int": "none",
            "--bool-or-int": "none",
            "--path": "none",
            "--expiry-date": "none",
            "-z": "none",
            "--null": "none",
            "--name-only": "none",
            "--show-origin": "none",
            "--show-scope": "none",
        }
    },
    "git remote show": {
        "safeFlags": {"-n": "none"},
        "additionalCommandIsDangerousCallback": _git_remote_show_is_dangerous,
    },
    "git remote": {
        "safeFlags": {"-v": "none", "--verbose": "none"},
        "additionalCommandIsDangerousCallback": _git_remote_is_dangerous,
    },
    "git merge-base": {
        "safeFlags": {
            "--is-ancestor": "none",
            "--fork-point": "none",
            "--octopus": "none",
            "--independent": "none",
            "--all": "none",
        }
    },
    "git rev-parse": {
        "safeFlags": {
            "--verify": "none",
            "--short": "string",
            "--abbrev-ref": "none",
            "--symbolic": "none",
            "--symbolic-full-name": "none",
            "--quiet": "none",
            "--sq": "none",
            "--sq-quote": "none",
            "--show-toplevel": "none",
            "--show-prefix": "none",
            "--show-cdup": "none",
            "--git-dir": "none",
            "--git-common-dir": "none",
            "--absolute-git-dir": "none",
            "--is-inside-git-dir": "none",
            "--is-inside-work-tree": "none",
            "--is-bare-repository": "none",
            "--is-shallow-repository": "none",
            "--show-object-format": "none",
            "--show-ref-format": "none",
        }
    },
}

GH_READ_ONLY_COMMANDS: Dict[str, ExternalCommandConfig] = {
    "gh pr view": {"safeFlags": {"--json": "string", "--comments": "none", "--repo": "string", "-R": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh pr list": {"safeFlags": {"--state": "string", "-s": "string", "--author": "string", "--assignee": "string", "--label": "string", "--limit": "number", "-L": "number", "--base": "string", "--head": "string", "--search": "string", "--json": "string", "--draft": "none", "--app": "string", "--repo": "string", "-R": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh pr diff": {"safeFlags": {"--color": "string", "--name-only": "none", "--patch": "none", "--repo": "string", "-R": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh pr checks": {"safeFlags": {"--watch": "none", "--required": "none", "--fail-fast": "none", "--json": "string", "--interval": "number", "--repo": "string", "-R": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh issue view": {"safeFlags": {"--json": "string", "--comments": "none", "--repo": "string", "-R": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh issue list": {"safeFlags": {"--state": "string", "-s": "string", "--assignee": "string", "--author": "string", "--label": "string", "--limit": "number", "-L": "number", "--milestone": "string", "--search": "string", "--json": "string", "--app": "string", "--repo": "string", "-R": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh repo view": {"safeFlags": {"--json": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh run list": {"safeFlags": {"--branch": "string", "-b": "string", "--status": "string", "-s": "string", "--workflow": "string", "-w": "string", "--limit": "number", "-L": "number", "--json": "string", "--repo": "string", "-R": "string", "--event": "string", "-e": "string", "--user": "string", "-u": "string", "--created": "string", "--commit": "string", "-c": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh run view": {"safeFlags": {"--log": "none", "--log-failed": "none", "--exit-status": "none", "--verbose": "none", "-v": "none", "--json": "string", "--repo": "string", "-R": "string", "--job": "string", "-j": "string", "--attempt": "number", "-a": "number"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh auth status": {"safeFlags": {"--active": "none", "-a": "none", "--hostname": "string", "-h": "string", "--json": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh pr status": {"safeFlags": {"--conflict-status": "none", "-c": "none", "--json": "string", "--repo": "string", "-R": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh issue status": {"safeFlags": {"--json": "string", "--repo": "string", "-R": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh release list": {"safeFlags": {"--exclude-drafts": "none", "--exclude-pre-releases": "none", "--json": "string", "--limit": "number", "-L": "number", "--order": "string", "-O": "string", "--repo": "string", "-R": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh release view": {"safeFlags": {"--json": "string", "--repo": "string", "-R": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh workflow list": {"safeFlags": {"--all": "none", "-a": "none", "--json": "string", "--limit": "number", "-L": "number", "--repo": "string", "-R": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh workflow view": {"safeFlags": {"--ref": "string", "-r": "string", "--yaml": "none", "-y": "none", "--repo": "string", "-R": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh label list": {"safeFlags": {"--json": "string", "--limit": "number", "-L": "number", "--order": "string", "--search": "string", "-S": "string", "--sort": "string", "--repo": "string", "-R": "string"}, "additionalCommandIsDangerousCallback": ghIsDangerousCallback},
    "gh search repos": {"safeFlags": {"--archived": "none", "--created": "string", "--followers": "string", "--forks": "string", "--good-first-issues": "string", "--help-wanted-issues": "string", "--include-forks": "string", "--json": "string", "--language": "string", "--license": "string", "--limit": "number", "-L": "number", "--match": "string", "--number-topics": "string", "--order": "string", "--owner": "string", "--size": "string", "--sort": "string", "--stars": "string", "--topic": "string", "--updated": "string", "--visibility": "string"}},
    "gh search issues": {"safeFlags": {"--app": "string", "--assignee": "string", "--author": "string", "--closed": "string", "--commenter": "string", "--comments": "string", "--created": "string", "--include-prs": "none", "--interactions": "string", "--involves": "string", "--json": "string", "--label": "string", "--language": "string", "--limit": "number", "-L": "number", "--locked": "none", "--match": "string", "--mentions": "string", "--milestone": "string", "--no-assignee": "none", "--no-label": "none", "--no-milestone": "none", "--no-project": "none", "--order": "string", "--owner": "string", "--project": "string", "--reactions": "string", "--repo": "string", "-R": "string", "--sort": "string", "--state": "string", "--team-mentions": "string", "--updated": "string", "--visibility": "string"}},
    "gh search prs": {"safeFlags": {"--app": "string", "--assignee": "string", "--author": "string", "--base": "string", "-B": "string", "--checks": "string", "--closed": "string", "--commenter": "string", "--comments": "string", "--created": "string", "--draft": "none", "--head": "string", "-H": "string", "--interactions": "string", "--involves": "string", "--json": "string", "--label": "string", "--language": "string", "--limit": "number", "-L": "number", "--locked": "none", "--match": "string", "--mentions": "string", "--merged": "none", "--merged-at": "string", "--milestone": "string", "--no-assignee": "none", "--no-label": "none", "--no-milestone": "none", "--no-project": "none", "--order": "string", "--owner": "string", "--project": "string", "--reactions": "string", "--repo": "string", "-R": "string", "--review": "string", "--review-requested": "string", "--reviewed-by": "string", "--sort": "string", "--state": "string", "--team-mentions": "string", "--updated": "string", "--visibility": "string"}},
    "gh search commits": {"safeFlags": {"--author": "string", "--author-date": "string", "--author-email": "string", "--author-name": "string", "--committer": "string", "--committer-date": "string", "--committer-email": "string", "--committer-name": "string", "--hash": "string", "--json": "string", "--limit": "number", "-L": "number", "--merge": "none", "--order": "string", "--owner": "string", "--parent": "string", "--repo": "string", "-R": "string", "--sort": "string", "--tree": "string", "--visibility": "string"}},
    "gh search code": {"safeFlags": {"--extension": "string", "--filename": "string", "--json": "string", "--language": "string", "--limit": "number", "-L": "number", "--match": "string", "--owner": "string", "--repo": "string", "-R": "string", "--size": "string"}},
}

DOCKER_READ_ONLY_COMMANDS: Dict[str, ExternalCommandConfig] = {
    "docker logs": {"safeFlags": {"--follow": "none", "-f": "none", "--tail": "string", "-n": "string", "--timestamps": "none", "-t": "none", "--since": "string", "--until": "string", "--details": "none"}},
    "docker inspect": {"safeFlags": {"--format": "string", "-f": "string", "--type": "string", "--size": "none", "-s": "none"}},
}

RIPGREP_READ_ONLY_COMMANDS: Dict[str, ExternalCommandConfig] = {
    "rg": {
        "safeFlags": {
            "-A": "number",
            "--after-context": "number",
            "-B": "number",
            "--before-context": "number",
            "-C": "number",
            "--context": "number",
            "-H": "none",
            "-h": "none",
            "--heading": "none",
            "--no-heading": "none",
            "-q": "none",
            "--quiet": "none",
            "--column": "none",
            "-g": "string",
            "--glob": "string",
            "-t": "string",
            "--type": "string",
            "-T": "string",
            "--type-not": "string",
            "--type-list": "none",
            "--hidden": "none",
            "--no-ignore": "none",
            "-u": "none",
            "-m": "number",
            "--max-count": "number",
            "-d": "number",
            "--max-depth": "number",
            "-a": "none",
            "--text": "none",
            "-z": "none",
            "-L": "none",
            "--follow": "none",
            "--color": "string",
            "--json": "none",
            "--stats": "none",
            "--help": "none",
            "--version": "none",
            "--debug": "none",
            "--": "none",
        }
    }
}

PYRIGHT_READ_ONLY_COMMANDS: Dict[str, ExternalCommandConfig] = {
    "pyright": {
        "respectsDoubleDash": False,
        "safeFlags": {
            "--outputjson": "none",
            "--project": "string",
            "-p": "string",
            "--pythonversion": "string",
            "--pythonplatform": "string",
            "--typeshedpath": "string",
            "--venvpath": "string",
            "--level": "string",
            "--stats": "none",
            "--verbose": "none",
            "--version": "none",
            "--dependencies": "none",
            "--warnings": "none",
        },
        "additionalCommandIsDangerousCallback": lambda _raw_command, args: any(token in {"--watch", "-w"} for token in args),
    }
}

EXTERNAL_READONLY_COMMANDS: list[str] = ["docker ps", "docker images"]

FLAG_PATTERN = re.compile(r"^-[a-zA-Z0-9_-]")


def containsVulnerableUncPath(pathOrCommand: str) -> bool:
    if get_platform() != "windows":
        return False
    if re.search(r"\\\\[^\s\\/]+(?:@(?:\d+|ssl))?(?:[\\/]|$|\s)", pathOrCommand, re.IGNORECASE):
        return True
    if re.search(r"(?<!:)//[^\s\\/]+(?:@(?:\d+|ssl))?(?:[\\/]|$|\s)", pathOrCommand, re.IGNORECASE):
        return True
    if re.search(r"/\\{2,}[^\s\\/]", pathOrCommand):
        return True
    if re.search(r"\\{2,}/[^\s\\/]", pathOrCommand):
        return True
    if re.search(r"@SSL@\d+", pathOrCommand, re.IGNORECASE) or re.search(r"@\d+@SSL", pathOrCommand, re.IGNORECASE):
        return True
    if re.search(r"DavWWWRoot", pathOrCommand, re.IGNORECASE):
        return True
    if re.search(r"^(?:\\\\|//)(\d{1,3}(?:\.\d{1,3}){3})[\\/]", pathOrCommand):
        return True
    if re.search(r"^(?:\\\\|//)(\[[\da-fA-F:]+\])[\\/]", pathOrCommand):
        return True
    return False


def validateFlagArgument(value: str, argType: FlagArgType) -> bool:
    if argType == "number":
        return re.fullmatch(r"\d+", value) is not None
    if argType == "string":
        return True
    if argType == "char":
        return len(value) == 1
    if argType == "{}":
        return value == "{}"
    if argType == "EOF":
        return value == "EOF"
    return False


def validateFlags(tokens: list[str], startIndex: int, config: ExternalCommandConfig, options: dict[str, Any] | None = None) -> bool:
    options = options or {}
    i = startIndex
    safe_flags = config.get("safeFlags", {})

    while i < len(tokens):
        token = tokens[i]
        if not token:
            i += 1
            continue

        if options.get("xargsTargetCommands") and options.get("commandName") == "xargs" and (not token.startswith("-") or token == "--"):
            if token == "--" and i + 1 < len(tokens):
                i += 1
                token = tokens[i]
            if token in options["xargsTargetCommands"]:
                break
            return False

        if token == "--":
            if config.get("respectsDoubleDash", True):
                i += 1
                break
            i += 1
            continue

        if token.startswith("-") and len(token) > 1 and FLAG_PATTERN.match(token):
            has_equals = "=" in token
            flag, *value_parts = token.split("=")
            inline_value = "=".join(value_parts)
            if not flag:
                return False

            flag_arg_type = safe_flags.get(flag)
            if not flag_arg_type:
                if options.get("commandName") == "git" and re.fullmatch(r"-\d+", flag):
                    i += 1
                    continue
                if options.get("commandName") in {"grep", "rg"} and flag.startswith("-") and not flag.startswith("--") and len(flag) > 2:
                    potential_flag = flag[:2]
                    potential_value = flag[2:]
                    if safe_flags.get(potential_flag) in {"number", "string"} and re.fullmatch(r"\d+", potential_value):
                        if validateFlagArgument(potential_value, safe_flags[potential_flag]):
                            i += 1
                            continue
                        return False
                if flag.startswith("-") and not flag.startswith("--") and len(flag) > 2:
                    for char in flag[1:]:
                        single_flag = f"-{char}"
                        flag_type = safe_flags.get(single_flag)
                        if not flag_type or flag_type != "none":
                            return False
                    i += 1
                    continue
                return False

            if flag_arg_type == "none":
                if has_equals:
                    return False
                i += 1
                continue

            if has_equals:
                arg_value = inline_value
                i += 1
            else:
                if i + 1 >= len(tokens):
                    return False
                next_token = tokens[i + 1]
                if next_token and next_token.startswith("-") and len(next_token) > 1 and FLAG_PATTERN.match(next_token):
                    return False
                arg_value = next_token or ""
                i += 2

            if flag_arg_type == "string" and arg_value.startswith("-"):
                if not (flag == "--sort" and options.get("commandName") == "git" and re.match(r"^-[a-zA-Z]", arg_value)):
                    return False
            if not validateFlagArgument(arg_value, flag_arg_type):
                return False
        else:
            i += 1

    callback = config.get("additionalCommandIsDangerousCallback")
    if callback and callback(options.get("rawCommand", ""), tokens[startIndex:]):
        return False
    return True

