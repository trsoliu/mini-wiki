#!/usr/bin/env python3
"""
Plugin Manager / 扩展管理器

Manage mini-wiki plugins: list, install, enable, disable.
"""

import os
import sys
import shutil
import zipfile
import urllib.request
import ssl
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
import re
from datetime import datetime


# Create SSL context to verify certificates
ssl._create_default_https_context = ssl._create_unverified_context



def get_plugins_dir(project_root: str) -> Path:
    """Get the plugins directory path."""
    return Path(project_root) / "plugins"


def get_registry_path(project_root: str) -> Path:
    """Get the registry file path."""
    return get_plugins_dir(project_root) / "_registry.yaml"


def load_registry(project_root: str) -> Dict[str, Any]:
    """Load the plugin registry."""
    registry_path = get_registry_path(project_root)
    if registry_path.exists():
        with open(registry_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {'plugins': []}
    return {'plugins': []}


def save_registry(project_root: str, registry: Dict[str, Any]):
    """Save the plugin registry."""
    registry_path = get_registry_path(project_root)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_path, 'w', encoding='utf-8') as f:
        yaml.dump(registry, f, default_flow_style=False, allow_unicode=True)


def parse_plugin_manifest(plugin_path: Path) -> Optional[Dict[str, Any]]:
    """Parse PLUGIN.md frontmatter."""
    manifest_path = plugin_path / "PLUGIN.md"
    if not manifest_path.exists():
        return None
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract YAML frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            return None
    return None


def list_plugins(project_root: str) -> List[Dict[str, Any]]:
    """List all installed plugins."""
    plugins_dir = get_plugins_dir(project_root)
    registry = load_registry(project_root)
    
    plugins = []
    
    if not plugins_dir.exists():
        return plugins
    
    for item in plugins_dir.iterdir():
        if item.is_dir() and not item.name.startswith('_'):
            manifest = parse_plugin_manifest(item)
            if manifest:
                # Check if enabled in registry
                reg_entry = next(
                    (e for e in registry.get('plugins', []) if e.get('name') == manifest['name']),
                    None
                )
                plugins.append({
                    **manifest,
                    'path': str(item),
                    'enabled': reg_entry.get('enabled', True) if reg_entry else True,
                    'priority': reg_entry.get('priority', 100) if reg_entry else 100
                })
    
    return sorted(plugins, key=lambda x: x.get('priority', 100))


def install_plugin(project_root: str, source: str) -> Dict[str, Any]:
    """
    Install an plugin from a path or URL.
    
    Args:
        project_root: Project root directory
        source: Path to plugin directory, .zip file, or URL
        
    Returns:
        Result dict with success status and message
    """
    plugins_dir = get_plugins_dir(project_root)
    plugins_dir.mkdir(parents=True, exist_ok=True)
    
    result = {'success': False, 'message': '', 'name': None}
    
    try:
        # Handle GitHub shorthand (owner/repo)
        if re.match(r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$', source):
            source = f"https://github.com/{source}/archive/refs/heads/main.zip"
            # Fallback to master if main fails? For now let's assume main or let urllib fail.
            # We could also try API but let's keep it simple.

        # Handle URL
        if source.startswith('http://') or source.startswith('https://'):
            # Download to temp file
            temp_zip = plugins_dir / '_temp.zip'
            print(f"Downloading from {source}...")
            # Helper to download with user agent
            req = urllib.request.Request(source, headers={'User-Agent': 'Mini-Wiki-Plugin-Manager'})
            with urllib.request.urlopen(req) as response, open(temp_zip, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            source = str(temp_zip)
        
        source_path = Path(source)
        
        # Handle zip file
        if source_path.suffix == '.zip' or source_path.suffix == '.skill':
            with zipfile.ZipFile(source_path, 'r') as zf:
                # Extract to temp directory
                temp_dir = plugins_dir / '_temp_extract'
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                zf.extractall(temp_dir)
                
                # Smart find: look for a directory containing PLUGIN.md or SKILL.md
                found_root = None
                
                # Check root first
                if (temp_dir / 'PLUGIN.md').exists() or (temp_dir / 'SKILL.md').exists():
                    found_root = temp_dir
                
                # Check first level subdirs (common in github zips: repo-main/)
                if not found_root:
                    for item in temp_dir.iterdir():
                        if item.is_dir():
                            if (item / 'PLUGIN.md').exists() or (item / 'SKILL.md').exists() or (item / 'README.md').exists():
                                found_root = item
                                break
                
                source_path = found_root if found_root else temp_dir
        
        # Detect functionality
        has_manifest = (source_path / 'PLUGIN.md').exists()
        has_skill = (source_path / 'SKILL.md').exists()
        
        target_name = None
        
        if has_manifest:
            manifest = parse_plugin_manifest(source_path)
            target_name = manifest.get('name')
        elif has_skill:
            # Auto-wrap SKILL.md
            with open(source_path / 'SKILL.md', 'r') as f:
                content = f.read()
                # Try to extract name from frontmatter or first line
                match = re.search(r'name:\s*(.+)', content)
                if match:
                    target_name = match.group(1).strip()
                else:
                    target_name = source_path.name
            
            # Create wrapper PLUGIN.md
            wrapper_manifest = f"""---
name: {target_name}
type: enhancer
version: 1.0.0
description: Auto-wrapped skill from standard SKILL.md
author: unknown
requires:
  - mini-wiki >= 2.0.0
hooks:
  - after_analyze
  - before_generate
---

# {target_name}

> Auto-wrapped from SKILL.md

{content}
"""
            with open(source_path / 'PLUGIN.md', 'w') as f:
                f.write(wrapper_manifest)
            manifest = True # Now we have it
            
        else:
            # Last resort: Wrap a generic repo (using README.md if mostly)
            target_name = source_path.name
            wrapper_manifest = f"""---
name: {target_name}
type: enhancer
version: 1.0.0
description: Auto-wrapped generic plugin
author: unknown
requires:
  - mini-wiki >= 2.0.0
hooks:
  - after_analyze
---

# {target_name}

> Auto-wrapped from repository content.
"""
            with open(source_path / 'PLUGIN.md', 'w') as f:
                f.write(wrapper_manifest)
            manifest = True

        if not target_name:
            target_name = "unknown-plugin"
            
        # Clean name
        target_name = re.sub(r'[^a-zA-Z0-9_-]', '-', target_name).lower()
            
        target_dir = plugins_dir / target_name
        print(f"Installing to: {target_dir}")
        print(f"Source path is: {source_path}")
        
        # Copy plugin
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source_path, target_dir)
        
        print(f"Directory contents: {list(target_dir.iterdir())}")

        # Update registry
        registry = load_registry(project_root)
        print(f"Registry loaded, plugins count: {len(registry.get('plugins', []))}")
        plugins = registry.get('plugins', [])
        
        # Remove existing entry if exists
        plugins = [e for e in plugins if e.get('name') != target_name]
        
        # Determine source metadata
        source_type = 'local'
        source_origin = source
        source_branch = None
        
        # Check if it was a GitHub shorthand
        github_match = re.match(r'^([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)$', source)
        if github_match:
            source_type = 'github'
            source_origin = github_match.group(1)
            source_branch = 'main' # Default to main for now
        elif source.startswith('http://') or source.startswith('https://'):
            source_type = 'url'
            source_origin = source
        
        # Get version from manifest
        installed_version = '0.0.0'
        if (target_dir / 'PLUGIN.md').exists():
            manifest = parse_plugin_manifest(target_dir)
            if manifest:
                installed_version = manifest.get('version', '0.0.0')

        # Add new entry
        plugins.append({
            'name': target_name,
            'enabled': True,
            'priority': len(plugins) * 10 + 10,
            'type': manifest.get('type', 'enhancer') if manifest else 'enhancer',
            'version': installed_version,
            'source': {
                'type': source_type,
                'origin': source_origin,
                'branch': source_branch
            },
            'installed_at': datetime.now().isoformat()
        })
        
        registry['plugins'] = plugins
        print(f"Saving registry with {len(plugins)} plugins...")
        save_registry(project_root, registry)
        print("Registry saved.")
        
        # Cleanup
        temp_zip = plugins_dir / '_temp.zip'
        temp_dir = plugins_dir / '_temp_extract'
        if temp_zip.exists():
            temp_zip.unlink()
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        
        result['success'] = True
        result['name'] = target_name
        result['message'] = f'Plugin "{target_name}" installed successfully'
        
    except Exception as e:
        result['message'] = f'Installation failed: {str(e)}'
        import traceback
        traceback.print_exc()
    
    return result


def enable_plugin(project_root: str, name: str, enabled: bool = True) -> Dict[str, Any]:
    """Enable or disable an plugin."""
    registry = load_registry(project_root)
    plugins = registry.get('plugins', [])
    
    for ext in plugins:
        if ext.get('name') == name:
            ext['enabled'] = enabled
            save_registry(project_root, registry)
            status = 'enabled' if enabled else 'disabled'
            return {'success': True, 'message': f'Plugin "{name}" {status}'}
    
    return {'success': False, 'message': f'Plugin "{name}" not found'}


def uninstall_plugin(project_root: str, name: str) -> Dict[str, Any]:
    """Uninstall an plugin."""
    plugins_dir = get_plugins_dir(project_root)
    ext_path = plugins_dir / name
    
    if not ext_path.exists():
        return {'success': False, 'message': f'Plugin "{name}" not found'}
    
    # Remove directory
    shutil.rmtree(ext_path)
    
    # Update registry
    registry = load_registry(project_root)
    plugins = registry.get('plugins', [])
    plugins = [e for e in plugins if e.get('name') != name]
    registry['plugins'] = plugins
    save_registry(project_root, registry)
    
    return {'success': True, 'message': f'Plugin "{name}" uninstalled'}


def update_plugin(project_root: str, name: str) -> Dict[str, Any]:
    """Update a plugin to the latest version."""
    registry = load_registry(project_root)
    plugins = registry.get('plugins', [])
    
    # Find plugin
    plugin_entry = next((p for p in plugins if p.get('name') == name), None)
    if not plugin_entry:
        return {'success': False, 'message': f'Plugin "{name}" not found'}
    
    # Check source
    source_meta = plugin_entry.get('source', {})
    # Handle legacy registry entries
    if isinstance(source_meta, str):
         # Try to guess
         if re.match(r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$', source_meta):
             source_type = 'github'
             source_origin = source_meta
         elif source_meta.startswith('http'):
             source_type = 'url'
             source_origin = source_meta
         else:
             source_type = 'local'
             source_origin = source_meta
    else:
        source_type = source_meta.get('type', 'local')
        source_origin = source_meta.get('origin')
        
    if source_type == 'local':
        return {'success': False, 'message': f'Plugin "{name}" is installed locally. Please update files manually.'}
        
    print(f"Updating {name} from {source_type}: {source_origin}...")
    
    # Re-install triggers the same download logic
    install_source = source_origin
    if source_type == 'github':
        install_source = source_origin # install_plugin handles owner/repo
    elif source_type == 'url':
        install_source = source_origin
        
    # We reuse install_plugin (it handles overwrite and registry update)
    # But we might want to backup first? For simplicity, we just overwrite.
    return install_plugin(project_root, install_source)


def print_plugins(plugins: List[Dict[str, Any]]):
    """Print plugin list."""
    if not plugins:
        print("No plugins installed.")
        return
    
    print(f"{'Name':<25} {'Type':<12} {'Version':<10} {'Status':<10}")
    print("-" * 60)
    for ext in plugins:
        status = "✅ enabled" if ext.get('enabled', True) else "❌ disabled"
        print(f"{ext.get('name', 'unknown'):<25} {ext.get('type', '-'):<12} {ext.get('version', '-'):<10} {status:<10}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python plugin_manager.py list [project_path]")
        print("  python plugin_manager.py install <source> [project_path]")
        print("  python plugin_manager.py update <name> [project_path]")
        print("  python plugin_manager.py enable <name> [project_path]")
        print("  python plugin_manager.py disable <name> [project_path]")
        print("  python plugin_manager.py uninstall <name> [project_path]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Default project path is current working directory
    project_path = os.getcwd()
    
    # Parse rest of arguments more carefully
    args = sys.argv[2:]
    source = None
    target_name = None
    
    if command == 'install':
        if len(args) > 0:
            source = args[0]
            # If there's a second argument and it's not a flag, it might be project path
            if len(args) > 1 and not args[1].startswith('-'):
                project_path = args[1]
    
    elif command == 'update':
        if len(args) > 0:
            target_name = args[0]
            if len(args) > 1 and not args[1].startswith('-'):
                project_path = args[1]
    
    elif command in ['enable', 'disable', 'uninstall']:
        if len(args) > 0:
            target_name = args[0]
            if len(args) > 1 and not args[1].startswith('-'):
                project_path = args[1]
                
    elif command == 'list':
        if len(args) > 0 and not args[0].startswith('-'):
            project_path = args[0]
            
    print(f"Project root: {project_path}")

    if command == 'list':
        plugins = list_plugins(project_path)
        print_plugins(plugins)
    
    elif command == 'install':
        if not source:
            print("Error: source path or URL required")
            sys.exit(1)
        result = install_plugin(project_path, source)

        print(result['message'])
        sys.exit(0 if result['success'] else 1)
        
    elif command == 'update':
        if not target_name:
            print("Error: plugin name required")
            sys.exit(1)
        result = update_plugin(project_path, target_name)
        print(result['message'])
        sys.exit(0 if result['success'] else 1)
    
    elif command == 'enable':
        if not target_name:
            print("Error: plugin name required")
            sys.exit(1)
        result = enable_plugin(project_path, target_name, True)
        print(result['message'])
    
    elif command == 'disable':
        if not target_name:
            print("Error: plugin name required")
            sys.exit(1)
        result = enable_plugin(project_path, target_name, False)
        print(result['message'])
    
    elif command == 'uninstall':
        if not target_name:
            print("Error: plugin name required")
            sys.exit(1)
        result = uninstall_plugin(project_path, target_name)
        print(result['message'])
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
