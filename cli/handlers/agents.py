"""Agents subcommand handler — mirrors src/cli/handlers/agents.ts.

Prints the list of configured agents.
Dynamically imported only when ``vivian agents`` runs.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional


def format_agent(agent: dict) -> str:
    """Format a single agent for display."""
    parts = [agent.get("agentType", "unknown")]
    model = agent.get("model")
    if model:
        parts.append(model)
    memory = agent.get("memory")
    if memory:
        parts.append(f"{memory} memory")
    return " · ".join(parts)


def load_agents_from_dir(directory: str) -> list[dict]:
    """Scan *directory* for agent JSON/YAML files and return a list of dicts."""
    import json

    agents = []
    base = Path(directory)
    if not base.is_dir():
        return agents
    for f in sorted(base.iterdir()):
        if f.suffix in (".json", ".yaml", ".yml"):
            try:
                if f.suffix == ".json":
                    with f.open() as fh:
                        data = json.load(fh)
                else:
                    try:
                        import yaml
                        with f.open() as fh:
                            data = yaml.safe_load(fh)
                    except ImportError:
                        continue
                if isinstance(data, dict):
                    data.setdefault("name", f.stem)
                    data.setdefault("source", "project")
                    agents.append(data)
            except Exception:
                pass
    return agents


def agents_handler(cwd: Optional[str] = None) -> None:
    """Print all configured agents for the current project."""
    cwd = cwd or os.getcwd()

    # Search standard agent directories
    search_dirs = [
        Path(cwd) / ".vivian" / "agents",
        Path.home() / ".vivian" / "agents",
    ]

    all_agents: list[dict] = []
    for d in search_dirs:
        for agent in load_agents_from_dir(str(d)):
            agent.setdefault("_dir", str(d))
            all_agents.append(agent)

    if not all_agents:
        print("No agents found.")
        return

    active = [a for a in all_agents if not a.get("disabled")]
    print(f"{len(active)} active agents\n")
    for agent in sorted(all_agents, key=lambda a: a.get("name", "")):
        line = f"  {format_agent(agent)}"
        if agent.get("disabled"):
            line = f"  (disabled) {format_agent(agent)}"
        print(line)
