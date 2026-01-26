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
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
import re


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
        # Handle URL
        if source.startswith('http://') or source.startswith('https://'):
            # Download to temp file
            temp_zip = plugins_dir / '_temp.zip'
            urllib.request.urlretrieve(source, temp_zip)
            source = str(temp_zip)
        
        source_path = Path(source)
        
        # Handle zip file
        if source_path.suffix == '.zip' or source_path.suffix == '.skill':
            with zipfile.ZipFile(source_path, 'r') as zf:
                # Extract to temp directory
                temp_dir = plugins_dir / '_temp_extract'
                zf.extractall(temp_dir)
                
                # Find the plugin directory
                for item in temp_dir.iterdir():
                    if item.is_dir():
                        source_path = item
                        break
                    elif item.name == 'PLUGIN.md':
                        source_path = temp_dir
                        break
        
        # Parse manifest
        manifest = parse_plugin_manifest(source_path)
        if not manifest:
            result['message'] = 'Invalid plugin: PLUGIN.md not found or invalid'
            return result
        
        ext_name = manifest.get('name', source_path.name)
        target_dir = plugins_dir / ext_name
        
        # Copy plugin
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source_path, target_dir)
        
        # Update registry
        registry = load_registry(project_root)
        plugins = registry.get('plugins', [])
        
        # Remove existing entry if exists
        plugins = [e for e in plugins if e.get('name') != ext_name]
        
        # Add new entry
        plugins.append({
            'name': ext_name,
            'enabled': True,
            'priority': len(plugins) * 10 + 10
        })
        
        registry['plugins'] = plugins
        save_registry(project_root, registry)
        
        # Cleanup
        temp_zip = plugins_dir / '_temp.zip'
        temp_dir = plugins_dir / '_temp_extract'
        if temp_zip.exists():
            temp_zip.unlink()
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        
        result['success'] = True
        result['name'] = ext_name
        result['message'] = f'Plugin "{ext_name}" installed successfully'
        
    except Exception as e:
        result['message'] = f'Installation failed: {str(e)}'
    
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
        print("  python plugin_manager.py enable <name> [project_path]")
        print("  python plugin_manager.py disable <name> [project_path]")
        print("  python plugin_manager.py uninstall <name> [project_path]")
        sys.exit(1)
    
    command = sys.argv[1]
    project_path = sys.argv[-1] if len(sys.argv) > 2 and not sys.argv[-1].startswith('-') else os.getcwd()
    
    if command == 'list':
        plugins = list_plugins(project_path)
        print_plugins(plugins)
    
    elif command == 'install':
        if len(sys.argv) < 3:
            print("Error: source path or URL required")
            sys.exit(1)
        source = sys.argv[2]
        result = install_plugin(project_path, source)
        print(result['message'])
        sys.exit(0 if result['success'] else 1)
    
    elif command == 'enable':
        if len(sys.argv) < 3:
            print("Error: plugin name required")
            sys.exit(1)
        name = sys.argv[2]
        result = enable_plugin(project_path, name, True)
        print(result['message'])
    
    elif command == 'disable':
        if len(sys.argv) < 3:
            print("Error: plugin name required")
            sys.exit(1)
        name = sys.argv[2]
        result = enable_plugin(project_path, name, False)
        print(result['message'])
    
    elif command == 'uninstall':
        if len(sys.argv) < 3:
            print("Error: plugin name required")
            sys.exit(1)
        name = sys.argv[2]
        result = uninstall_plugin(project_path, name)
        print(result['message'])
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
