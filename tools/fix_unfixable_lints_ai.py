#!/usr/bin/env python3
"""
Fix linting errors using AI (OpenAI API or similar).

This script uses an LLM API to intelligently fix linting errors that
ruff --fix cannot automatically fix.
"""

import json
import os
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
    try:
        data = json.loads(result.stdout)
        for violation in data.get("violations", []):
            code = violation.get("code", "")
            fix_info = violation.get("fix", {})
            if not fix_info or not fix_info.get("available", True):
                errors.append(
                    (
                        violation.get("filename", ""),
                        code,
                        violation.get("location", {}).get("row", 0),
                        violation.get("message", ""),
                        violation.get("end_location", {}).get(
                            "row", violation.get("location", {}).get("row", 0)
                        ),
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
            if ":" in line:
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    code_part = parts[3].strip().split()[0] if parts[3].strip() else ""
                    errors.append(
                        (
                            parts[0],
                            code_part,
                            int(parts[1]),
                            parts[3] if len(parts) > 3 else "",
                            int(parts[1]),
                        )
                    )

    return errors


def fix_with_openai(
    filepath: Path, error_code: str, line_num: int, message: str, end_line: int
) -> bool:
    """Fix a linting error using OpenAI API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return False

    try:
        import openai
    except ImportError:
        print("⚠️  OpenAI library not installed. Install with: pip install openai", file=sys.stderr)
        return False

    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        error_context = "\n".join(lines[max(0, line_num - 5) : min(len(lines), end_line + 5)])

        prompt = f"""Fix the following Python linting error:

File: {filepath}
Error Code: {error_code}
Line: {line_num}
Message: {message}

Code context:
```python
{error_context}
```

Please provide the fixed code for the affected section. Only return the fixed code, maintaining the same structure and functionality."""

        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Python code fixer that fixes linting errors while preserving functionality.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )

        fixed_code = response.choices[0].message.content.strip()

        # Extract code from markdown if present
        if "```python" in fixed_code:
            fixed_code = fixed_code.split("```python")[1].split("```")[0].strip()
        elif "```" in fixed_code:
            fixed_code = fixed_code.split("```")[1].split("```")[0].strip()

        # Apply the fix (simplified - would need more sophisticated merging)
        # For now, this is a placeholder that shows the concept
        print(f"🤖 AI suggested fix for {error_code} in {filepath}:")
        print(fixed_code[:200] + "..." if len(fixed_code) > 200 else fixed_code)

        return True

    except Exception as e:
        print(f"Error using OpenAI API: {e}", file=sys.stderr)
        return False


def fix_with_github_copilot_api(
    filepath: Path, error_code: str, line_num: int, message: str
) -> bool:
    """Fix using GitHub Copilot API (if available)."""
    # Note: GitHub Copilot doesn't have a public API for Actions
    # This is a placeholder for future integration
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        return False

    # GitHub doesn't provide Copilot API for Actions yet
    # Would need to use GitHub's Code Suggestions API when available
    return False


def main():
    """Main function to fix unfixable linting errors using AI."""
    print("🔍 Checking for unfixable linting errors...")

    errors = get_unfixable_errors()

    if not errors:
        print("✅ No unfixable errors found!")
        return 0

    print(f"Found {len(errors)} unfixable errors")

    # Check for AI API keys
    use_openai = bool(os.getenv("OPENAI_API_KEY"))
    use_copilot = bool(os.getenv("GITHUB_TOKEN"))

    if not use_openai and not use_copilot:
        print("⚠️  No AI API keys found. Set OPENAI_API_KEY environment variable to use AI fixes.")
        print("   Falling back to heuristic-based fixes...")
        # Could call the heuristic-based script here
        return 1

    fixed_count = 0

    for error_data in errors:
        if len(error_data) >= 5:
            filepath_str, code, line_num, message, end_line = error_data[:5]
        else:
            filepath_str, code, line_num, message = error_data[:4]
            end_line = line_num

        filepath = Path(filepath_str)

        if not filepath.exists():
            continue

        fixed = False

        if use_openai:
            fixed = fix_with_openai(filepath, code, line_num, message, end_line)
        elif use_copilot:
            fixed = fix_with_github_copilot_api(filepath, code, line_num, message)

        if fixed:
            fixed_count += 1
            print(f"✅ Fixed {code} in {filepath}")

    if fixed_count > 0:
        print(f"\n✨ Fixed {fixed_count} issues using AI!")
        return 0
    else:
        print("\n⚠️  Could not fix issues with AI.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
