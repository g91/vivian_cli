"""Migrations package — mirrors src/migrations/.

Run all migrations at startup to keep config/settings in sync.
"""
from .migrate_auto_updates_to_settings import migrate_auto_updates_to_settings
from .migrate_bypass_permissions_accepted_to_settings import (
    migrate_bypass_permissions_accepted_to_settings,
)
from .migrate_enable_all_project_mcp_servers_to_settings import (
    migrate_enable_all_project_mcp_servers_to_settings,
)
from .migrate_fennec_to_opus import migrate_fennec_to_opus
from .migrate_legacy_opus_to_current import migrate_legacy_opus_to_current
from .migrate_opus_to_opus_1m import migrate_opus_to_opus_1m
from .migrate_repl_bridge_enabled_to_remote_control_at_startup import (
    migrate_repl_bridge_enabled_to_remote_control_at_startup,
)
from .migrate_sonnet_1m_to_sonnet_45 import migrate_sonnet_1m_to_sonnet_45
from .migrate_sonnet_45_to_sonnet_46 import migrate_sonnet_45_to_sonnet_46
from .reset_auto_mode_opt_in_for_default_offer import reset_auto_mode_opt_in_for_default_offer
from .reset_pro_to_opus_default import reset_pro_to_opus_default

_ALL_MIGRATIONS = [
    migrate_auto_updates_to_settings,
    migrate_bypass_permissions_accepted_to_settings,
    migrate_enable_all_project_mcp_servers_to_settings,
    migrate_fennec_to_opus,
    migrate_legacy_opus_to_current,
    migrate_opus_to_opus_1m,
    migrate_repl_bridge_enabled_to_remote_control_at_startup,
    migrate_sonnet_1m_to_sonnet_45,
    migrate_sonnet_45_to_sonnet_46,
    reset_auto_mode_opt_in_for_default_offer,
    reset_pro_to_opus_default,
]


def run_all_migrations() -> None:
    """Run every migration in order.  Each is idempotent."""
    for migration in _ALL_MIGRATIONS:
        try:
            migration()
        except Exception:
            pass


__all__ = [
    "run_all_migrations",
    "migrate_auto_updates_to_settings",
    "migrate_bypass_permissions_accepted_to_settings",
    "migrate_enable_all_project_mcp_servers_to_settings",
    "migrate_fennec_to_opus",
    "migrate_legacy_opus_to_current",
    "migrate_opus_to_opus_1m",
    "migrate_repl_bridge_enabled_to_remote_control_at_startup",
    "migrate_sonnet_1m_to_sonnet_45",
    "migrate_sonnet_45_to_sonnet_46",
    "reset_auto_mode_opt_in_for_default_offer",
    "reset_pro_to_opus_default",
]
