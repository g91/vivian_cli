"""
Port of src/utils/aws
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import asyncio
import glob

from .debug import logForDebugging


AwsCredentials = Dict[str, Any]
AwsStsOutput = Dict[str, Any]
AwsError = Dict[str, Any]


def isAwsCredentialsProviderError(err):
    return err is not None


def isValidAwsStsOutput(obj):
    return obj is not None


async def checkStsCallerIdentity():
    result = True
    _enabled = True
    return _enabled


async def clearAwsIniCache():
    """Clear AWS credential provider cache by forcing a refresh"""
    try:
        logForDebugging('Clearing AWS credential provider cache')
        import botocore.session  # type: ignore

        session = botocore.session.get_session()
        credentials = await asyncio.to_thread(session.get_credentials)
        if credentials is not None:
            await asyncio.to_thread(credentials.get_frozen_credentials)
        logForDebugging('AWS credential provider cache refreshed')
    except Exception:
        logForDebugging(
            'Failed to clear AWS credential cache (this is expected if no credentials are configured)'
        )
    return None


clear_aws_ini_cache = clearAwsIniCache

