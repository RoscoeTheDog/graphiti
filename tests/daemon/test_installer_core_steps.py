"""
Integration Test for GraphitiInstaller Core Steps (without admin privileges)

This script tests the core installation steps that don't require admin:
- _validate_environment()
- _create_directories()
- _create_venv()
- _install_dependencies(source_dir)
- _freeze_packages(source_dir)
- _create_pth_file()

Run from repository root:
    python tests/daemon/test_installer_core_steps.py

Created: 2025-12-25
Purpose: Validate installer core functionality without service registration
"""

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a test step."""
    step: str
    success: bool
    message: str
    details: Optional[dict] = None


def run_core_installer_test():
    """
    Test the core GraphitiInstaller steps using a temporary directory.

    This avoids modifying the real installation directories (~/.graphiti, etc.)
    and tests only the steps that don't require admin privileges.
    """
    results = []
    temp_dir = None

    try:
        # Step 1: Create temp directory for testing
        temp_dir = Path(tempfile.mkdtemp(prefix="graphiti_install_test_"))
        logger.info(f"Created temp test directory: {temp_dir}")

        # Define paths that will be used
        install_dir = temp_dir / "install"
        config_dir = temp_dir / "config"
        state_dir = temp_dir / "state"

        # Import after temp dir is created
        from mcp_server.daemon.installer import GraphitiInstaller, GraphitiPaths
        from mcp_server.daemon.paths import GraphitiPaths as RealGraphitiPaths

        # Create custom GraphitiPaths for testing
        test_paths = RealGraphitiPaths(
            install_dir=install_dir,
            config_dir=config_dir,
            state_dir=state_dir,
            config_file=config_dir / "graphiti.config.json"
        )

        # Patch get_paths to return our test paths
        with patch('mcp_server.daemon.installer.get_paths', return_value=test_paths):
            # Also patch VenvManager's get_install_dir to use our test paths
            with patch('mcp_server.daemon.venv_manager.get_install_dir', return_value=install_dir):
                # Create installer instance
                installer = GraphitiInstaller()
                installer.paths = test_paths  # Ensure paths are set correctly

                # Find the source repository root
                repo_root = Path(__file__).resolve().parent.parent.parent
                logger.info(f"Using repository root: {repo_root}")

                # ============================================================
                # Step 2: Test _validate_environment()
                # ============================================================
                logger.info("\n" + "="*60)
                logger.info("STEP 2: Testing _validate_environment()")
                logger.info("="*60)

                try:
                    installer._validate_environment()
                    results.append(TestResult(
                        step="_validate_environment",
                        success=True,
                        message="Environment validation passed",
                        details={
                            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
                        }
                    ))
                    logger.info("[PASS] _validate_environment()")
                except Exception as e:
                    results.append(TestResult(
                        step="_validate_environment",
                        success=False,
                        message=str(e)
                    ))
                    logger.error(f"[FAIL] _validate_environment(): {e}")
                    # Don't continue if validation fails
                    return results

                # ============================================================
                # Step 3: Test _create_directories()
                # ============================================================
                logger.info("\n" + "="*60)
                logger.info("STEP 3: Testing _create_directories()")
                logger.info("="*60)

                try:
                    installer._create_directories()

                    # Verify directories were created
                    expected_dirs = [
                        install_dir / "bin",
                        install_dir / "lib",
                        config_dir,
                        state_dir / "logs",
                        state_dir / "data",
                        state_dir / "data" / "sessions",
                    ]

                    missing_dirs = [d for d in expected_dirs if not d.exists()]

                    if missing_dirs:
                        results.append(TestResult(
                            step="_create_directories",
                            success=False,
                            message=f"Missing directories: {missing_dirs}"
                        ))
                        logger.error(f"[FAIL] _create_directories(): Missing {missing_dirs}")
                    else:
                        results.append(TestResult(
                            step="_create_directories",
                            success=True,
                            message="All directories created successfully",
                            details={"directories": [str(d) for d in expected_dirs]}
                        ))
                        logger.info("[PASS] _create_directories()")
                        for d in expected_dirs:
                            logger.info(f"  - Created: {d}")

                except Exception as e:
                    results.append(TestResult(
                        step="_create_directories",
                        success=False,
                        message=str(e)
                    ))
                    logger.error(f"[FAIL] _create_directories(): {e}")
                    return results

                # ============================================================
                # Step 4: Test _create_venv()
                # ============================================================
                logger.info("\n" + "="*60)
                logger.info("STEP 4: Testing _create_venv()")
                logger.info("="*60)

                try:
                    installer._create_venv()

                    # Verify venv was created
                    pyvenv_cfg = install_dir / "pyvenv.cfg"
                    if sys.platform == "win32":
                        python_exe = install_dir / "Scripts" / "python.exe"
                        activate = install_dir / "Scripts" / "activate.bat"
                    else:
                        python_exe = install_dir / "bin" / "python"
                        activate = install_dir / "bin" / "activate"

                    if not pyvenv_cfg.exists():
                        results.append(TestResult(
                            step="_create_venv",
                            success=False,
                            message=f"pyvenv.cfg not found at {pyvenv_cfg}"
                        ))
                        logger.error(f"[FAIL] _create_venv(): pyvenv.cfg missing")
                    elif not python_exe.exists():
                        results.append(TestResult(
                            step="_create_venv",
                            success=False,
                            message=f"Python executable not found at {python_exe}"
                        ))
                        logger.error(f"[FAIL] _create_venv(): python executable missing")
                    else:
                        results.append(TestResult(
                            step="_create_venv",
                            success=True,
                            message="Virtual environment created successfully",
                            details={
                                "venv_path": str(install_dir),
                                "python_exe": str(python_exe),
                                "pyvenv_cfg": str(pyvenv_cfg)
                            }
                        ))
                        logger.info("[PASS] _create_venv()")
                        logger.info(f"  - pyvenv.cfg: {pyvenv_cfg}")
                        logger.info(f"  - Python exe: {python_exe}")

                except Exception as e:
                    results.append(TestResult(
                        step="_create_venv",
                        success=False,
                        message=str(e)
                    ))
                    logger.error(f"[FAIL] _create_venv(): {e}")
                    import traceback
                    traceback.print_exc()
                    return results

                # ============================================================
                # Step 5: Test _install_dependencies()
                # ============================================================
                logger.info("\n" + "="*60)
                logger.info("STEP 5: Testing _install_dependencies()")
                logger.info("="*60)

                try:
                    installer._install_dependencies(source_dir=repo_root)

                    # Verify requirements.txt was created
                    requirements_file = install_dir / "requirements.txt"

                    if not requirements_file.exists():
                        results.append(TestResult(
                            step="_install_dependencies",
                            success=False,
                            message=f"requirements.txt not found at {requirements_file}"
                        ))
                        logger.error(f"[FAIL] _install_dependencies(): requirements.txt missing")
                    else:
                        # Read requirements count
                        reqs = requirements_file.read_text().strip().split('\n')
                        results.append(TestResult(
                            step="_install_dependencies",
                            success=True,
                            message=f"Dependencies installed ({len(reqs)} packages)",
                            details={
                                "requirements_file": str(requirements_file),
                                "package_count": len(reqs)
                            }
                        ))
                        logger.info("[PASS] _install_dependencies()")
                        logger.info(f"  - requirements.txt: {requirements_file}")
                        logger.info(f"  - Package count: {len(reqs)}")

                except Exception as e:
                    results.append(TestResult(
                        step="_install_dependencies",
                        success=False,
                        message=str(e)
                    ))
                    logger.error(f"[FAIL] _install_dependencies(): {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue anyway to test freeze_packages

                # ============================================================
                # Step 6: Test _freeze_packages()
                # ============================================================
                logger.info("\n" + "="*60)
                logger.info("STEP 6: Testing _freeze_packages()")
                logger.info("="*60)

                try:
                    installer._freeze_packages(source_dir=repo_root)

                    # Verify packages were copied
                    lib_dir = install_dir / "lib"
                    mcp_server_dir = lib_dir / "mcp_server"
                    graphiti_core_dir = lib_dir / "graphiti_core"
                    manifest_file = lib_dir / "PACKAGE_MANIFEST.json"

                    missing = []
                    if not mcp_server_dir.exists():
                        missing.append("mcp_server")
                    if not graphiti_core_dir.exists():
                        missing.append("graphiti_core")
                    if not manifest_file.exists():
                        missing.append("PACKAGE_MANIFEST.json")

                    if missing:
                        results.append(TestResult(
                            step="_freeze_packages",
                            success=False,
                            message=f"Missing: {missing}"
                        ))
                        logger.error(f"[FAIL] _freeze_packages(): Missing {missing}")
                    else:
                        import json
                        manifest = json.loads(manifest_file.read_text())
                        results.append(TestResult(
                            step="_freeze_packages",
                            success=True,
                            message="Packages frozen successfully",
                            details={
                                "lib_dir": str(lib_dir),
                                "total_files": manifest.get("total_files", 0),
                                "total_size_bytes": manifest.get("total_size_bytes", 0)
                            }
                        ))
                        logger.info("[PASS] _freeze_packages()")
                        logger.info(f"  - mcp_server: {mcp_server_dir}")
                        logger.info(f"  - graphiti_core: {graphiti_core_dir}")
                        logger.info(f"  - Manifest: {manifest.get('total_files', 0)} files, {manifest.get('total_size_bytes', 0) / 1024:.1f} KB")

                except Exception as e:
                    results.append(TestResult(
                        step="_freeze_packages",
                        success=False,
                        message=str(e)
                    ))
                    logger.error(f"[FAIL] _freeze_packages(): {e}")
                    import traceback
                    traceback.print_exc()

                # ============================================================
                # Step 7: Test _create_pth_file()
                # ============================================================
                logger.info("\n" + "="*60)
                logger.info("STEP 7: Testing _create_pth_file()")
                logger.info("="*60)

                try:
                    installer._create_pth_file()

                    # Find the .pth file
                    if sys.platform == "win32":
                        site_packages = install_dir / "Lib" / "site-packages"
                    else:
                        python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
                        site_packages = install_dir / "lib" / python_version / "site-packages"

                    pth_file = site_packages / "graphiti.pth"

                    if not pth_file.exists():
                        results.append(TestResult(
                            step="_create_pth_file",
                            success=False,
                            message=f".pth file not found at {pth_file}"
                        ))
                        logger.error(f"[FAIL] _create_pth_file(): .pth file missing")
                    else:
                        pth_content = pth_file.read_text().strip()
                        lib_dir = install_dir / "lib"

                        if str(lib_dir.resolve()) not in pth_content:
                            results.append(TestResult(
                                step="_create_pth_file",
                                success=False,
                                message=f".pth file doesn't point to lib/: {pth_content}"
                            ))
                            logger.error(f"[FAIL] _create_pth_file(): Wrong path in .pth")
                        else:
                            results.append(TestResult(
                                step="_create_pth_file",
                                success=True,
                                message=".pth file created successfully",
                                details={
                                    "pth_file": str(pth_file),
                                    "points_to": pth_content
                                }
                            ))
                            logger.info("[PASS] _create_pth_file()")
                            logger.info(f"  - .pth file: {pth_file}")
                            logger.info(f"  - Points to: {pth_content}")

                except Exception as e:
                    results.append(TestResult(
                        step="_create_pth_file",
                        success=False,
                        message=str(e)
                    ))
                    logger.error(f"[FAIL] _create_pth_file(): {e}")
                    import traceback
                    traceback.print_exc()

                # ============================================================
                # Step 8: Verify imports from venv's Python
                # ============================================================
                logger.info("\n" + "="*60)
                logger.info("STEP 8: Testing imports from venv Python")
                logger.info("="*60)

                try:
                    if sys.platform == "win32":
                        python_exe = install_dir / "Scripts" / "python.exe"
                    else:
                        python_exe = install_dir / "bin" / "python"

                    # First, check what sys.path looks like in the venv
                    logger.info("Checking venv's sys.path...")
                    result_path = subprocess.run(
                        [str(python_exe), "-c", "import sys; print('\\n'.join(sys.path))"],
                        capture_output=True,
                        text=True,
                        timeout=15
                    )
                    if result_path.returncode == 0:
                        logger.info(f"Venv sys.path:\n{result_path.stdout}")
                    else:
                        logger.warning(f"Could not get sys.path: {result_path.stderr}")

                    # Test importing mcp_server (simpler, should be faster)
                    logger.info("Testing mcp_server import...")
                    result_mcp = subprocess.run(
                        [str(python_exe), "-c", "import mcp_server; print('OK')"],
                        capture_output=True,
                        text=True,
                        timeout=60  # Increased timeout
                    )

                    # Test importing graphiti_core (has heavier deps, may be slow)
                    logger.info("Testing graphiti_core import (may take longer due to dependencies)...")
                    result_core = subprocess.run(
                        [str(python_exe), "-c", "import graphiti_core; print('OK')"],
                        capture_output=True,
                        text=True,
                        timeout=120  # Increased timeout for graphiti_core
                    )

                    core_ok = result_core.returncode == 0 and "OK" in result_core.stdout
                    mcp_ok = result_mcp.returncode == 0 and "OK" in result_mcp.stdout

                    if core_ok and mcp_ok:
                        results.append(TestResult(
                            step="verify_imports",
                            success=True,
                            message="Both graphiti_core and mcp_server are importable",
                            details={
                                "python_exe": str(python_exe),
                                "graphiti_core": "OK",
                                "mcp_server": "OK"
                            }
                        ))
                        logger.info("[PASS] Import verification")
                        logger.info("  - graphiti_core: importable")
                        logger.info("  - mcp_server: importable")
                    else:
                        details = {"python_exe": str(python_exe)}
                        if not core_ok:
                            details["graphiti_core_error"] = result_core.stderr.strip() if result_core.stderr else result_core.stdout.strip()
                            details["graphiti_core_returncode"] = result_core.returncode
                            logger.error(f"  - graphiti_core import failed (rc={result_core.returncode}):")
                            logger.error(f"    stdout: {result_core.stdout.strip()}")
                            logger.error(f"    stderr: {result_core.stderr.strip()}")
                        if not mcp_ok:
                            details["mcp_server_error"] = result_mcp.stderr.strip() if result_mcp.stderr else result_mcp.stdout.strip()
                            details["mcp_server_returncode"] = result_mcp.returncode
                            logger.error(f"  - mcp_server import failed (rc={result_mcp.returncode}):")
                            logger.error(f"    stdout: {result_mcp.stdout.strip()}")
                            logger.error(f"    stderr: {result_mcp.stderr.strip()}")

                        results.append(TestResult(
                            step="verify_imports",
                            success=False,
                            message="Import verification failed",
                            details=details
                        ))
                        logger.error("[FAIL] Import verification")

                except Exception as e:
                    results.append(TestResult(
                        step="verify_imports",
                        success=False,
                        message=str(e)
                    ))
                    logger.error(f"[FAIL] Import verification: {e}")
                    import traceback
                    traceback.print_exc()

                # ============================================================
                # Summary
                # ============================================================
                logger.info("\n" + "="*60)
                logger.info("SUMMARY")
                logger.info("="*60)

                passed = sum(1 for r in results if r.success)
                failed = sum(1 for r in results if not r.success)

                logger.info(f"Total: {len(results)} tests")
                logger.info(f"Passed: {passed}")
                logger.info(f"Failed: {failed}")

                for r in results:
                    status = "[PASS]" if r.success else "[FAIL]"
                    logger.info(f"  {status} {r.step}: {r.message}")

                return results

    except Exception as e:
        logger.error(f"Unexpected error during test: {e}")
        import traceback
        traceback.print_exc()
        results.append(TestResult(
            step="test_setup",
            success=False,
            message=str(e)
        ))
        return results

    finally:
        # Cleanup temp directory
        if temp_dir and temp_dir.exists():
            logger.info(f"\nCleaning up temp directory: {temp_dir}")
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info("Cleanup complete")
            except Exception as e:
                logger.warning(f"Cleanup failed (non-critical): {e}")


def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("GraphitiInstaller Core Steps Integration Test")
    print("="*70 + "\n")

    # Ensure we're running from the repository root
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent

    # Check that we're in the right place
    if not (repo_root / "mcp_server" / "__init__.py").exists():
        print(f"ERROR: Repository root not found at {repo_root}")
        print("Please run from the repository root directory")
        sys.exit(1)

    # Add repo root to path so we can import the modules
    sys.path.insert(0, str(repo_root))

    print(f"Repository root: {repo_root}")
    print(f"Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"Platform: {sys.platform}\n")

    # Run the test
    results = run_core_installer_test()

    # Exit with appropriate code
    failed = sum(1 for r in results if not r.success)
    if failed > 0:
        print(f"\n[FAIL] {failed} test(s) failed")
        sys.exit(1)
    else:
        print(f"\n[PASS] All {len(results)} tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
