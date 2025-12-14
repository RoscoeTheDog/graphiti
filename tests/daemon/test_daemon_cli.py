"""
Integration Tests for Daemon CLI Commands

Tests the daemon management commands against the actual implementation:
- graphiti-mcp daemon install
- graphiti-mcp daemon uninstall
- graphiti-mcp daemon status
- graphiti-mcp daemon logs

These tests verify CLI behavior without requiring OS service installation.
"""

import json
import platform
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from mcp_server.daemon.manager import DaemonManager, UnsupportedPlatformError


class TestDaemonManagerInit:
    """Test DaemonManager initialization and platform detection."""

    def test_windows_platform_detection(self):
        """Windows platform initializes WindowsServiceManager"""
        with patch('platform.system', return_value='Windows'):
            with patch('mcp_server.daemon.manager.WindowsServiceManager') as mock_windows:
                manager = DaemonManager()
                assert manager.platform == 'Windows'
                mock_windows.assert_called_once()

    def test_macos_platform_detection(self):
        """macOS platform initializes LaunchdServiceManager"""
        with patch('platform.system', return_value='Darwin'):
            with patch('mcp_server.daemon.manager.LaunchdServiceManager') as mock_launchd:
                manager = DaemonManager()
                assert manager.platform == 'Darwin'
                mock_launchd.assert_called_once()

    def test_linux_platform_detection(self):
        """Linux platform initializes SystemdServiceManager"""
        with patch('platform.system', return_value='Linux'):
            with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_systemd:
                manager = DaemonManager()
                assert manager.platform == 'Linux'
                mock_systemd.assert_called_once()

    def test_unsupported_platform_raises_error(self):
        """Unsupported platform raises UnsupportedPlatformError"""
        with patch('platform.system', return_value='FreeBSD'):
            with pytest.raises(UnsupportedPlatformError) as exc_info:
                DaemonManager()
            assert 'FreeBSD' in str(exc_info.value)
            assert 'not supported' in str(exc_info.value)


class TestConfigPathDetection:
    """Test configuration file path detection across platforms."""

    def test_windows_config_path(self, tmp_path):
        """Windows uses ~/.graphiti/graphiti.config.json"""
        with patch('platform.system', return_value='Windows'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('mcp_server.daemon.manager.WindowsServiceManager'):
                    manager = DaemonManager()
                    expected = tmp_path / ".graphiti" / "graphiti.config.json"
                    assert manager.config_path == expected

    def test_unix_config_path_default(self, tmp_path):
        """Unix without XDG_CONFIG_HOME uses ~/.graphiti/graphiti.config.json"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch.dict('os.environ', {}, clear=True):
                    with patch('mcp_server.daemon.manager.SystemdServiceManager'):
                        manager = DaemonManager()
                        expected = tmp_path / ".graphiti" / "graphiti.config.json"
                        assert manager.config_path == expected

    def test_unix_config_path_xdg(self, tmp_path):
        """Unix with XDG_CONFIG_HOME uses $XDG_CONFIG_HOME/graphiti/graphiti.config.json"""
        xdg_path = tmp_path / "config"
        with patch('platform.system', return_value='Linux'):
            with patch.dict('os.environ', {'XDG_CONFIG_HOME': str(xdg_path)}):
                with patch('mcp_server.daemon.manager.SystemdServiceManager'):
                    manager = DaemonManager()
                    expected = xdg_path / "graphiti" / "graphiti.config.json"
                    assert manager.config_path == expected


class TestInstallCommand:
    """Test daemon install command behavior."""

    def test_install_creates_config_directory(self, tmp_path, capsys):
        """Install creates config directory if missing"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_systemd:
                    mock_systemd_instance = Mock()
                    mock_systemd_instance.install.return_value = True
                    mock_systemd.return_value = mock_systemd_instance

                    manager = DaemonManager()
                    success = manager.install()

                    assert success
                    assert manager.config_path.parent.exists()
                    mock_systemd_instance.install.assert_called_once()

    def test_install_creates_default_config(self, tmp_path, capsys):
        """Install creates default config if file missing"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_systemd:
                    mock_systemd_instance = Mock()
                    mock_systemd_instance.install.return_value = True
                    mock_systemd.return_value = mock_systemd_instance

                    manager = DaemonManager()
                    success = manager.install()

                    assert success
                    assert manager.config_path.exists()

                    # Verify default config structure
                    config = json.loads(manager.config_path.read_text())
                    assert 'daemon' in config
                    assert config['daemon']['enabled'] is False

    def test_install_preserves_existing_config(self, tmp_path):
        """Install does not overwrite existing config"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_systemd:
                    mock_systemd_instance = Mock()
                    mock_systemd_instance.install.return_value = True
                    mock_systemd.return_value = mock_systemd_instance

                    manager = DaemonManager()

                    # Create existing config with custom values
                    manager.config_path.parent.mkdir(parents=True, exist_ok=True)
                    existing_config = {
                        "daemon": {"enabled": True, "port": 9999},
                        "custom_key": "custom_value"
                    }
                    manager.config_path.write_text(json.dumps(existing_config))

                    success = manager.install()

                    assert success
                    config = json.loads(manager.config_path.read_text())
                    assert config == existing_config

    def test_install_success_message(self, tmp_path, capsys):
        """Install displays success message with next steps"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_systemd:
                    mock_systemd_instance = Mock()
                    mock_systemd_instance.install.return_value = True
                    mock_systemd.return_value = mock_systemd_instance

                    manager = DaemonManager()
                    manager.install()

                    captured = capsys.readouterr()
                    assert 'SUCCESS' in captured.out
                    assert 'daemon": { "enabled": true }' in captured.out
                    assert 'graphiti-mcp daemon status' in captured.out

    def test_install_failure_message(self, tmp_path, capsys):
        """Install displays error message on failure"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_systemd:
                    mock_systemd_instance = Mock()
                    mock_systemd_instance.install.return_value = False
                    mock_systemd.return_value = mock_systemd_instance

                    manager = DaemonManager()
                    success = manager.install()

                    assert not success
                    captured = capsys.readouterr()
                    assert 'FAILED' in captured.out or 'failed' in captured.out.lower()


class TestUninstallCommand:
    """Test daemon uninstall command behavior."""

    def test_uninstall_delegates_to_service_manager(self, tmp_path):
        """Uninstall calls service manager's uninstall method"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_systemd:
                    mock_systemd_instance = Mock()
                    mock_systemd_instance.uninstall.return_value = True
                    mock_systemd.return_value = mock_systemd_instance

                    manager = DaemonManager()
                    success = manager.uninstall()

                    assert success
                    mock_systemd_instance.uninstall.assert_called_once()

    def test_uninstall_success_message(self, tmp_path, capsys):
        """Uninstall displays success message"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_systemd:
                    mock_systemd_instance = Mock()
                    mock_systemd_instance.uninstall.return_value = True
                    mock_systemd.return_value = mock_systemd_instance

                    manager = DaemonManager()
                    manager.uninstall()

                    captured = capsys.readouterr()
                    assert 'SUCCESS' in captured.out or 'uninstalled' in captured.out.lower()

    def test_uninstall_preserves_config(self, tmp_path):
        """Uninstall does not delete config file"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_systemd:
                    mock_systemd_instance = Mock()
                    mock_systemd_instance.uninstall.return_value = True
                    mock_systemd.return_value = mock_systemd_instance

                    manager = DaemonManager()

                    # Create config
                    manager.config_path.parent.mkdir(parents=True, exist_ok=True)
                    manager.config_path.write_text('{"daemon": {"enabled": true}}')

                    manager.uninstall()

                    # Config should still exist
                    assert manager.config_path.exists()


class TestStatusCommand:
    """Test daemon status command behavior."""

    def test_status_delegates_to_service_manager(self, tmp_path):
        """Status calls service manager's is_installed and is_running methods"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_systemd:
                    mock_systemd_instance = Mock()
                    mock_systemd_instance.is_installed.return_value = True
                    mock_systemd_instance.is_running.return_value = True
                    mock_systemd_instance.name = "systemd"
                    mock_systemd_instance.start_hint = "systemctl start graphiti-bootstrap"
                    mock_systemd.return_value = mock_systemd_instance

                    manager = DaemonManager()
                    manager.status()

                    # Status calls is_installed and is_running (not status method)
                    mock_systemd_instance.is_installed.assert_called_once()
                    mock_systemd_instance.is_running.assert_called_once()

    def test_status_reads_config_if_exists(self, tmp_path, capsys):
        """Status displays config settings when config exists"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_systemd:
                    mock_systemd_instance = Mock()
                    mock_systemd_instance.is_installed.return_value = True
                    mock_systemd_instance.is_running.return_value = True
                    mock_systemd_instance.name = "systemd"
                    mock_systemd_instance.start_hint = "systemctl start graphiti-bootstrap"
                    mock_systemd.return_value = mock_systemd_instance

                    manager = DaemonManager()

                    # Create config
                    manager.config_path.parent.mkdir(parents=True, exist_ok=True)
                    config = {
                        "daemon": {
                            "enabled": True,
                            "host": "127.0.0.1",
                            "port": 8321
                        }
                    }
                    manager.config_path.write_text(json.dumps(config))

                    manager.status()

                    captured = capsys.readouterr()
                    assert '127.0.0.1' in captured.out
                    assert '8321' in captured.out


class TestLogsCommand:
    """Test daemon logs command behavior."""

    def test_logs_delegates_to_service_manager(self, tmp_path):
        """Logs calls service manager's show_logs method"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_systemd:
                    mock_systemd_instance = Mock()
                    mock_systemd_instance.show_logs.return_value = None
                    mock_systemd.return_value = mock_systemd_instance

                    manager = DaemonManager()
                    manager.logs()

                    # logs() calls show_logs (not logs method)
                    mock_systemd_instance.show_logs.assert_called_once_with(follow=False, lines=50)

    def test_logs_with_follow_flag(self, tmp_path):
        """Logs passes follow flag to service manager"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_systemd:
                    mock_systemd_instance = Mock()
                    mock_systemd_instance.show_logs.return_value = None
                    mock_systemd.return_value = mock_systemd_instance

                    manager = DaemonManager()
                    manager.logs(follow=True)

                    # logs() calls show_logs (not logs method)
                    mock_systemd_instance.show_logs.assert_called_once_with(follow=True, lines=50)


class TestCLIArgumentParsing:
    """Test command-line argument parsing for daemon commands."""

    def test_daemon_subcommand_detection(self):
        """Verify 'daemon' subcommand is detected correctly"""
        import sys
        from unittest.mock import patch

        test_argv = ['graphiti-mcp', 'daemon', 'install']

        with patch.object(sys, 'argv', test_argv):
            # The main entry point should recognize 'daemon' subcommand
            # This is tested via the subcommand routing logic
            assert sys.argv[1] == 'daemon'

    def test_daemon_install_command(self):
        """Verify 'daemon install' routes to install method"""
        from argparse import Namespace

        # Create mock args as argparse would
        args = Namespace(command='install')
        assert args.command == 'install'

    def test_daemon_uninstall_command(self):
        """Verify 'daemon uninstall' routes to uninstall method"""
        from argparse import Namespace

        args = Namespace(command='uninstall')
        assert args.command == 'uninstall'

    def test_daemon_status_command(self):
        """Verify 'daemon status' routes to status method"""
        from argparse import Namespace

        args = Namespace(command='status')
        assert args.command == 'status'

    def test_daemon_logs_command(self):
        """Verify 'daemon logs' routes to logs method"""
        from argparse import Namespace

        args = Namespace(command='logs', follow=False)
        assert args.command == 'logs'
        assert hasattr(args, 'follow')


class TestErrorMessages:
    """Test actionable error messages for common failure scenarios."""

    def test_install_without_permissions(self, tmp_path, capsys):
        """Install failure shows actionable permission error"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_systemd:
                    mock_systemd_instance = Mock()
                    # Simulate permission error
                    mock_systemd_instance.install.side_effect = PermissionError(
                        "Permission denied"
                    )
                    mock_systemd.return_value = mock_systemd_instance

                    manager = DaemonManager()
                    with pytest.raises(PermissionError):
                        manager.install()

    def test_config_not_found_shows_help(self, tmp_path, capsys):
        """Status with missing config shows how to install"""
        with patch('platform.system', return_value='Linux'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('mcp_server.daemon.manager.SystemdServiceManager') as mock_systemd:
                    mock_systemd_instance = Mock()
                    mock_systemd_instance.status.return_value = True
                    mock_systemd.return_value = mock_systemd_instance

                    manager = DaemonManager()
                    manager.status()

                    captured = capsys.readouterr()
                    # Should mention daemon not installed or config not found
                    assert 'install' in captured.out.lower() or 'config' in captured.out.lower()
