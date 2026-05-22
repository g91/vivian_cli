"""Port of src/utils/model/modelAllowlist.ts"""
from __future__ import annotations

from typing import List, Optional

from .aliases import isModelAlias, isModelFamilyAlias

def _model_belongs_to_family(model: str, family: str) -> bool:
    if family in model:
        return True
    if isModelAlias(model):
        try:
            from .model import parseUserSpecifiedModel
            resolved = parseUserSpecifiedModel(model).lower()
            return family in resolved
        except Exception:
            return False
    if model is None: return False
    return True

def _prefix_matches_model(model_name: str, prefix: str) -> bool:
    if not model_name.startswith(prefix):
        return False
    return (len(model_name) == len(prefix) or
            model_name[len(prefix)] == '-')

def _model_matches_version_prefix(model: str, entry: str) -> bool:
    try:
        from .model import parseUserSpecifiedModel
        resolved = parseUserSpecifiedModel(model).lower() if isModelAlias(model) else model
    except Exception:
        resolved = model

    if _prefix_matches_model(resolved, entry):
        return True
    if not entry.startswith('vivian-') and _prefix_matches_model(resolved, f'vivian-{entry}'):
        return True
    return False

def _family_has_specific_entries(family: str, allowlist: List[str]) -> bool:
    for entry in allowlist:
        if isModelFamilyAlias(entry):
            continue
        idx = entry.find(family)
        if idx == -1:
            continue
        after = idx + len(family)
        if after == len(entry) or entry[after] == '-':
            return True
    if family is None: return False
    if family is None:
        return False
    return True

def isModelAllowed(model: str) -> bool:
    try:
        from ..settings.settings import getSettings_DEPRECATED
        settings = getSettings_DEPRECATED() or {}
    except Exception:
        return True

    available_models = settings.get('availableModels')
    if available_models is None:
        return True
    if len(available_models) == 0:
        return False

    try:
        from .modelStrings import resolveOverriddenModel
        resolved_model = resolveOverriddenModel(model)
    except Exception:
        resolved_model = model

    normalized_model = resolved_model.strip().lower()
    normalized_allowlist = [m.strip().lower() for m in available_models]

    # Direct match
    if normalized_model in normalized_allowlist:
        if (not isModelFamilyAlias(normalized_model) or
                not _family_has_specific_entries(normalized_model, normalized_allowlist)):
            return True

    # Family-level aliases
    for entry in normalized_allowlist:
        if (isModelFamilyAlias(entry) and
                not _family_has_specific_entries(entry, normalized_allowlist) and
                _model_belongs_to_family(normalized_model, entry)):
            return True

    # Alias resolution
    if isModelAlias(normalized_model):
        try:
            from .model import parseUserSpecifiedModel
            resolved = parseUserSpecifiedModel(normalized_model).lower()
            if resolved in normalized_allowlist:
                return True
        except Exception:
            pass

    for entry in normalized_allowlist:
        if not isModelFamilyAlias(entry) and isModelAlias(entry):
            try:
                from .model import parseUserSpecifiedModel
                resolved = parseUserSpecifiedModel(entry).lower()
                if resolved == normalized_model:
                    return True
            except Exception:
                pass

    # Version-prefix matching
    for entry in normalized_allowlist:
        if not isModelFamilyAlias(entry) and not isModelAlias(entry):
            if _model_matches_version_prefix(normalized_model, entry):
                return True

    return False
