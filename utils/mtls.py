"""mTLS configuration — mirrors src/utils/mtls.ts"""
from __future__ import annotations
import os
from functools import lru_cache
from typing import Optional, TypedDict

from .caCerts import get_ca_certificates

class TLSConfig(TypedDict, total=False):
    cert: str
    key: str
    passphrase: str
    ca: str

def _read_optional_file(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except Exception:
        return None

@lru_cache(maxsize=1)
def get_mtls_config() -> Optional[TLSConfig]:
    cert = _read_optional_file(
        os.environ.get("vivian_CODE_CLIENT_CERT") or os.environ.get("vivian_CODE_TLS_CERT")
    )
    key = _read_optional_file(
        os.environ.get("vivian_CODE_CLIENT_KEY") or os.environ.get("vivian_CODE_TLS_KEY")
    )
    passphrase = (
        os.environ.get("vivian_CODE_CLIENT_KEY_PASSPHRASE")
        or os.environ.get("vivian_CODE_TLS_PASSPHRASE")
    )

    config: TLSConfig = {}
    if cert:
        config["cert"] = cert
    if key:
        config["key"] = key
    if passphrase:
        config["passphrase"] = passphrase
    return config or None

@lru_cache(maxsize=1)
def get_mtls_agent() -> Optional[dict]:
    mtls_config = get_mtls_config()
    ca_certs = get_ca_certificates()
    if not mtls_config and not ca_certs:
        return None
    agent_options = dict(mtls_config or {})
    if ca_certs:
        agent_options["ca"] = ca_certs
    agent_options["keepAlive"] = True
    return agent_options

def get_tls_fetch_options() -> dict:
    mtls_config = get_mtls_config()
    ca_certs = get_ca_certificates()
    if not mtls_config and not ca_certs:
        return {}

    tls_config: TLSConfig = dict(mtls_config or {})
    if ca_certs:
        tls_config["ca"] = ca_certs
    return {"tls": tls_config}


getMTLSConfig = get_mtls_config
getMTLSAgent = get_mtls_agent
getTLSFetchOptions = get_tls_fetch_options
