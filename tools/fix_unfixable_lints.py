#!/usr/bin/env python3
"""
Fix linting errors that ruff --fix cannot automatically fix.

This script uses intelligent pattern matching and heuristics to fix common issues like:
- Quote consistency
- Complex import ordering
- Unused imports that require context
- Other fixable but not auto-fixable issues

Note: GitHub Copilot doesn't have a public API for programmatic access from GitHub Actions,
so we use heuristic-based fixes that intelligently handle common patterns.
"""

import re
import subprocess
import sys
from pathlib import Path


def get_unfixable_errors() -> list[tuple[str, str, int, str]]:
    """Get list of errors that ruff cannot auto-fix."""
    # First run with --fix to get auto-fixable ones fixed
    subprocess.run(["ruff", "check", "--fix", "."], capture_output=True)

    # Now check for remaining errors
    result = subprocess.run(
        ["ruff", "check", ".", "--output-format", "json"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return []

    errors = []
    # Parse JSON output
    try:
        import json

        data = json.loads(result.stdout)
        for violation in data.get("violations", []):
            code = violation.get("code", "")
            # Get errors that don't have a fix or have fix.available = false
            fix_info = violation.get("fix", {})
            if not fix_info or not fix_info.get("available", True):
                errors.append(
                    (
                        violation.get("filename", ""),
                        code,
                        violation.get("location", {}).get("row", 0),
                        violation.get("message", ""),
                    )
                )
    except (json.JSONDecodeError, KeyError, ValueError):
        # Fallback: parse text output
        result_text = subprocess.run(
            ["ruff", "check", "."],
            capture_output=True,
            text=True,
        )
        for line in result_text.stdout.split("\n"):
            if ":" in line and any(code in line for code in ["Q", "F401", "I", "UP", "B"]):
                # Parse format: path:line:col: code message
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    code_part = parts[3].strip().split()[0] if parts[3].strip() else ""
                    errors.append(
                        (parts[0], code_part, int(parts[1]), parts[3] if len(parts) > 3 else "")
                    )

    return errors


def fix_quote_consistency(filepath: Path) -> bool:
    """Fix quote consistency issues (single vs double quotes)."""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Use ruff's quote fixer if available, otherwise use heuristics
        # Try ruff check --select Q --fix first
        result = subprocess.run(
            ["ruff", "check", "--select", "Q", "--fix", str(filepath)],
            capture_output=True,
        )

        if result.returncode == 0:
            # Check if file was modified
            with open(filepath, encoding="utf-8") as f:
                new_content = f.read()
            if new_content != original_content:
                return True

        # Fallback: manual fixing for simple cases
        # Standardize to double quotes (PEP 8 style)
        # But preserve in docstrings and comments
        lines = content.split("\n")
        fixed_lines = []
        in_triple_quote = False

        for line in lines:
            # Track triple quotes
            if '"""' in line:
                in_triple_quote = not in_triple_quote
                fixed_lines.append(line)
                continue
            if "'''" in line:
                in_triple_quote = not in_triple_quote
                fixed_lines.append(line)
                continue

            if in_triple_quote:
                fixed_lines.append(line)
                continue

            # Simple quote replacement for string literals
            # Replace single quotes with double quotes when safe
            if "'" in line:
                # Only replace if it's clearly a string literal
                line = re.sub(r"(\W)'([^']*)'(\W)", r'\1"\2"\3', line)
                line = re.sub(r"^'([^']*)'(\W)", r'"\1"\2', line)

            fixed_lines.append(line)

        new_content = "\n".join(fixed_lines)

        if new_content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True
    except Exception as e:
        print(f"Error fixing quotes in {filepath}: {e}", file=sys.stderr)

    return False


def fix_unused_imports(filepath: Path, line_num: int) -> bool:
    """Remove unused imports."""
    try:
        with open(filepath, encoding="utf-8") as f:
            lines = f.readlines()

        if line_num > len(lines):
            return False

        # Get the import line
        import_line = lines[line_num - 1]

        # Check if it's actually unused (simple heuristic)
        import_name = None
        if "import " in import_line:
            # Extract imported name
            match = re.search(r"import\s+(\w+)", import_line)
            if match:
                import_name = match.group(1)

        if import_name:
            # Check if import_name is used elsewhere in the file
            file_content = "".join(lines)
            # Count occurrences (excluding the import line itself)
            occurrences = len(re.findall(rf"\b{import_name}\b", file_content))
            if occurrences <= 1:  # Only in the import line
                # Remove the import line
                lines.pop(line_num - 1)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                return True
    except Exception as e:
        print(f"Error fixing unused import in {filepath}: {e}", file=sys.stderr)

    return False


def fix_import_ordering(filepath: Path) -> bool:
    """Fix import ordering issues."""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Split into sections
        lines = content.split("\n")
        imports = []
        other_lines = []
        in_imports = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("from __future__"):
                imports.append((i, line, 0))  # Priority 0: future imports
                in_imports = True
            elif stripped.startswith("import ") or stripped.startswith("from "):
                # Determine priority
                if "typing" in stripped:
                    priority = 1  # Standard library
                elif any(x in stripped for x in ["numpy", "PyQt", "pytest"]):
                    priority = 2  # Third-party
                else:
                    priority = 3  # Local imports
                imports.append((i, line, priority))
                in_imports = True
            elif stripped == "" and in_imports:
                # Blank line ends import section
                imports.append((i, line, -1))
                in_imports = False
            elif not in_imports:
                other_lines.append((i, line))

        # Sort imports by priority, then alphabetically
        import_section = []
        current_group = []
        current_priority = None

        for idx, line, priority in imports:
            if priority == -1:  # Blank line
                if current_group:
                    import_section.extend(sorted(current_group, key=lambda x: x[1]))
                    current_group = []
                import_section.append((idx, line))
            else:
                if current_priority is not None and priority != current_priority:
                    if current_group:
                        import_section.extend(sorted(current_group, key=lambda x: x[1]))
                    current_group = []
                current_priority = priority
                current_group.append((idx, line))

        if current_group:
            import_section.extend(sorted(current_group, key=lambda x: x[1]))

        # Reconstruct file
        new_lines = [""] * len(lines)
        for idx, line in import_section:
            new_lines[idx] = line
        for idx, line in other_lines:
            new_lines[idx] = line

        new_content = "\n".join(new_lines)
        if new_content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True
    except Exception as e:
        print(f"Error fixing import ordering in {filepath}: {e}", file=sys.stderr)

    return False


def main():
    """Main function to fix unfixable linting errors."""
    print("🔍 Checking for unfixable linting errors...")

    # First, try to get unfixable errors
    errors = get_unfixable_errors()

    if not errors:
        print("✅ No unfixable errors found!")
        return 0

    print(f"Found {len(errors)} potentially unfixable errors")

    fixed_count = 0
    files_fixed = set()

    for filepath_str, code, line_num, _message in errors:
        filepath = Path(filepath_str)

        if not filepath.exists():
            continue

        # Fix based on error code
        fixed = False

        if code.startswith("Q"):  # Quote consistency
            if filepath not in files_fixed:
                fixed = fix_quote_consistency(filepath)
                files_fixed.add(filepath)
        elif code == "F401":  # Unused import
            fixed = fix_unused_imports(filepath, line_num)
        elif code.startswith("I"):  # Import ordering
            if filepath not in files_fixed:
                # Try ruff's isort fixer first
                result = subprocess.run(
                    ["ruff", "check", "--select", "I", "--fix", str(filepath)],
                    capture_output=True,
                )
                if result.returncode == 0:
                    fixed = True
                else:
                    fixed = fix_import_ordering(filepath)
                files_fixed.add(filepath)

        if fixed:
            fixed_count += 1
            print(f"✅ Fixed {code} in {filepath}")

    if fixed_count > 0:
        print(f"\n✨ Fixed {fixed_count} issues!")
        return 0
    else:
        print("\n⚠️  Could not automatically fix remaining issues.")
        print("These may require manual review.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
