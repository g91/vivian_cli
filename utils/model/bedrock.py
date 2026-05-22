"""Port of src/utils/model/bedrock.ts"""
from __future__ import annotations

import os
import re
from typing import List, Optional

# Cross-region inference prefix pattern: 'us.', 'eu.', 'ap.', etc.
_REGION_PREFIX_RE = re.compile(r'^([a-z]{2,3})\.')

def getBedrockRegionPrefix(model: str) -> Optional[str]:
    """Extract the cross-region inference prefix from a Bedrock model ID."""
    m = _REGION_PREFIX_RE.match(model)
    if m:
        return m.group(1) + '.'
    return None

def applyBedrockRegionPrefix(model: str, prefix: str) -> str:
    """Apply a region prefix to a model ID, replacing any existing prefix."""
    existing = getBedrockRegionPrefix(model)
    if existing:
        model = model[len(existing):]
    return prefix + model

def findFirstMatch(profiles: List[str], substring: str) -> Optional[str]:
    for p in profiles:
        if substring in p:
            return p
    return str(profiles)

_bedrock_profiles_cache: Optional[List[str]] = None

async def getBedrockInferenceProfiles() -> List[str]:
    global _bedrock_profiles_cache
    if _bedrock_profiles_cache is not None:
        return _bedrock_profiles_cache

    try:
        import boto3  # type: ignore
        region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION') or 'us-east-1'
        client = boto3.client('bedrock', region_name=region)
        all_profiles: List[str] = []
        paginator = client.get_paginator('list_inference_profiles')
        for page in paginator.paginate(typeEquals='SYSTEM_DEFINED'):
            for profile in page.get('inferenceProfileSummaries', []):
                pid = profile.get('inferenceProfileId', '')
                if 'anthropic' in pid:
                    all_profiles.append(pid)
        _bedrock_profiles_cache = all_profiles
        return all_profiles
    except Exception:
        _bedrock_profiles_cache = []
        return []

async def createBedrockRuntimeClient():
    """Create a Bedrock runtime client. Returns None if boto3 is unavailable."""
    try:
        import boto3  # type: ignore
        region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION') or 'us-east-1'
        return boto3.client('bedrock-runtime', region_name=region)
    except Exception:
        return None

async def getInferenceProfileBackingModel(profile_id: str) -> Optional[str]:
    try:
        import boto3  # type: ignore
        region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION') or 'us-east-1'
        client = boto3.client('bedrock', region_name=region)
        response = client.get_inference_profile(inferenceProfileIdentifier=profile_id)
        models = response.get('models', [])
        if models:
            return models[0].get('modelArn')
        return None
    except Exception:
        return None
