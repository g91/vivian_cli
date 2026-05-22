"""Port of src/utils/computerUse/appNames.ts."""
from __future__ import annotations

import re
from typing import Any


InstalledAppLike = dict[str, Any]
PATH_ALLOWLIST = ["/Applications/", "/System/Applications/"]
NAME_PATTERN_BLOCKLIST = [
    re.compile(r"Helper(?:$|\s\()"),
    re.compile(r"Agent(?:$|\s\()"),
    re.compile(r"Service(?:$|\s\()"),
    re.compile(r"Uninstaller(?:$|\s\()"),
    re.compile(r"Updater(?:$|\s\()"),
    re.compile(r"^\."),
]
ALWAYS_KEEP_BUNDLE_IDS = {
    "com.apple.Safari",
    "com.google.Chrome",
    "com.microsoft.edgemac",
    "org.mozilla.firefox",
    "company.thebrowser.Browser",
    "com.tinyspeck.slackmacgap",
    "us.zoom.xos",
    "com.microsoft.teams2",
    "com.microsoft.teams",
    "com.apple.MobileSMS",
    "com.apple.mail",
    "com.microsoft.Word",
    "com.microsoft.Excel",
    "com.microsoft.Powerpoint",
    "com.microsoft.Outlook",
    "com.apple.iWork.Pages",
    "com.apple.iWork.Numbers",
    "com.apple.iWork.Keynote",
    "com.google.GoogleDocs",
    "notion.id",
    "com.apple.Notes",
    "md.obsidian",
    "com.linear",
    "com.figma.Desktop",
    "com.microsoft.VSCode",
    "com.apple.Terminal",
    "com.googlecode.iterm2",
    "com.github.GitHubDesktop",
    "com.apple.finder",
    "com.apple.iCal",
    "com.apple.systempreferences",
}
APP_NAME_ALLOWED = re.compile(r"^[\w .&'()+\-\u00C0-\uFFFF]+$", re.UNICODE)
APP_NAME_MAX_LEN = 40
APP_NAME_MAX_COUNT = 50


def isUserFacingPath(path, homeDir):
    if any(str(path).startswith(root) for root in PATH_ALLOWLIST):
        return True
    if homeDir:
        user_apps = f"{str(homeDir).rstrip('/')}/Applications/"
        if str(path).startswith(user_apps):
            return True
    return False


def isNoisyName(name):
    return any(pattern.search(str(name)) for pattern in NAME_PATTERN_BLOCKLIST)


def sanitizeCore(raw, applyCharFilter):
    seen: set[str] = set()
    cleaned: list[str] = []
    for name in raw:
        trimmed = str(name).strip()
        if not trimmed:
            continue
        if len(trimmed) > APP_NAME_MAX_LEN:
            continue
        if applyCharFilter and not APP_NAME_ALLOWED.match(trimmed):
            continue
        if trimmed in seen:
            continue
        seen.add(trimmed)
        cleaned.append(trimmed)
    return sorted(cleaned, key=lambda value: value.casefold())


def sanitizeAppNames(raw):
    filtered = sanitizeCore(raw, True)
    if len(filtered) <= APP_NAME_MAX_COUNT:
        return filtered
    return [*filtered[:APP_NAME_MAX_COUNT], f"… and {len(filtered) - APP_NAME_MAX_COUNT} more"]


def sanitizeTrustedNames(raw):
    return sanitizeCore(raw, False)


def filterAppsForDescription(installed, homeDir):
    always_kept: list[str] = []
    rest: list[str] = []
    for app in installed:
        bundle_id = str(app.get("bundleId", ""))
        display_name = str(app.get("displayName", ""))
        path = str(app.get("path", ""))
        if bundle_id in ALWAYS_KEEP_BUNDLE_IDS:
            always_kept.append(display_name)
        elif isUserFacingPath(path, homeDir) and not isNoisyName(display_name):
            rest.append(display_name)
    sanitized_always = sanitizeTrustedNames(always_kept)
    always_set = set(sanitized_always)
    return [*sanitized_always, *[name for name in sanitizeAppNames(rest) if name not in always_set]]


is_user_facing_path = isUserFacingPath
is_noisy_name = isNoisyName
sanitize_core = sanitizeCore
sanitize_app_names = sanitizeAppNames
sanitize_trusted_names = sanitizeTrustedNames
filter_apps_for_description = filterAppsForDescription

