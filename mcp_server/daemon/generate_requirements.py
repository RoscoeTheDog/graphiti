"""
Graphiti Requirements Generator

Standalone script to parse mcp_server/pyproject.toml and generate requirements.txt
with proper version pinning for standalone deployments.

This module provides:
- TOML parsing using tomllib (Python 3.11+) or toml package (Python 3.10)
- Extraction of dependencies from [project.dependencies]
- Optional inclusion of [project.optional-dependencies]
- Platform-agnostic path handling
- Output to ~/.graphiti/requirements.txt

Design Principle: Enable standalone pip installations without access to pyproject.toml
by pre-generating requirements.txt during daemon deployment.

See: .claude/sprint/stories/1-generate-requirements-txt.md
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Python 3.11+ has tomllib in stdlib, Python 3.10 needs toml package
try:
    import tomllib
except ImportError:
    try:
        import toml as tomllib  # type: ignore
    except ImportError:
        raise ImportError(
            "TOML parsing requires tomllib (Python 3.11+) or toml package (Python 3.10). "
            "Install toml: pip install toml"
        )

logger = logging.getLogger(__name__)


class RequirementsGenerationError(Exception):
    """Raised when requirements.txt generation fails."""
    pass


class PyprojectParseError(Exception):
    """Raised when pyproject.toml parsing fails."""
    pass


def parse_pyproject_toml(pyproject_path: Path) -> Dict:
    """
    Parse pyproject.toml and extract project metadata.

    Args:
        pyproject_path: Path to pyproject.toml file

    Returns:
        Dictionary containing parsed TOML data

    Raises:
        PyprojectParseError: If file doesn't exist or TOML is malformed
    """
    if not pyproject_path.exists():
        raise PyprojectParseError(f"pyproject.toml not found at: {pyproject_path}")

    if not pyproject_path.suffix == ".toml":
        raise PyprojectParseError(f"Expected .toml file, got: {pyproject_path}")

    try:
        # Python 3.11+ tomllib requires binary mode, toml package accepts text mode
        if hasattr(tomllib, 'load'):
            # tomllib (3.11+)
            with open(pyproject_path, 'rb') as f:
                data = tomllib.load(f)
        else:
            # toml package (3.10)
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                data = tomllib.load(f)  # type: ignore

        if 'project' not in data:
            raise PyprojectParseError(
                f"Invalid pyproject.toml: missing [project] section at {pyproject_path}"
            )

        return data
    except Exception as e:
        if isinstance(e, PyprojectParseError):
            raise
        raise PyprojectParseError(f"Failed to parse pyproject.toml: {e}")


def generate_requirements_txt(
    pyproject_data: Dict,
    include_optional: bool = False,
    optional_groups: Optional[List[str]] = None,
    exclude_local_packages: bool = True
) -> List[str]:
    """
    Generate requirements.txt content from pyproject.toml data.

    Args:
        pyproject_data: Parsed pyproject.toml dictionary
        include_optional: Include optional dependencies
        optional_groups: Specific optional dependency groups to include (e.g., ['azure', 'providers'])
        exclude_local_packages: If True, exclude packages that are being frozen locally
                               (e.g., graphiti-core when using frozen packages)

    Returns:
        List of requirement strings (one per dependency)

    Raises:
        RequirementsGenerationError: If [project.dependencies] section is missing
    """
    project = pyproject_data.get('project', {})

    # Extract core dependencies
    dependencies = project.get('dependencies', [])
    if not dependencies and not include_optional:
        raise RequirementsGenerationError(
            "No dependencies found in [project.dependencies] section"
        )

    requirements = []

    # Packages that are frozen locally and shouldn't be installed from pip
    # These are copied from source to lib/ directory during installation
    LOCAL_FROZEN_PACKAGES = {
        'graphiti-core',  # Frozen from local source, has extras like [falkordb]
    }

    # Dependencies of graphiti-core that we need to install since we're not
    # installing graphiti-core from pip
    # From graphiti_core/pyproject.toml [project.dependencies] + [project.optional-dependencies.falkordb]
    GRAPHITI_CORE_DEPS = [
        "pydantic>=2.11.5",
        "neo4j>=5.26.0",
        "diskcache>=5.6.3",
        "openai>=1.91.0",
        "tenacity>=9.0.0",
        "numpy>=1.0.0",
        "python-dotenv>=1.0.1",
        "posthog>=3.0.0",
        "falkordb>=1.1.2,<2.0.0",  # From [falkordb] extra
    ]

    # Add core dependencies
    for dep in dependencies:
        dep = dep.strip()

        if exclude_local_packages:
            # Check if this is a local frozen package (handle extras like [falkordb])
            pkg_name = dep.split('[')[0].split('>')[0].split('<')[0].split('=')[0].strip()
            if pkg_name.lower() in [p.lower() for p in LOCAL_FROZEN_PACKAGES]:
                logger.info(f"Excluding local package '{dep}', adding its dependencies instead")
                # Add the transitive dependencies instead
                for trans_dep in GRAPHITI_CORE_DEPS:
                    requirements.append(trans_dep)
                continue

        # Preserve version specifiers exactly as written
        requirements.append(dep)

    # Add optional dependencies if requested
    if include_optional:
        optional_deps = project.get('optional-dependencies', {})

        if optional_groups:
            # Include only specified groups
            for group in optional_groups:
                if group in optional_deps:
                    for dep in optional_deps[group]:
                        requirements.append(dep.strip())
                else:
                    logger.warning(f"Optional dependency group '{group}' not found")
        else:
            # Include all optional dependencies
            for group, deps in optional_deps.items():
                for dep in deps:
                    requirements.append(dep.strip())

    # Remove duplicates while preserving order
    seen = set()
    unique_requirements = []
    for req in requirements:
        if req not in seen:
            seen.add(req)
            unique_requirements.append(req)

    return unique_requirements


def write_requirements_file(requirements: List[str], output_path: Path) -> None:
    """
    Write requirements to file with proper formatting.

    Args:
        requirements: List of requirement strings
        output_path: Path to output requirements.txt file

    Raises:
        RequirementsGenerationError: If writing fails
    """
    # Validate output path (prevent path traversal)
    original_path = str(output_path)

    # Check for path traversal BEFORE resolving (.. in original path)
    if '..' in original_path.replace('\\', '/'):
        raise RequirementsGenerationError(
            f"Path traversal detected in output path: {output_path}"
        )

    try:
        output_path = output_path.resolve()
    except Exception as e:
        raise RequirementsGenerationError(f"Invalid output path: {e}")

    # Create parent directory if missing
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise RequirementsGenerationError(
            f"Failed to create output directory {output_path.parent}: {e}"
        )

    # Write requirements (one per line)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for req in requirements:
                f.write(f"{req}\n")

        # Set readable permissions (platform-agnostic)
        output_path.chmod(0o644)

        logger.info(f"Successfully wrote {len(requirements)} requirements to {output_path}")
    except Exception as e:
        raise RequirementsGenerationError(f"Failed to write requirements.txt: {e}")


def main() -> int:
    """
    CLI entry point for requirements generation.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Generate requirements.txt from pyproject.toml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from mcp_server/pyproject.toml to ~/.graphiti/requirements.txt
  python generate_requirements.py

  # Include optional dependencies
  python generate_requirements.py --include-optional

  # Include specific optional groups
  python generate_requirements.py --optional-groups azure providers

  # Custom input/output paths
  python generate_requirements.py --input /path/to/pyproject.toml --output /path/to/requirements.txt
        """
    )

    parser.add_argument(
        '--input',
        type=Path,
        default=None,
        help='Path to pyproject.toml (default: mcp_server/pyproject.toml relative to script)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Path to output requirements.txt (default: ~/.graphiti/requirements.txt)'
    )

    parser.add_argument(
        '--include-optional',
        action='store_true',
        help='Include all optional dependencies'
    )

    parser.add_argument(
        '--optional-groups',
        nargs='+',
        help='Specific optional dependency groups to include (e.g., azure providers)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    # Determine input path
    if args.input is None:
        # Default: mcp_server/pyproject.toml relative to script location
        script_dir = Path(__file__).parent.parent
        input_path = script_dir / 'pyproject.toml'
    else:
        input_path = args.input

    # Determine output path
    if args.output is None:
        # Default: ~/.graphiti/requirements.txt
        output_path = Path.home() / '.graphiti' / 'requirements.txt'
    else:
        output_path = args.output

    try:
        # Parse pyproject.toml
        logger.debug(f"Parsing {input_path}")
        pyproject_data = parse_pyproject_toml(input_path)

        # Generate requirements
        logger.debug("Generating requirements list")
        requirements = generate_requirements_txt(
            pyproject_data,
            include_optional=args.include_optional or bool(args.optional_groups),
            optional_groups=args.optional_groups
        )

        logger.info(f"Generated {len(requirements)} requirements")

        # Write to file
        logger.debug(f"Writing to {output_path}")
        write_requirements_file(requirements, output_path)

        print(f"Successfully generated {output_path}")
        print(f"{len(requirements)} dependencies written")

        return 0

    except (PyprojectParseError, RequirementsGenerationError) as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
