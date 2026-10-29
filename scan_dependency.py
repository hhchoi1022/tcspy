"""
Scan the current project for third-party imports and write installed
versions to requirements.txt.
"""

from pathlib import Path
from importlib.metadata import (
    PackageNotFoundError,
    packages_distributions,
    version,
)
import ast
import sys


PROJECT_DIR = Path(__file__).resolve().parent
THIS_FILE = Path(__file__).resolve()

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "build",
    "dist",
    "docs",
    "analysis",
}

# ??? Python ?? ??
python_files = [
    path
    for path in PROJECT_DIR.rglob("*.py")
    if path.resolve() != THIS_FILE
    and not any(part in EXCLUDE_DIRS for part in path.parts)
]

# ???? ?? ???? ?? ?? ??
local_modules = set()

for path in python_files:
    relative = path.relative_to(PROJECT_DIR)

    # ?? ???? ??
    local_modules.update(relative.parts[:-1])

    # ?? Python ?? ??
    if path.name != "__init__.py":
        local_modules.add(path.stem)

# import ? ??
imports = set()

for path in python_files:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        continue

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            # from .module import ... ??? ?? import??? ??
            if node.level > 0:
                continue

            if node.module:
                imports.add(node.module.split(".")[0])

# ?? ?????? ?? ?? ??
third_party = sorted(
    module
    for module in imports
    if module not in sys.stdlib_module_names
    and module not in local_modules
    and module != "tcspy"  # this project itself (imported as tcspy.*)
)

# import ??? ?? ??? ??? ?? ??
mapping = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "sklearn": "scikit-learn",
    "yaml": "PyYAML",
    # import name differs from the PyPI name (falls back to a wrong PyPI package if not installed)
    "alpaca": "alpyca",
    "mysql": "mysql-connector-python",
    "ligo": "ligo.skymap",
}

# ??? import ?? ? PyPI ?? ??? ??
distribution_map = packages_distributions()

pypi_packages = set()

for module in third_party:
    if module in mapping:
        pypi_packages.add(mapping[module])
    elif distribution_map.get(module):
        pypi_packages.add(distribution_map[module][0])
    else:
        # ???? ?? ?? ??? ??? ? ?? ??
        pypi_packages.add(module)

# ?? ??? ??? ?? ??
requirements = []

for package in sorted(pypi_packages, key=str.lower):
    try:
        requirements.append(f"{package}=={version(package)}")
    except PackageNotFoundError:
        requirements.append(package)

# requirements.txt ??
req_file = PROJECT_DIR / "requirements.txt"
req_file.write_text(
    "\n".join(requirements) + ("\n" if requirements else ""),
    encoding="utf-8",
)

print(f"Scanned {len(python_files)} Python files.")
print(f"Detected {len(requirements)} external packages.")

for requirement in requirements:
    print(f"  {requirement}")

print(f"Saved to {req_file}")
