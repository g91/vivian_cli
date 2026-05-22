"""Compatibility wrapper for state/onChangeAppState.py."""

from __future__ import annotations

from .onChangeAppState import externalMetadataToAppState, onChangeAppState


def external_metadata_to_app_state(metadata: dict):
    return externalMetadataToAppState(metadata)


def on_change_app_state(new_state: dict, old_state: dict) -> None:
    onChangeAppState(newState=new_state, oldState=old_state)
