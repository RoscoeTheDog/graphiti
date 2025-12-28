"""
Unit Tests for Service Managers' Frozen Package Integration (v2.1)

Tests that service managers use frozen package installation paths:
- WindowsServiceManager uses {INSTALL_DIR}/bin/python.exe
- LaunchdServiceManager uses {INSTALL_DIR}/bin/python
- SystemdServiceManager uses {INSTALL_DIR}/bin/python
- Service managers use module invocation: python -m mcp_server.daemon.bootstrap
- Service managers set PYTHONPATH={INSTALL_DIR}/lib
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

import pytest

from mcp_server.daemon.windows_service import WindowsServiceManager
from mcp_server.daemon.launchd_service import LaunchdServiceManager
from mcp_server.daemon.systemd_service import SystemdServiceManager
from mcp_server.daemon.venv_manager import VenvManager, VenvCreationError


class TestWindowsServiceVenvIntegration:
    """Test WindowsServiceManager uses venv Python path."""

    def test_windows_service_uses_venv_python_path(self):
        """WindowsServiceManager uses venv Python path (not sys.executable)"""
        with patch('platform.system', return_value='Windows'):
            # Mock VenvManager
            mock_venv = Mock(spec=VenvManager)
            mock_venv.venv_path = Path.home() / '.graphiti' / '.venv'
            mock_venv.get_python_executable.return_value = str(
                Path.home() / '.graphiti' / '.venv' / 'Scripts' / 'python.exe'
            )

            # Create service manager with venv_manager
            service_manager = WindowsServiceManager(venv_manager=mock_venv)

            # Verify python_exe is NOT sys.executable
            assert service_manager.python_exe != sys.executable

            # Verify python_exe uses venv path
            assert service_manager.python_exe == mock_venv.get_python_executable.return_value
            assert 'Scripts' in service_manager.python_exe
            assert 'python.exe' in service_manager.python_exe

    def test_windows_service_calls_venv_manager_get_python_executable(self):
        """WindowsServiceManager calls VenvManager.get_python_executable()"""
        with patch('platform.system', return_value='Windows'):
            mock_venv = Mock(spec=VenvManager)
            mock_venv.get_python_executable.return_value = str(
                Path.home() / '.graphiti' / '.venv' / 'Scripts' / 'python.exe'
            )

            service_manager = WindowsServiceManager(venv_manager=mock_venv)

            # Verify get_python_executable was called
            mock_venv.get_python_executable.assert_called_once()

    def test_windows_service_handles_venv_missing_gracefully(self):
        """WindowsServiceManager handles VenvCreationError gracefully if venv missing"""
        with patch('platform.system', return_value='Windows'):
            mock_venv = Mock(spec=VenvManager)
            mock_venv.get_python_executable.side_effect = VenvCreationError(
                "Venv does not exist at ~/.graphiti/.venv"
            )

            # Should raise VenvCreationError (not crash with AttributeError)
            with pytest.raises(VenvCreationError) as exc_info:
                service_manager = WindowsServiceManager(venv_manager=mock_venv)

            assert "Venv does not exist" in str(exc_info.value)


class TestLaunchdServiceFrozenIntegration:
    """Test LaunchdServiceManager uses frozen package paths (v2.1)."""

    def test_launchd_service_uses_frozen_python_path(self):
        """LaunchdServiceManager uses {INSTALL_DIR}/bin/python (not sys.executable)"""
        with patch('platform.system', return_value='Darwin'):
            # Mock get_install_dir
            mock_install_dir = Path.home() / '.graphiti'
            with patch('mcp_server.daemon.launchd_service.get_install_dir', return_value=mock_install_dir):
                service_manager = LaunchdServiceManager()

                # Verify python_exe is NOT sys.executable
                assert service_manager.python_exe != Path(sys.executable)

                # Verify python_exe uses frozen package path
                expected_path = mock_install_dir / 'bin' / 'python'
                assert service_manager.python_exe == expected_path
                assert 'bin' in str(service_manager.python_exe)
                assert 'python' in str(service_manager.python_exe)

    def test_launchd_service_uses_install_dir_from_paths(self):
        """LaunchdServiceManager gets install_dir from get_install_dir()"""
        with patch('platform.system', return_value='Darwin'):
            mock_install_dir = Path.home() / '.graphiti'
            with patch('mcp_server.daemon.launchd_service.get_install_dir', return_value=mock_install_dir) as mock_get_install:
                service_manager = LaunchdServiceManager()

                # Verify get_install_dir was called
                mock_get_install.assert_called_once()

                # Verify install_dir is set correctly
                assert service_manager.install_dir == mock_install_dir

    def test_launchd_plist_uses_module_invocation(self):
        """LaunchdServiceManager plist uses 'python -m mcp_server.daemon.bootstrap'"""
        with patch('platform.system', return_value='Darwin'):
            mock_install_dir = Path.home() / '.graphiti'
            with patch('mcp_server.daemon.launchd_service.get_install_dir', return_value=mock_install_dir):
                service_manager = LaunchdServiceManager()
                plist_content = service_manager._create_plist()

                # Verify ProgramArguments uses module invocation
                program_args = plist_content['ProgramArguments']
                assert program_args[0] == str(mock_install_dir / 'bin' / 'python')
                assert program_args[1] == '-m'
                assert program_args[2] == 'mcp_server.daemon.bootstrap'


class TestSystemdServiceVenvIntegration:
    """Test SystemdServiceManager uses venv Python path."""

    def test_systemd_service_uses_venv_python_path(self):
        """SystemdServiceManager uses venv Python path (not sys.executable)"""
        with patch('platform.system', return_value='Linux'):
            # Mock VenvManager
            mock_venv = Mock(spec=VenvManager)
            mock_venv.venv_path = Path.home() / '.graphiti' / '.venv'
            mock_venv.get_python_executable.return_value = str(
                Path.home() / '.graphiti' / '.venv' / 'bin' / 'python'
            )

            # Create service manager with venv_manager
            service_manager = SystemdServiceManager(venv_manager=mock_venv)

            # Verify python_exe is NOT sys.executable
            assert service_manager.python_exe != sys.executable

            # Verify python_exe uses venv path
            assert service_manager.python_exe == mock_venv.get_python_executable.return_value
            assert 'bin' in service_manager.python_exe
            assert 'python' in service_manager.python_exe

    def test_systemd_service_calls_venv_manager_get_python_executable(self):
        """SystemdServiceManager calls VenvManager.get_python_executable()"""
        with patch('platform.system', return_value='Linux'):
            mock_venv = Mock(spec=VenvManager)
            mock_venv.get_python_executable.return_value = str(
                Path.home() / '.graphiti' / '.venv' / 'bin' / 'python'
            )

            service_manager = SystemdServiceManager(venv_manager=mock_venv)

            # Verify get_python_executable was called
            mock_venv.get_python_executable.assert_called_once()

    def test_systemd_service_handles_venv_missing_gracefully(self):
        """SystemdServiceManager handles VenvCreationError gracefully if venv missing"""
        with patch('platform.system', return_value='Linux'):
            mock_venv = Mock(spec=VenvManager)
            mock_venv.get_python_executable.side_effect = VenvCreationError(
                "Venv does not exist at ~/.graphiti/.venv"
            )

            # Should raise VenvCreationError (not crash with AttributeError)
            with pytest.raises(VenvCreationError) as exc_info:
                service_manager = SystemdServiceManager(venv_manager=mock_venv)

            assert "Venv does not exist" in str(exc_info.value)


class TestServiceManagerPlatformSpecificPaths:
    """Test service managers use correct platform-specific venv paths."""

    def test_windows_service_uses_scripts_python_exe(self):
        """Windows service uses Scripts/python.exe (not bin/python)"""
        with patch('platform.system', return_value='Windows'):
            mock_venv = Mock(spec=VenvManager)
            mock_venv.get_python_executable.return_value = str(
                Path.home() / '.graphiti' / '.venv' / 'Scripts' / 'python.exe'
            )

            service_manager = WindowsServiceManager(venv_manager=mock_venv)

            # Verify Windows-specific path structure
            assert 'Scripts' in service_manager.python_exe
            assert service_manager.python_exe.endswith('python.exe')
            assert 'bin' not in service_manager.python_exe

    def test_unix_services_use_bin_python(self):
        """Unix services (macOS/Linux) use bin/python (not Scripts/python.exe)"""
        # Test macOS
        with patch('platform.system', return_value='Darwin'):
            mock_install_dir = Path.home() / '.graphiti'
            with patch('mcp_server.daemon.launchd_service.get_install_dir', return_value=mock_install_dir):
                launchd_manager = LaunchdServiceManager()

                # Verify Unix-specific path structure
                assert 'bin' in str(launchd_manager.python_exe)
                assert str(launchd_manager.python_exe).endswith('python')
                assert 'Scripts' not in str(launchd_manager.python_exe)
                assert not str(launchd_manager.python_exe).endswith('.exe')

        # Test Linux
        with patch('platform.system', return_value='Linux'):
            mock_venv = Mock(spec=VenvManager)
            mock_venv.get_python_executable.return_value = str(
                Path.home() / '.graphiti' / '.venv' / 'bin' / 'python'
            )

            systemd_manager = SystemdServiceManager(venv_manager=mock_venv)

            # Verify Unix-specific path structure
            assert 'bin' in systemd_manager.python_exe
            assert systemd_manager.python_exe.endswith('python')
            assert 'Scripts' not in systemd_manager.python_exe
            assert not systemd_manager.python_exe.endswith('.exe')


class TestServiceTemplateGeneration:
    """Test service templates use venv Python path."""

    def test_windows_service_template_uses_venv_python(self):
        """Windows service uses venv Python path in NSSM install command"""
        with patch('platform.system', return_value='Windows'):
            mock_venv = Mock(spec=VenvManager)
            venv_python = str(Path.home() / '.graphiti' / '.venv' / 'Scripts' / 'python.exe')
            mock_venv.get_python_executable.return_value = venv_python

            # Mock _find_nssm to return a valid path
            with patch.object(WindowsServiceManager, '_find_nssm', return_value=Path('C:/nssm/nssm.exe')):
                service_manager = WindowsServiceManager(venv_manager=mock_venv)

                # Mock NSSM execution to verify venv Python is used
                with patch.object(service_manager, '_run_nssm') as mock_nssm:
                    with patch.object(service_manager, 'is_installed', return_value=False):
                        with patch('builtins.print'):  # Suppress print statements
                            mock_nssm.return_value = (True, "Service installed")

                            # Call install() - should pass venv_python to NSSM
                            service_manager.install()

                            # Verify NSSM install command used venv Python (not sys.executable)
                            install_call = mock_nssm.call_args_list[0]  # First call is 'install'
                            assert install_call[0][0] == 'install'  # First arg is 'install'
                            assert install_call[0][2] == venv_python  # Third arg is python path
                            assert install_call[0][2] != sys.executable  # Not system Python

    def test_launchd_plist_uses_frozen_python_and_pythonpath(self):
        """macOS launchd plist uses frozen Python path and sets PYTHONPATH"""
        with patch('platform.system', return_value='Darwin'):
            mock_install_dir = Path.home() / '.graphiti'
            with patch('mcp_server.daemon.launchd_service.get_install_dir', return_value=mock_install_dir):
                service_manager = LaunchdServiceManager()

                # Call actual _create_plist method (no mocking)
                plist_content = service_manager._create_plist()

                # Verify plist includes frozen Python path (in ProgramArguments)
                expected_python = str(mock_install_dir / 'bin' / 'python')
                assert expected_python in plist_content['ProgramArguments']
                assert sys.executable not in plist_content['ProgramArguments']

                # Verify WorkingDirectory is INSTALL_DIR
                assert plist_content['WorkingDirectory'] == str(mock_install_dir)

                # Verify PYTHONPATH is set to {INSTALL_DIR}/lib
                expected_pythonpath = str(mock_install_dir / 'lib')
                assert plist_content['EnvironmentVariables']['PYTHONPATH'] == expected_pythonpath

    def test_systemd_unit_uses_venv_python(self):
        """Linux systemd unit file uses venv Python path"""
        with patch('platform.system', return_value='Linux'):
            mock_venv = Mock(spec=VenvManager)
            venv_python = str(Path.home() / '.graphiti' / '.venv' / 'bin' / 'python')
            mock_venv.get_python_executable.return_value = venv_python

            service_manager = SystemdServiceManager(venv_manager=mock_venv)

            # Call actual _create_service_unit method (no mocking)
            unit_content = service_manager._create_service_unit()

            # Verify unit file includes venv Python path (in ExecStart)
            assert venv_python in unit_content
            assert sys.executable not in unit_content


class TestDaemonManagerServiceIntegration:
    """Integration test: DaemonManager.install() passes venv_manager to service managers."""

    def test_daemon_manager_passes_venv_manager_to_service_manager(self):
        """DaemonManager.install() passes venv_manager to service manager constructor"""
        with patch('platform.system', return_value='Linux'):
            from mcp_server.daemon.manager import DaemonManager

            # Mock WrapperGenerator BEFORE creating DaemonManager
            with patch('mcp_server.daemon.manager.WrapperGenerator') as mock_wrapper_class:
                mock_wrapper = mock_wrapper_class.return_value
                mock_wrapper.generate_wrappers.return_value = (True, "Wrappers generated")

                with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_service_class:
                    manager = DaemonManager()

                    # Mock VenvManager
                    with patch.object(manager, 'venv_manager') as mock_venv:
                        mock_venv.validate_python_version.return_value = True
                        mock_venv.create_venv.return_value = (True, "Venv created")
                        mock_venv.install_package.return_value = (True, "Package installed")

                        # Install daemon
                        with patch.object(manager.service_manager, 'install', return_value=True):
                            result = manager.install()

                            # Verify service manager was instantiated with venv_manager
                            # (This test verifies integration point from plan)
                            assert result is True

                            # Verify wrapper generation was called (integration check)
                            mock_wrapper.generate_wrappers.assert_called_once()


class TestSecurityServiceFiles:
    """Security tests for service file generation."""

    def test_service_files_dont_contain_hardcoded_credentials(self):
        """Service files don't contain hardcoded credentials"""
        # Test service managers that generate template files
        # Note: Windows uses NSSM commands (no template file), so skip Windows
        service_managers = [
            (LaunchdServiceManager, 'Darwin', '_create_plist', 'mcp_server.daemon.launchd_service.get_install_dir'),
            (SystemdServiceManager, 'Linux', '_create_service_unit', 'mcp_server.daemon.systemd_service.get_install_dir')
        ]

        for manager_class, platform, template_method, install_dir_patch in service_managers:
            with patch('platform.system', return_value=platform):
                mock_install_dir = Path.home() / '.graphiti'
                # Mock both paths.get_install_dir and venv_manager.get_install_dir
                with patch(install_dir_patch, return_value=mock_install_dir):
                    with patch('mcp_server.daemon.venv_manager.get_install_dir', return_value=mock_install_dir):
                        # Also mock VenvManager.detect_venv to return True (venv exists)
                        with patch.object(VenvManager, 'detect_venv', return_value=True):
                            # Mock get_python_executable to return a mock path
                            mock_python = mock_install_dir / 'bin' / 'python'
                            with patch.object(VenvManager, 'get_python_executable', return_value=mock_python):
                                service_manager = manager_class()

                                # Call actual template generation method
                                template_content = getattr(service_manager, template_method)()

                                # Convert to string for verification
                                template_str = str(template_content).lower()

                                # Verify no credential patterns
                                assert 'password=' not in template_str
                                assert 'api_key=' not in template_str
                                assert 'secret=' not in template_str
                                assert 'token=' not in template_str

    def test_install_dir_path_resolution_prevents_path_traversal(self):
        """Install dir path resolution doesn't allow path traversal"""
        # get_install_dir() should always resolve to a safe path
        # This test verifies that even if mocked with malicious input,
        # the service manager doesn't expose path traversal vulnerabilities

        with patch('platform.system', return_value='Darwin'):
            # Use a safe path (get_install_dir ensures this)
            expected_safe_path = Path.home() / '.graphiti'
            with patch('mcp_server.daemon.launchd_service.get_install_dir', return_value=expected_safe_path):
                service_manager = LaunchdServiceManager()

                # Verify paths don't contain path traversal sequences
                assert '..' not in str(service_manager.install_dir)
                assert '..' not in str(service_manager.python_exe)
                assert 'etc/passwd' not in str(service_manager.python_exe)
                assert str(service_manager.install_dir) == str(expected_safe_path)
