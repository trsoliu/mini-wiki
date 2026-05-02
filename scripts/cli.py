#!/usr/bin/env python3
"""
Mini-Wiki CLI — Generate professional project documentation with AI.

Usage:
    mini-wiki init [--force]
    mini-wiki analyze [PATH]
    mini-wiki check [PATH]
    mini-wiki changes [PATH]
    mini-wiki plugins list [PATH]
    mini-wiki plugins enable NAME [PATH]
    mini-wiki plugins disable NAME [PATH]
    mini-wiki plugins install SOURCE [PATH]
    mini-wiki plugins uninstall NAME [PATH]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from analyze_project import analyze_project, print_analysis
from check_quality import check_wiki_quality
from detect_changes import detect_changes, print_changes
from init_wiki import init_mini_wiki, print_result
from plugin_manager import (
    enable_plugin,
    install_plugin,
    list_plugins,
    print_plugins,
    uninstall_plugin,
    update_plugin,
)


def _resolve_project(path: str | None) -> str:
    if path:
        return str(Path(path).resolve())
    return os.getcwd()


@click.group()
@click.version_option(version="3.2.0", prog_name="mini-wiki")
def main():
    """Mini-Wiki: AI-powered project documentation generator."""


# --- init ---


@main.command()
@click.option("--force", is_flag=True, help="Force re-initialization (backs up existing config).")
@click.argument("path", required=False)
def init(force: bool, path: str | None):
    """Initialize .mini-wiki directory structure."""
    project = _resolve_project(path)
    result = init_mini_wiki(project, force=force)
    print_result(result)
    sys.exit(0 if result["success"] else 1)


# --- analyze ---


@main.command()
@click.option("--no-cache", is_flag=True, help="Don't save results to cache.")
@click.argument("path", required=False)
def analyze(no_cache: bool, path: str | None):
    """Analyze project structure and tech stack."""
    project = _resolve_project(path)
    result = analyze_project(project, save_to_cache=not no_cache)
    print_analysis(result)


# --- check ---


@main.command()
@click.argument("path", required=False)
def check(path: str | None):
    """Check documentation quality against standards."""
    project = _resolve_project(path)
    wiki_dir = str(Path(project) / ".mini-wiki" / "wiki")

    if not Path(wiki_dir).exists():
        click.echo("No wiki found. Run 'mini-wiki init' first, then generate docs.")
        sys.exit(1)

    report = check_wiki_quality(wiki_dir)
    click.echo(f"Checked {report.total_docs} documents")
    click.echo(f"  Professional: {report.professional_count}")
    click.echo(f"  Standard: {report.standard_count}")
    click.echo(f"  Basic: {report.basic_count}")

    if report.summary_issues:
        click.echo("\nIssues:")
        for issue in report.summary_issues:
            click.echo(f"  - {issue}")


# --- changes ---


@main.command()
@click.argument("path", required=False)
def changes(path: str | None):
    """Detect file changes since last documentation generation."""
    project = _resolve_project(path)
    result = detect_changes(project)
    print_changes(result)


# --- plugins ---


@main.group()
def plugins():
    """Manage Mini-Wiki plugins."""


@plugins.command("list")
@click.argument("path", required=False)
def plugins_list(path: str | None):
    """List installed plugins."""
    project = _resolve_project(path)
    result = list_plugins(project)
    print_plugins(result)


@plugins.command("install")
@click.argument("source")
@click.argument("path", required=False)
def plugins_install(source: str, path: str | None):
    """Install a plugin from path, URL, or GitHub (owner/repo)."""
    project = _resolve_project(path)
    result = install_plugin(project, source)
    click.echo(result["message"])
    sys.exit(0 if result["success"] else 1)


@plugins.command("uninstall")
@click.argument("name")
@click.argument("path", required=False)
def plugins_uninstall(name: str, path: str | None):
    """Uninstall a plugin."""
    project = _resolve_project(path)
    result = uninstall_plugin(project, name)
    click.echo(result["message"])
    sys.exit(0 if result["success"] else 1)


@plugins.command("enable")
@click.argument("name")
@click.argument("path", required=False)
def plugins_enable(name: str, path: str | None):
    """Enable a plugin."""
    project = _resolve_project(path)
    result = enable_plugin(project, name, enabled=True)
    click.echo(result["message"])


@plugins.command("disable")
@click.argument("name")
@click.argument("path", required=False)
def plugins_disable(name: str, path: str | None):
    """Disable a plugin."""
    project = _resolve_project(path)
    result = enable_plugin(project, name, enabled=False)
    click.echo(result["message"])


@plugins.command("update")
@click.argument("name")
@click.argument("path", required=False)
def plugins_update(name: str, path: str | None):
    """Update a plugin to the latest version."""
    project = _resolve_project(path)
    result = update_plugin(project, name)
    click.echo(result["message"])
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
