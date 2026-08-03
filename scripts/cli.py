#!/usr/bin/env python3
"""
Mini-Wiki CLI — Generate professional project documentation with AI.

Usage:
    mini-wiki init [--force]
    mini-wiki analyze [PATH]
    mini-wiki build [PATH]
    mini-wiki check [PATH]
    mini-wiki changes [PATH]
    mini-wiki doctor [PATH]
    mini-wiki plugins list [PATH]
    mini-wiki plugins enable NAME [PATH]
    mini-wiki plugins disable NAME [PATH]
    mini-wiki plugins install SOURCE [PATH]
    mini-wiki plugins uninstall NAME [PATH]
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from analyze_project import analyze_project, print_analysis
from check_quality import check_wiki_quality
from detect_changes import detect_changes, print_changes
from init_wiki import init_mini_wiki, print_result
from mini_wiki_core.builder import BuildOptions, TransactionError, build_project
from mini_wiki_core.config import ConfigError, load_config
from mini_wiki_core.doctor import doctor_project
from mini_wiki_core.migration import MigrationError, apply_migration, plan_migration
from mini_wiki_core.validation import validate_vault
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


# --- build ---


@main.command()
@click.option("--full", is_flag=True, help="Rebuild every managed document.")
@click.option("--dry-run", is_flag=True, help="Preview changes without writing files.")
@click.option("--json", "json_output", is_flag=True, help="Print a machine-readable result.")
@click.argument("path", required=False)
def build(full: bool, dry_run: bool, json_output: bool, path: str | None):
    """Build the deterministic Markdown Vault and Manifest."""
    project = _resolve_project(path)
    try:
        result = build_project(project, BuildOptions(full=full, dry_run=dry_run))
    except (ConfigError, TransactionError) as exc:
        if json_output:
            click.echo(
                json.dumps(
                    {
                        "success": False,
                        "created": [],
                        "modified": [],
                        "archived": [],
                        "warnings": [],
                        "errors": [str(exc)],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        else:
            click.echo(str(exc))
        raise click.exceptions.Exit(1) from exc

    if json_output:
        click.echo(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
    else:
        mode = "Dry run" if dry_run else "Build"
        click.echo(f"{mode} complete: {len(result.changed)} changed, {len(result.warnings)} warnings")


# --- check ---


@main.command()
@click.option("--strict", is_flag=True, help="Validate structural knowledge-network integrity.")
@click.option("--json", "json_output", is_flag=True, help="Print a machine-readable result.")
@click.argument("path", required=False)
def check(strict: bool, json_output: bool, path: str | None):
    """Check documentation quality against standards."""
    project = _resolve_project(path)
    try:
        config = load_config(project)
    except ConfigError:
        click.echo("No wiki found. Run 'mini-wiki init' first, then generate docs.")
        raise click.exceptions.Exit(1) from None

    if not config.vault_dir.exists():
        click.echo("No wiki found. Run 'mini-wiki init' first, then generate docs.")
        raise click.exceptions.Exit(1)

    if strict:
        structural = validate_vault(config)
        if json_output:
            click.echo(json.dumps(structural.to_dict(), ensure_ascii=False, sort_keys=True))
        else:
            click.echo(
                f"Validated {structural.documents} documents: "
                f"{sum(issue.severity == 'error' for issue in structural.issues)} errors, "
                f"{sum(issue.severity == 'warning' for issue in structural.issues)} warnings"
            )
            for structural_issue in structural.issues:
                click.echo(
                    f"  [{structural_issue.severity}] {structural_issue.code} "
                    f"{structural_issue.path}: {structural_issue.message}"
                )
        if not structural.ok:
            raise click.exceptions.Exit(1)
        return

    report = check_wiki_quality(str(config.vault_dir))
    click.echo(f"Checked {report.total_docs} documents")
    click.echo(f"  Professional: {report.professional_count}")
    click.echo(f"  Standard: {report.standard_count}")
    click.echo(f"  Basic: {report.basic_count}")

    if report.summary_issues:
        click.echo("\nIssues:")
        for summary_issue in report.summary_issues:
            click.echo(f"  - {summary_issue}")


# --- doctor ---


@main.command()
@click.option("--json", "json_output", is_flag=True, help="Print a machine-readable result.")
@click.argument("path", required=False)
def doctor(json_output: bool, path: str | None):
    """Diagnose Mini-Wiki project and optional integration readiness."""
    report = doctor_project(_resolve_project(path))
    if json_output:
        click.echo(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    else:
        for finding in report.findings:
            click.echo(f"[{finding.severity}] {finding.code}: {finding.message}")
            if finding.remediation:
                click.echo(f"  {finding.remediation}")
    if not report.ok:
        raise click.exceptions.Exit(1)


# --- migrate ---


@main.command()
@click.option("--apply", "apply_changes", is_flag=True, help="Apply the previewed copy-only migration.")
@click.option("--adopt", is_flag=True, help="Wrap copied legacy Markdown in managed ownership regions.")
@click.option("--json", "json_output", is_flag=True, help="Print a machine-readable result.")
@click.argument("path", required=False)
def migrate(apply_changes: bool, adopt: bool, json_output: bool, path: str | None):
    """Preview or apply a recoverable v2-to-v3 Vault migration."""
    plan = plan_migration(_resolve_project(path))
    if not apply_changes:
        if json_output:
            click.echo(json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True))
        else:
            state = "applicable" if plan.applicable else "not applicable"
            click.echo(f"Migration preview: {state} ({', '.join(plan.reasons)})")
        return
    try:
        result = apply_migration(plan, adopt=adopt)
    except MigrationError as exc:
        if json_output:
            click.echo(json.dumps({"success": False, "errors": [str(exc)]}, ensure_ascii=False, sort_keys=True))
        else:
            click.echo(str(exc))
        raise click.exceptions.Exit(1) from exc
    if json_output:
        click.echo(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
    else:
        click.echo(f"Migration complete: {len(result.copied)} files copied; backup: {result.backup}")


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
