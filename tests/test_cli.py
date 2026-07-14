"""Tests for CLI functionality."""

import pytest
from unittest.mock import MagicMock, call, patch
import argparse
import sys


class TestCLI:
    """Test CLI argument parsing and behavior."""
    
    @patch('app.main.start_glances')
    @patch('app.main.check_glances_running')
    @patch('uvicorn.run')
    def test_cli_default_behavior(self, mock_uvicorn, mock_check, mock_start):
        """Test CLI runs with default settings and auto-starts Glances."""
        mock_check.return_value = False
        
        # Import and run CLI
        from app.main import cli
        
        with patch('sys.argv', ['glancewatch']):
            with pytest.raises(SystemExit):
                cli()
        
        # Should check for Glances
        mock_check.assert_called_once()
        # Should start Glances when not running
        mock_start.assert_called_once()
        # Should start uvicorn with defaults
        mock_uvicorn.assert_called_once()
        call_kwargs = mock_uvicorn.call_args[1]
        assert call_kwargs['host'] == '0.0.0.0'
        assert call_kwargs['port'] == 8000
    
    @patch('app.main.start_glances')
    @patch('app.main.check_glances_running')
    @patch('uvicorn.run')
    def test_cli_ignore_glances_flag(self, mock_uvicorn, mock_check, mock_start):
        """Test --ignore-glances flag skips Glances management."""
        from app.main import cli
        
        with patch('sys.argv', ['glancewatch', '--ignore-glances']):
            with pytest.raises(SystemExit):
                cli()
        
        # Should NOT check or start Glances
        mock_check.assert_not_called()
        mock_start.assert_not_called()
        # Should still start uvicorn
        mock_uvicorn.assert_called_once()
    
    @patch('app.main.start_glances')
    @patch('app.main.check_glances_running')
    @patch('uvicorn.run')
    def test_cli_custom_port(self, mock_uvicorn, mock_check, mock_start):
        """Test --port flag changes server port."""
        mock_check.return_value = True
        
        from app.main import cli
        
        with patch('sys.argv', ['glancewatch', '--port', '9000']):
            with pytest.raises(SystemExit):
                cli()
        
        # Should use custom port
        mock_uvicorn.assert_called_once()
        call_kwargs = mock_uvicorn.call_args[1]
        assert call_kwargs['port'] == 9000
    
    @patch('app.main.start_glances')
    @patch('app.main.check_glances_running')
    @patch('uvicorn.run')
    def test_cli_custom_host(self, mock_uvicorn, mock_check, mock_start):
        """Test --host flag changes bind address."""
        mock_check.return_value = True
        
        from app.main import cli
        
        with patch('sys.argv', ['glancewatch', '--host', '127.0.0.1']):
            with pytest.raises(SystemExit):
                cli()
        
        # Should use custom host
        mock_uvicorn.assert_called_once()
        call_kwargs = mock_uvicorn.call_args[1]
        assert call_kwargs['host'] == '127.0.0.1'
    
    @patch('app.main.start_glances')
    @patch('app.main.check_glances_running')
    @patch('uvicorn.run')
    def test_cli_all_flags_combined(self, mock_uvicorn, mock_check, mock_start):
        """Test combining all CLI flags."""
        from app.main import cli
        
        with patch('sys.argv', ['glancewatch', '--ignore-glances', '--port', '9090', '--host', 'localhost']):
            with pytest.raises(SystemExit):
                cli()
        
        # Should NOT manage Glances
        mock_check.assert_not_called()
        mock_start.assert_not_called()
        
        # Should use custom settings
        mock_uvicorn.assert_called_once()
        call_kwargs = mock_uvicorn.call_args[1]
        assert call_kwargs['host'] == 'localhost'
        assert call_kwargs['port'] == 9090
    
    @patch('app.main.start_glances')
    @patch('app.main.check_glances_running')
    @patch('uvicorn.run')
    def test_cli_glances_already_running(self, mock_uvicorn, mock_check, mock_start):
        """Test CLI skips starting Glances when already running."""
        mock_check.return_value = True  # Glances already running
        
        from app.main import cli
        
        with patch('sys.argv', ['glancewatch']):
            with pytest.raises(SystemExit):
                cli()
        
        # Should check for Glances
        mock_check.assert_called_once()
        # Should NOT start Glances
        mock_start.assert_not_called()
        # Should start server
        mock_uvicorn.assert_called_once()
    
    @patch('builtins.print')
    @patch('app.main.start_glances')
    @patch('app.main.check_glances_running')
    @patch('uvicorn.run')
    def test_cli_glances_start_failure(self, mock_uvicorn, mock_check, mock_start, mock_print):
        """Test CLI handles Glances start failure gracefully."""
        mock_check.return_value = False
        mock_start.side_effect = Exception("Failed to start Glances")
        
        from app.main import cli
        
        with patch('sys.argv', ['glancewatch']):
            with pytest.raises(SystemExit):
                cli()
        
        # Should attempt to start Glances
        mock_start.assert_called_once()
        # Should print warning
        assert any("WARNING" in str(call) or "Failed" in str(call) for call in mock_print.call_args_list)
        # Should still start server despite Glances failure
        mock_uvicorn.assert_called_once()
    
    def test_cli_help_flag(self):
        """Test --help flag displays usage information."""
        from app.main import cli
        
        with patch('sys.argv', ['glancewatch', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                cli()
            
            # Help exits with code 0
            assert exc_info.value.code == 0
    
    @patch('uvicorn.run')
    def test_cli_invalid_port(self, mock_uvicorn):
        """Test CLI rejects invalid port numbers."""
        from app.main import cli
        
        with patch('sys.argv', ['glancewatch', '--port', 'invalid']):
            with pytest.raises(SystemExit) as exc_info:
                cli()
            
            # Should exit with error code
            assert exc_info.value.code != 0
            # Should NOT start uvicorn
            mock_uvicorn.assert_not_called()


class TestGlancesManagement:
    """Test Glances process management functions."""
    
    @patch('subprocess.run')
    def test_check_glances_running_success(self, mock_subprocess):
        """Test check_glances_running detects running Glances."""
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        from app.main import check_glances_running
        
        result = check_glances_running()
        
        assert result is True
        mock_subprocess.assert_called_once()
        # Should check with pgrep or ps
        cmd = mock_subprocess.call_args[0][0]
        assert 'glances' in ' '.join(cmd).lower()
    
    @patch('subprocess.run')
    def test_check_glances_not_running(self, mock_subprocess):
        """Test check_glances_running returns False when not running."""
        mock_subprocess.return_value = MagicMock(returncode=1)
        
        from app.main import check_glances_running
        
        result = check_glances_running()
        
        assert result is False
    
    @patch('subprocess.run')
    def test_check_glances_exception_handling(self, mock_subprocess):
        """Test check_glances_running handles exceptions."""
        mock_subprocess.side_effect = Exception("Command failed")
        
        from app.main import check_glances_running
        
        # Should return False on exception
        result = check_glances_running()
        assert result is False
    
    @patch('subprocess.Popen')
    def test_start_glances_success(self, mock_popen):
        """Test start_glances starts Glances server."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        from app.main import start_glances
        
        start_glances()
        
        # Should start Glances with web server
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert 'glances' in cmd
        assert '-w' in cmd  # Web server mode
    
    @patch('builtins.print')
    @patch('subprocess.Popen')
    def test_start_glances_failure(self, mock_popen, mock_print):
        """Test start_glances handles startup failure."""
        mock_popen.side_effect = Exception("Failed to start")
        
        from app.main import start_glances
        
        # Should handle exception gracefully and return False
        result = start_glances()
        assert result is False
    
    @patch('subprocess.Popen')
    @patch('time.sleep')
    def test_start_glances_waits_for_startup(self, mock_sleep, mock_popen):
        """Test start_glances waits for Glances to be ready."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        from app.main import start_glances
        
        start_glances()
        
        # Should wait a bit for Glances to start
        mock_sleep.assert_called()


class TestCLIIntegration:
    """Integration tests for CLI workflow."""
    
    @patch('subprocess.run')
    @patch('subprocess.Popen')
    @patch('uvicorn.run')
    def test_full_startup_workflow(self, mock_uvicorn, mock_popen, mock_run):
        """Test complete startup workflow: check Glances, start it, run server."""
        # Glances not running initially
        mock_run.return_value = MagicMock(returncode=1)
        mock_popen.return_value = MagicMock()
        
        from app.main import cli
        
        with patch('sys.argv', ['glancewatch', '--port', '8100']):
            with pytest.raises(SystemExit):
                cli()
        
        # Should check for Glances
        mock_run.assert_called()
        # Should start Glances
        mock_popen.assert_called()
        # Should start server
        mock_uvicorn.assert_called_once()
    
    @patch('subprocess.run')
    @patch('subprocess.Popen')
    @patch('uvicorn.run')
    def test_skip_glances_workflow(self, mock_uvicorn, mock_popen, mock_run):
        """Test workflow when skipping Glances management."""
        from app.main import cli
        
        with patch('sys.argv', ['glancewatch', '--ignore-glances']):
            with pytest.raises(SystemExit):
                cli()
        
        # Should NOT check or start Glances
        mock_run.assert_not_called()
        mock_popen.assert_not_called()
        # Should only start server
        mock_uvicorn.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
