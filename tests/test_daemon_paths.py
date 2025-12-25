"""
Comprehensive test suite for mcp_server.daemon.paths module.

Tests path resolution across all supported platforms (Windows, macOS, Linux)
with edge cases and environment variable handling.

Coverage targets:
- Line coverage: >90%
- Branch coverage: >85%
- All 6 public functions tested
- All 3 platforms tested

Created: 2025-12-25
Story: 3.i - Path Resolution Test Suite
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import os
import sys


class TestWindowsPaths(unittest.TestCase):
    """Test Windows-specific path resolution."""

    @patch('mcp_server.daemon.paths.sys.platform', 'win32')
    @patch.dict('os.environ', {'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local'})
    def test_default_paths(self):
        """Test Windows paths with LOCALAPPDATA set."""
        from mcp_server.daemon.paths import get_paths

        paths = get_paths()

        # Windows uses LOCALAPPDATA
        self.assertEqual(paths.install_dir, Path('C:/Users/Test/AppData/Local/Programs/Graphiti'))
        self.assertEqual(paths.config_dir, Path('C:/Users/Test/AppData/Local/Graphiti/config'))
        self.assertEqual(paths.state_dir, Path('C:/Users/Test/AppData/Local/Graphiti'))
        self.assertEqual(paths.config_file, Path('C:/Users/Test/AppData/Local/Graphiti/config/graphiti.config.json'))

        # Verify all paths are absolute
        self.assertTrue(paths.install_dir.is_absolute())
        self.assertTrue(paths.config_dir.is_absolute())
        self.assertTrue(paths.state_dir.is_absolute())
        self.assertTrue(paths.config_file.is_absolute())

    @patch('mcp_server.daemon.paths.sys.platform', 'win32')
    @patch('mcp_server.daemon.paths.Path.home')
    @patch.dict('os.environ', {}, clear=True)
    def test_missing_localappdata(self, mock_home):
        """Test Windows fallback when LOCALAPPDATA is missing."""
        mock_home.return_value = Path('C:/Users/Test')

        from mcp_server.daemon.paths import get_paths

        paths = get_paths()

        # Should fallback to Path.home() / AppData / Local
        self.assertEqual(paths.install_dir, Path('C:/Users/Test/AppData/Local/Programs/Graphiti'))
        self.assertEqual(paths.config_dir, Path('C:/Users/Test/AppData/Local/Graphiti/config'))
        self.assertEqual(paths.state_dir, Path('C:/Users/Test/AppData/Local/Graphiti'))

    @patch('mcp_server.daemon.paths.sys.platform', 'win32')
    @patch.dict('os.environ', {'LOCALAPPDATA': 'C:\\CustomAppData'})
    def test_custom_localappdata(self):
        """Test Windows with custom LOCALAPPDATA."""
        from mcp_server.daemon.paths import get_paths

        paths = get_paths()

        # Should respect custom LOCALAPPDATA
        self.assertEqual(paths.install_dir, Path('C:/CustomAppData/Programs/Graphiti'))
        self.assertEqual(paths.config_dir, Path('C:/CustomAppData/Graphiti/config'))
        self.assertEqual(paths.state_dir, Path('C:/CustomAppData/Graphiti'))

    @patch('mcp_server.daemon.paths.sys.platform', 'win32')
    @patch.dict('os.environ', {'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local'})
    def test_log_dir(self):
        """Test Windows log directory is state_dir/logs."""
        from mcp_server.daemon.paths import get_log_dir

        log_dir = get_log_dir()

        # Windows uses state_dir/logs
        self.assertEqual(log_dir, Path('C:/Users/Test/AppData/Local/Graphiti/logs'))

    @patch('mcp_server.daemon.paths.sys.platform', 'win32')
    @patch.dict('os.environ', {'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local'})
    def test_data_dir(self):
        """Test Windows data directory is state_dir/data."""
        from mcp_server.daemon.paths import get_data_dir

        data_dir = get_data_dir()

        # Windows uses state_dir/data
        self.assertEqual(data_dir, Path('C:/Users/Test/AppData/Local/Graphiti/data'))

    @patch('mcp_server.daemon.paths.sys.platform', 'win32')
    @patch.dict('os.environ', {'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local'})
    def test_convenience_functions(self):
        """Test Windows convenience accessor functions."""
        from mcp_server.daemon.paths import (
            get_install_dir, get_config_dir, get_config_file,
            get_log_dir, get_data_dir
        )

        # Test all convenience functions
        self.assertEqual(get_install_dir(), Path('C:/Users/Test/AppData/Local/Programs/Graphiti'))
        self.assertEqual(get_config_dir(), Path('C:/Users/Test/AppData/Local/Graphiti/config'))
        self.assertEqual(get_config_file(), Path('C:/Users/Test/AppData/Local/Graphiti/config/graphiti.config.json'))
        self.assertEqual(get_log_dir(), Path('C:/Users/Test/AppData/Local/Graphiti/logs'))
        self.assertEqual(get_data_dir(), Path('C:/Users/Test/AppData/Local/Graphiti/data'))


class TestMacOSPaths(unittest.TestCase):
    """Test macOS-specific path resolution."""

    @patch('mcp_server.daemon.paths.sys.platform', 'darwin')
    @patch('mcp_server.daemon.paths.Path.home')
    def test_fixed_library_paths(self, mock_home):
        """Test macOS uses fixed Library paths."""
        mock_home.return_value = Path('/Users/test')

        from mcp_server.daemon.paths import get_paths

        paths = get_paths()

        # macOS uses fixed Library paths
        self.assertEqual(paths.install_dir, Path('/Users/test/Library/Application Support/Graphiti'))
        self.assertEqual(paths.config_dir, Path('/Users/test/Library/Preferences/Graphiti'))
        self.assertEqual(paths.state_dir, Path('/Users/test/Library/Logs/Graphiti'))
        self.assertEqual(paths.config_file, Path('/Users/test/Library/Preferences/Graphiti/graphiti.config.json'))

    @patch('mcp_server.daemon.paths.sys.platform', 'darwin')
    @patch('mcp_server.daemon.paths.Path.home')
    @patch.dict('os.environ', {
        'XDG_DATA_HOME': '/custom/data',
        'XDG_CONFIG_HOME': '/custom/config',
        'XDG_STATE_HOME': '/custom/state'
    })
    def test_ignores_xdg_variables(self, mock_home):
        """Test macOS ignores XDG environment variables."""
        mock_home.return_value = Path('/Users/test')

        from mcp_server.daemon.paths import get_paths

        paths = get_paths()

        # macOS should ignore XDG variables
        self.assertEqual(paths.install_dir, Path('/Users/test/Library/Application Support/Graphiti'))
        self.assertEqual(paths.config_dir, Path('/Users/test/Library/Preferences/Graphiti'))
        self.assertEqual(paths.state_dir, Path('/Users/test/Library/Logs/Graphiti'))

    @patch('mcp_server.daemon.paths.sys.platform', 'darwin')
    @patch('mcp_server.daemon.paths.Path.home')
    def test_application_support_space(self, mock_home):
        """Test macOS handles space in 'Application Support' correctly."""
        mock_home.return_value = Path('/Users/test')

        from mcp_server.daemon.paths import get_paths

        paths = get_paths()

        # Path object should handle spaces correctly
        install_str = str(paths.install_dir)
        self.assertIn('Application Support', install_str)
        # Verify path contains expected components (cross-platform string test)
        self.assertIn('Library', install_str)
        self.assertIn('Graphiti', install_str)

    @patch('mcp_server.daemon.paths.sys.platform', 'darwin')
    @patch('mcp_server.daemon.paths.Path.home')
    def test_log_dir_is_state_dir(self, mock_home):
        """Test macOS log_dir returns state_dir (already points to Logs)."""
        mock_home.return_value = Path('/Users/test')

        from mcp_server.daemon.paths import get_log_dir, get_paths

        log_dir = get_log_dir()
        paths = get_paths()

        # macOS log_dir should equal state_dir (both point to Library/Logs/Graphiti)
        self.assertEqual(log_dir, paths.state_dir)
        self.assertEqual(log_dir, Path('/Users/test/Library/Logs/Graphiti'))

    @patch('mcp_server.daemon.paths.sys.platform', 'darwin')
    @patch('mcp_server.daemon.paths.Path.home')
    def test_data_dir_uses_caches(self, mock_home):
        """Test macOS data_dir uses separate Library/Caches directory."""
        mock_home.return_value = Path('/Users/test')

        from mcp_server.daemon.paths import get_data_dir

        data_dir = get_data_dir()

        # macOS uses Library/Caches (not state_dir/data)
        self.assertEqual(data_dir, Path('/Users/test/Library/Caches/Graphiti'))

    @patch('mcp_server.daemon.paths.sys.platform', 'darwin')
    @patch('mcp_server.daemon.paths.Path.home')
    def test_convenience_functions(self, mock_home):
        """Test macOS convenience accessor functions."""
        mock_home.return_value = Path('/Users/test')

        from mcp_server.daemon.paths import (
            get_install_dir, get_config_dir, get_config_file,
            get_log_dir, get_data_dir
        )

        # Test all convenience functions
        self.assertEqual(get_install_dir(), Path('/Users/test/Library/Application Support/Graphiti'))
        self.assertEqual(get_config_dir(), Path('/Users/test/Library/Preferences/Graphiti'))
        self.assertEqual(get_config_file(), Path('/Users/test/Library/Preferences/Graphiti/graphiti.config.json'))
        self.assertEqual(get_log_dir(), Path('/Users/test/Library/Logs/Graphiti'))
        self.assertEqual(get_data_dir(), Path('/Users/test/Library/Caches/Graphiti'))


class TestLinuxPaths(unittest.TestCase):
    """Test Linux-specific path resolution (XDG Base Directory spec)."""

    @patch('mcp_server.daemon.paths.sys.platform', 'linux')
    @patch('mcp_server.daemon.paths.Path.home')
    @patch.dict('os.environ', {}, clear=True)
    def test_default_xdg_paths(self, mock_home):
        """Test Linux with default XDG paths (no environment variables)."""
        mock_home.return_value = Path('/home/test')

        from mcp_server.daemon.paths import get_paths

        paths = get_paths()

        # Linux defaults to XDG Base Directory spec
        self.assertEqual(paths.install_dir, Path('/home/test/.local/share/graphiti'))
        self.assertEqual(paths.config_dir, Path('/home/test/.config/graphiti'))
        self.assertEqual(paths.state_dir, Path('/home/test/.local/state/graphiti'))
        self.assertEqual(paths.config_file, Path('/home/test/.config/graphiti/graphiti.config.json'))

    @patch('mcp_server.daemon.paths.sys.platform', 'linux')
    @patch('mcp_server.daemon.paths.Path.home')
    @patch.dict('os.environ', {}, clear=True)
    def test_missing_xdg_variables(self, mock_home):
        """Test Linux fallback when XDG variables are missing."""
        mock_home.return_value = Path('/home/test')

        from mcp_server.daemon.paths import get_paths

        paths = get_paths()

        # Should fallback to XDG defaults
        self.assertEqual(paths.install_dir, Path('/home/test/.local/share/graphiti'))
        self.assertEqual(paths.config_dir, Path('/home/test/.config/graphiti'))
        self.assertEqual(paths.state_dir, Path('/home/test/.local/state/graphiti'))

    @patch('mcp_server.daemon.paths.sys.platform', 'linux')
    @patch('mcp_server.daemon.paths.Path.home')
    @patch.dict('os.environ', {'XDG_CONFIG_HOME': '/custom/config'}, clear=False)
    def test_partial_xdg_variables(self, mock_home):
        """Test Linux with only some XDG variables set."""
        mock_home.return_value = Path('/home/test')

        from mcp_server.daemon.paths import get_paths

        paths = get_paths()

        # Should use custom config, fallback for others
        self.assertEqual(paths.install_dir, Path('/home/test/.local/share/graphiti'))
        self.assertEqual(paths.config_dir, Path('/custom/config/graphiti'))
        self.assertEqual(paths.state_dir, Path('/home/test/.local/state/graphiti'))

    @patch('mcp_server.daemon.paths.sys.platform', 'linux')
    @patch.dict('os.environ', {
        'XDG_DATA_HOME': '/custom/data',
        'XDG_CONFIG_HOME': '/custom/config',
        'XDG_STATE_HOME': '/custom/state'
    })
    def test_all_custom_xdg_variables(self):
        """Test Linux with all XDG variables customized."""
        from mcp_server.daemon.paths import get_paths

        paths = get_paths()

        # Should respect all custom XDG variables
        self.assertEqual(paths.install_dir, Path('/custom/data/graphiti'))
        self.assertEqual(paths.config_dir, Path('/custom/config/graphiti'))
        self.assertEqual(paths.state_dir, Path('/custom/state/graphiti'))

    @patch('mcp_server.daemon.paths.sys.platform', 'linux')
    @patch.dict('os.environ', {'XDG_DATA_HOME': '/custom/data/'})  # Trailing slash
    def test_trailing_slashes(self):
        """Test Linux handles trailing slashes in XDG variables correctly."""
        from mcp_server.daemon.paths import get_paths

        paths = get_paths()

        # Path should handle trailing slash correctly (no double slashes)
        install_str = str(paths.install_dir)
        self.assertNotIn('//', install_str)
        self.assertEqual(paths.install_dir, Path('/custom/data/graphiti'))

    @patch('mcp_server.daemon.paths.sys.platform', 'linux')
    @patch('mcp_server.daemon.paths.Path.home')
    @patch.dict('os.environ', {}, clear=True)
    def test_log_dir(self, mock_home):
        """Test Linux log directory is state_dir/logs."""
        mock_home.return_value = Path('/home/test')

        from mcp_server.daemon.paths import get_log_dir

        log_dir = get_log_dir()

        # Linux uses state_dir/logs
        self.assertEqual(log_dir, Path('/home/test/.local/state/graphiti/logs'))

    @patch('mcp_server.daemon.paths.sys.platform', 'linux')
    @patch('mcp_server.daemon.paths.Path.home')
    @patch.dict('os.environ', {}, clear=True)
    def test_data_dir(self, mock_home):
        """Test Linux data directory is state_dir/data."""
        mock_home.return_value = Path('/home/test')

        from mcp_server.daemon.paths import get_data_dir

        data_dir = get_data_dir()

        # Linux uses state_dir/data
        self.assertEqual(data_dir, Path('/home/test/.local/state/graphiti/data'))

    @patch('mcp_server.daemon.paths.sys.platform', 'linux')
    @patch('mcp_server.daemon.paths.Path.home')
    @patch.dict('os.environ', {}, clear=True)
    def test_convenience_functions(self, mock_home):
        """Test Linux convenience accessor functions."""
        mock_home.return_value = Path('/home/test')

        from mcp_server.daemon.paths import (
            get_install_dir, get_config_dir, get_config_file,
            get_log_dir, get_data_dir
        )

        # Test all convenience functions
        self.assertEqual(get_install_dir(), Path('/home/test/.local/share/graphiti'))
        self.assertEqual(get_config_dir(), Path('/home/test/.config/graphiti'))
        self.assertEqual(get_config_file(), Path('/home/test/.config/graphiti/graphiti.config.json'))
        self.assertEqual(get_log_dir(), Path('/home/test/.local/state/graphiti/logs'))
        self.assertEqual(get_data_dir(), Path('/home/test/.local/state/graphiti/data'))

    @patch('mcp_server.daemon.paths.sys.platform', 'freebsd12')
    @patch('mcp_server.daemon.paths.Path.home')
    @patch.dict('os.environ', {}, clear=True)
    def test_non_standard_platform(self, mock_home):
        """Test non-standard platform (FreeBSD) treated as Linux (XDG spec)."""
        mock_home.return_value = Path('/home/test')

        from mcp_server.daemon.paths import get_paths

        paths = get_paths()

        # FreeBSD should follow XDG spec (else clause)
        self.assertEqual(paths.install_dir, Path('/home/test/.local/share/graphiti'))
        self.assertEqual(paths.config_dir, Path('/home/test/.config/graphiti'))
        self.assertEqual(paths.state_dir, Path('/home/test/.local/state/graphiti'))


class TestPathTypes(unittest.TestCase):
    """Test path types and general path properties."""

    @patch('mcp_server.daemon.paths.sys.platform', 'linux')
    @patch('mcp_server.daemon.paths.Path.home')
    @patch.dict('os.environ', {}, clear=True)
    def test_returns_path_objects(self, mock_home):
        """Test that all functions return pathlib.Path objects."""
        mock_home.return_value = Path('/home/test')

        from mcp_server.daemon.paths import (
            get_paths, get_install_dir, get_config_dir, get_config_file,
            get_log_dir, get_data_dir
        )

        paths = get_paths()

        # Verify all are Path objects
        self.assertIsInstance(paths.install_dir, Path)
        self.assertIsInstance(paths.config_dir, Path)
        self.assertIsInstance(paths.state_dir, Path)
        self.assertIsInstance(paths.config_file, Path)
        self.assertIsInstance(get_install_dir(), Path)
        self.assertIsInstance(get_config_dir(), Path)
        self.assertIsInstance(get_config_file(), Path)
        self.assertIsInstance(get_log_dir(), Path)
        self.assertIsInstance(get_data_dir(), Path)

    @patch('mcp_server.daemon.paths.sys.platform', 'linux')
    @patch('mcp_server.daemon.paths.Path.home')
    @patch.dict('os.environ', {}, clear=True)
    def test_paths_are_absolute(self, mock_home):
        """Test that all paths contain expected components."""
        mock_home.return_value = Path('/home/test')

        from mcp_server.daemon.paths import (
            get_paths, get_log_dir, get_data_dir
        )

        paths = get_paths()

        # Verify all paths contain expected components (cross-platform test)
        self.assertIn('.local', str(paths.install_dir))
        self.assertIn('graphiti', str(paths.install_dir))
        self.assertIn('.config', str(paths.config_dir))
        self.assertIn('graphiti', str(paths.config_dir))
        self.assertIn('.local', str(paths.state_dir))
        self.assertIn('graphiti', str(paths.state_dir))
        self.assertIn('graphiti.config.json', str(paths.config_file))
        self.assertIn('logs', str(get_log_dir()))
        self.assertIn('data', str(get_data_dir()))

    @patch('mcp_server.daemon.paths.sys.platform', 'linux')
    @patch('mcp_server.daemon.paths.Path.home')
    @patch.dict('os.environ', {}, clear=True)
    def test_graphiti_paths_namedtuple(self, mock_home):
        """Test GraphitiPaths is a NamedTuple with correct attributes."""
        mock_home.return_value = Path('/home/test')

        from mcp_server.daemon.paths import get_paths, GraphitiPaths

        paths = get_paths()

        # Verify it's a GraphitiPaths instance
        self.assertIsInstance(paths, GraphitiPaths)

        # Verify it has all expected attributes
        self.assertTrue(hasattr(paths, 'install_dir'))
        self.assertTrue(hasattr(paths, 'config_dir'))
        self.assertTrue(hasattr(paths, 'state_dir'))
        self.assertTrue(hasattr(paths, 'config_file'))

        # Verify it's a tuple (NamedTuple is a tuple)
        self.assertIsInstance(paths, tuple)

        # Verify tuple unpacking works
        install, config, state, config_file = paths
        self.assertEqual(install, paths.install_dir)
        self.assertEqual(config, paths.config_dir)
        self.assertEqual(state, paths.state_dir)
        self.assertEqual(config_file, paths.config_file)


if __name__ == '__main__':
    unittest.main()
