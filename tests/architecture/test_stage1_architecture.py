"""
Tests for HTDAM Stage 1: Architecture Compliance

Verify "State lives in hooks; App orchestrates" principle.
"""

import pytest
import os
import re
from pathlib import Path


class TestArchitectureCompliance:
    """Test architecture separation and compliance."""
    
    @pytest.fixture
    def repo_root(self):
        """Get repository root directory."""
        # From tests/architecture/ → tests/ → (repo root)
        return Path(__file__).parent.parent.parent
    
    def test_domain_layer_has_no_logging(self, repo_root):
        """Domain layer must have ZERO logging imports."""
        domain_dir = repo_root / "src" / "domain" / "htdam"
        
        violations = []
        for py_file in domain_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            
            content = py_file.read_text()
            if "import logging" in content or "from logging import" in content:
                violations.append(str(py_file.relative_to(repo_root)))
        
        assert len(violations) == 0, (
            f"Domain layer must have NO logging imports. "
            f"Found in: {violations}"
        )
    
    def test_hooks_layer_has_logging(self, repo_root):
        """Hooks layer must have logging imports."""
        hooks_dir = repo_root / "src" / "hooks"
        
        stage1_hook = hooks_dir / "useStage1Verifier.py"
        assert stage1_hook.exists(), "useStage1Verifier.py must exist"
        
        content = stage1_hook.read_text()
        assert "import logging" in content, (
            "useStage1Verifier.py must import logging for side effects"
        )
    
    def test_constants_file_is_pure(self, repo_root):
        """Constants file must be pure (no code execution)."""
        constants_file = repo_root / "src" / "domain" / "htdam" / "constants.py"
        assert constants_file.exists(), "constants.py must exist"
        
        content = constants_file.read_text()
        
        # Should not have logger
        assert "logging" not in content.lower(), (
            "constants.py must not use logging"
        )
        
        # Should not have if __name__
        assert "if __name__" not in content, (
            "constants.py must not execute code"
        )
        
        # Should have type hints
        assert "from typing import" in content or "import" in content, (
            "constants.py should use type hints"
        )
    
    def test_domain_functions_are_pure(self, repo_root):
        """Domain functions must not call hooks or have side effects."""
        domain_dir = repo_root / "src" / "domain" / "htdam" / "stage1"
        
        violations = []
        for py_file in domain_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            
            content = py_file.read_text()
            
            # Check for hook imports (hooks should NOT be imported in domain)
            if "from src.hooks" in content or "import src.hooks" in content:
                violations.append((
                    str(py_file.relative_to(repo_root)),
                    "imports hooks (violates separation)"
                ))
            
            # Check for logger usage
            if "logger." in content:
                violations.append((
                    str(py_file.relative_to(repo_root)),
                    "uses logger (side effect)"
                ))
            
            # Check for file I/O
            if re.search(r'\bopen\(', content):
                violations.append((
                    str(py_file.relative_to(repo_root)),
                    "uses open() (side effect)"
                ))
        
        assert len(violations) == 0, (
            f"Domain functions must be pure. Violations:\n" +
            "\n".join(f"  {file}: {reason}" for file, reason in violations)
        )
    
    def test_hook_calls_domain_not_vice_versa(self, repo_root):
        """Hooks must call domain functions, not vice versa."""
        # Check hook imports domain
        hook_file = repo_root / "src" / "hooks" / "useStage1Verifier.py"
        hook_content = hook_file.read_text()
        
        assert "from src.domain.htdam.stage1" in hook_content, (
            "Hook must import from domain layer"
        )
        
        # Check domain does NOT import hooks
        domain_dir = repo_root / "src" / "domain" / "htdam"
        
        for py_file in domain_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            
            content = py_file.read_text()
            assert "from src.hooks" not in content, (
                f"{py_file.relative_to(repo_root)} must not import hooks"
            )
            assert "import src.hooks" not in content, (
                f"{py_file.relative_to(repo_root)} must not import hooks"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
