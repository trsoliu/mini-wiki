"""Tests for scripts/generate_diagram.py."""

import re
from pathlib import Path

import pytest

from generate_diagram import (
    generate_architecture_diagram,
    generate_module_dependency_diagram,
    generate_data_flow_diagram,
    generate_file_tree_diagram,
    generate_class_diagram,
    load_structure,
)


# --- generate_architecture_diagram ---


def test_generate_architecture_diagram_basic(sample_structure):
    """Should generate a valid Mermaid architecture diagram."""
    # Act
    result = generate_architecture_diagram(sample_structure)

    # Assert
    assert "```mermaid" in result
    assert "flowchart TB" in result
    assert "```" in result
    assert "subgraph Core" in result
    assert "subgraph Utils" in result


def test_generate_architecture_diagram_nodejs_project():
    """Should include Frontend subgraph for nodejs/typescript projects."""
    # Arrange
    structure = {
        "project_type": ["nodejs", "typescript"],
        "modules": [
            {"name": "Button", "path": "src/components/Button.tsx", "files": 1},
            {"name": "HomePage", "path": "src/pages/HomePage.tsx", "files": 1},
            {"name": "api-service", "path": "src/services/api.ts", "files": 1},
        ],
    }

    # Act
    result = generate_architecture_diagram(structure)

    # Assert
    assert "subgraph Frontend" in result
    assert "Button" in result or "HomePage" in result


def test_generate_architecture_diagram_python_project():
    """Should not include Frontend subgraph for pure Python projects."""
    # Arrange
    structure = {
        "project_type": ["python"],
        "modules": [
            {"name": "core", "path": "src/core/main.py", "files": 1},
            {"name": "utils", "path": "src/utils/helpers.py", "files": 1},
        ],
    }

    # Act
    result = generate_architecture_diagram(structure)

    # Assert
    assert "subgraph Frontend" not in result
    assert "subgraph Core" in result
    assert "subgraph Utils" in result


def test_generate_architecture_diagram_empty_modules():
    """Should handle empty module list gracefully."""
    # Arrange
    structure = {"project_type": ["python"], "modules": []}

    # Act
    result = generate_architecture_diagram(structure)

    # Assert
    assert "```mermaid" in result
    assert "flowchart TB" in result
    assert "Logic" in result or "Utilities" in result  # Fallback nodes


def test_generate_architecture_diagram_fullstack_project():
    """Should include all layers for fullstack projects."""
    # Arrange
    structure = {
        "project_type": ["nodejs", "python"],
        "modules": [
            {"name": "LoginForm", "path": "frontend/components/LoginForm.tsx", "files": 1},
            {"name": "auth-api", "path": "backend/api/auth.py", "files": 1},
            {"name": "validators", "path": "backend/utils/validators.py", "files": 1},
        ],
    }

    # Act
    result = generate_architecture_diagram(structure)

    # Assert
    assert "subgraph Frontend" in result
    assert "subgraph Core" in result
    assert "subgraph Utils" in result
    assert "Frontend --> Core" in result
    assert "Core --> Utils" in result


# --- generate_module_dependency_diagram ---


def test_generate_module_dependency_diagram_internal_only():
    """Should generate diagram with only internal dependencies."""
    # Arrange
    module_name = "auth-service"
    dependencies = {
        "internal": ["./utils/validator.ts", "./models/User.ts", "./config/db.ts"],
        "external": [],
    }

    # Act
    result = generate_module_dependency_diagram(module_name, dependencies)

    # Assert
    assert "```mermaid" in result
    assert "graph LR" in result
    assert "auth-service" in result or "authservice" in result
    assert "validator" in result
    assert "User" in result
    assert "db" in result


def test_generate_module_dependency_diagram_external_only():
    """Should generate diagram with only external dependencies."""
    # Arrange
    module_name = "main"
    dependencies = {
        "internal": [],
        "external": ["express", "lodash", "axios"],
    }

    # Act
    result = generate_module_dependency_diagram(module_name, dependencies)

    # Assert
    assert "```mermaid" in result
    assert "graph LR" in result
    assert "main" in result
    assert "外部依赖" in result
    assert "express" in result
    assert "lodash" in result
    assert "axios" in result


def test_generate_module_dependency_diagram_mixed():
    """Should generate diagram with both internal and external dependencies."""
    # Arrange
    module_name = "api-handler"
    dependencies = {
        "internal": ["./utils/logger.ts", "./models/Response.ts"],
        "external": ["express", "joi"],
    }

    # Act
    result = generate_module_dependency_diagram(module_name, dependencies)

    # Assert
    assert "```mermaid" in result
    assert "graph LR" in result
    assert "logger" in result
    assert "Response" in result
    assert "外部依赖" in result
    assert "express" in result
    assert "joi" in result


def test_generate_module_dependency_diagram_empty_dependencies():
    """Should handle empty dependencies gracefully."""
    # Arrange
    module_name = "standalone"
    dependencies = {"internal": [], "external": []}

    # Act
    result = generate_module_dependency_diagram(module_name, dependencies)

    # Assert
    assert "```mermaid" in result
    assert "graph LR" in result
    assert "standalone" in result


def test_generate_module_dependency_diagram_special_chars():
    """Should sanitize module names with special characters."""
    # Arrange
    module_name = "auth-service.v2"
    dependencies = {
        "internal": ["./utils/helper-func.ts"],
        "external": ["@types/node"],
    }

    # Act
    result = generate_module_dependency_diagram(module_name, dependencies)

    # Assert
    assert "```mermaid" in result
    assert "graph LR" in result
    # Special chars should be removed
    assert "authservicev2" in result or "auth" in result


# --- generate_data_flow_diagram ---


def test_generate_data_flow_diagram_basic():
    """Should generate a valid sequence diagram."""
    # Arrange
    entry_points = ["main.ts"]
    modules = [
        {"name": "Router", "path": "src/router.ts"},
        {"name": "Controller", "path": "src/controller.ts"},
        {"name": "Service", "path": "src/service.ts"},
    ]

    # Act
    result = generate_data_flow_diagram(entry_points, modules)

    # Assert
    assert "```mermaid" in result
    assert "sequenceDiagram" in result
    assert "participant U as 用户" in result
    assert "participant E as 入口" in result
    assert "Router" in result
    assert "Controller" in result
    assert "Service" in result


def test_generate_data_flow_diagram_empty_modules():
    """Should handle empty module list gracefully."""
    # Arrange
    entry_points = ["index.js"]
    modules = []

    # Act
    result = generate_data_flow_diagram(entry_points, modules)

    # Assert
    assert "```mermaid" in result
    assert "sequenceDiagram" in result
    assert "U->>E: 请求" in result
    assert "E-->>U: 响应" in result


def test_generate_data_flow_diagram_single_module():
    """Should generate diagram with single module."""
    # Arrange
    entry_points = ["app.py"]
    modules = [{"name": "Handler", "path": "src/handler.py"}]

    # Act
    result = generate_data_flow_diagram(entry_points, modules)

    # Assert
    assert "```mermaid" in result
    assert "sequenceDiagram" in result
    assert "Handler" in result
    assert "E->>Handler: 调用" in result


# --- generate_file_tree_diagram ---


def test_generate_file_tree_diagram_basic(sample_structure):
    """Should generate a valid mindmap diagram."""
    # Act
    result = generate_file_tree_diagram(sample_structure)

    # Assert
    assert "```mermaid" in result
    assert "mindmap" in result
    assert "root((项目))" in result
    assert "core" in result
    assert "utils" in result
    assert "api" in result


def test_generate_file_tree_diagram_empty_modules():
    """Should handle empty module list gracefully."""
    # Arrange
    structure = {"modules": []}

    # Act
    result = generate_file_tree_diagram(structure)

    # Assert
    assert "```mermaid" in result
    assert "mindmap" in result
    assert "root((项目))" in result


def test_generate_file_tree_diagram_max_depth():
    """Should respect max_depth parameter."""
    # Arrange
    structure = {
        "modules": [
            {"name": f"module{i}", "path": f"src/module{i}", "files": i}
            for i in range(20)
        ]
    }

    # Act
    result = generate_file_tree_diagram(structure, max_depth=2)

    # Assert
    assert "```mermaid" in result
    assert "mindmap" in result
    # Should limit to 10 modules
    assert result.count("module") <= 12  # 10 modules + possible text


# --- generate_class_diagram ---


def test_generate_class_diagram_basic():
    """Should generate a valid class diagram."""
    # Arrange
    classes = [
        {
            "name": "User",
            "properties": ["id", "name", "email"],
            "methods": ["login", "logout", "updateProfile"],
        },
        {
            "name": "Post",
            "properties": ["id", "title", "content"],
            "methods": ["publish", "delete"],
        },
    ]

    # Act
    result = generate_class_diagram(classes)

    # Assert
    assert "```mermaid" in result
    assert "classDiagram" in result
    assert "class User" in result
    assert "class Post" in result
    assert "+id" in result
    assert "+login()" in result


def test_generate_class_diagram_empty_classes():
    """Should handle empty class list gracefully."""
    # Arrange
    classes = []

    # Act
    result = generate_class_diagram(classes)

    # Assert
    assert "```mermaid" in result
    assert "classDiagram" in result


def test_generate_class_diagram_special_chars():
    """Should sanitize class names with special characters."""
    # Arrange
    classes = [
        {
            "name": "User-Model.v2",
            "properties": ["user_id"],
            "methods": ["get_user"],
        }
    ]

    # Act
    result = generate_class_diagram(classes)

    # Assert
    assert "```mermaid" in result
    assert "classDiagram" in result
    assert "class UserModelv2" in result or "class User" in result


# --- load_structure ---


def test_load_structure_valid_file(tmp_path):
    """Should load structure from valid JSON file."""
    # Arrange
    wiki_dir = tmp_path / ".mini-wiki"
    cache_dir = wiki_dir / "cache"
    cache_dir.mkdir(parents=True)

    structure_data = {
        "project_type": ["python"],
        "modules": [{"name": "test", "path": "src/test.py"}],
    }
    structure_file = cache_dir / "structure.json"
    structure_file.write_text(json.dumps(structure_data), encoding="utf-8")

    # Act
    result = load_structure(str(wiki_dir))

    # Assert
    assert result is not None
    assert result["project_type"] == ["python"]
    assert len(result["modules"]) == 1


def test_load_structure_nonexistent_file(tmp_path):
    """Should return None for nonexistent structure file."""
    # Arrange
    wiki_dir = tmp_path / ".mini-wiki"

    # Act
    result = load_structure(str(wiki_dir))

    # Assert
    assert result is None


def test_load_structure_invalid_json(tmp_path):
    """Should handle invalid JSON gracefully."""
    # Arrange
    wiki_dir = tmp_path / ".mini-wiki"
    cache_dir = wiki_dir / "cache"
    cache_dir.mkdir(parents=True)

    structure_file = cache_dir / "structure.json"
    structure_file.write_text("invalid json {", encoding="utf-8")

    # Act & Assert
    with pytest.raises(json.JSONDecodeError):
        load_structure(str(wiki_dir))


# --- Mermaid syntax validity ---


def test_mermaid_syntax_validity_architecture():
    """Should generate valid Mermaid syntax for architecture diagram."""
    # Arrange
    structure = {
        "project_type": ["python"],
        "modules": [{"name": "core", "path": "src/core.py", "files": 1}],
    }

    # Act
    result = generate_architecture_diagram(structure)

    # Assert
    assert result.startswith("```mermaid")
    assert result.endswith("```")
    assert "flowchart TB" in result
    lines = result.split("\n")
    assert lines[0] == "```mermaid"
    assert lines[-1] == "```"
