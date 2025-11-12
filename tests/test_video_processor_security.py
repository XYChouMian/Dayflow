"""Security tests for VideoProcessor frame rate parsing.

This test suite verifies that the eval() vulnerability has been fixed
and that malicious input cannot execute arbitrary code.
"""

import pytest
from dayflow.core.video_processor import VideoProcessor


class TestFrameRateParsingSecurity:
    """Test suite for secure frame rate parsing."""

    @pytest.fixture
    def processor(self):
        """Create a VideoProcessor instance."""
        return VideoProcessor()

    def test_normal_frame_rates(self, processor):
        """Test parsing of normal frame rate values."""
        # Common frame rates
        assert processor._parse_frame_rate("30/1") == 30.0
        assert processor._parse_frame_rate("60/1") == 60.0
        assert processor._parse_frame_rate("25/1") == 25.0

        # Cinema frame rate (23.976 fps)
        result = processor._parse_frame_rate("24000/1001")
        assert 23.9 < result < 24.0

        # PAL frame rate
        result = processor._parse_frame_rate("30000/1001")
        assert 29.9 < result < 30.0

    def test_simple_numeric_format(self, processor):
        """Test parsing of simple numeric formats."""
        assert processor._parse_frame_rate("30") == 30.0
        assert processor._parse_frame_rate("60") == 60.0
        assert processor._parse_frame_rate("23.976") == 23.976

    def test_edge_cases(self, processor):
        """Test edge cases and error handling."""
        # Empty string
        assert processor._parse_frame_rate("") == 0.0

        # None value (converted to empty string)
        assert processor._parse_frame_rate("") == 0.0

        # Division by zero
        assert processor._parse_frame_rate("30/0") == 0.0

        # Invalid format
        assert processor._parse_frame_rate("invalid") == 0.0
        assert processor._parse_frame_rate("30/abc") == 0.0

    def test_code_injection_attempts(self, processor):
        """Test that code injection attempts are safely handled.

        This is the critical security test - ensures that malicious
        video metadata cannot execute arbitrary code.
        """
        # These would have executed with eval(), but should now return 0.0

        # System command injection
        malicious_input = "__import__('os').system('echo hacked')"
        result = processor._parse_frame_rate(malicious_input)
        assert result == 0.0

        # File read attempt
        malicious_input = "open('/etc/passwd').read()"
        result = processor._parse_frame_rate(malicious_input)
        assert result == 0.0

        # Module import attempt
        malicious_input = "__import__('subprocess').run(['whoami'])"
        result = processor._parse_frame_rate(malicious_input)
        assert result == 0.0

        # Python code execution
        malicious_input = "exec('import sys; sys.exit()')"
        result = processor._parse_frame_rate(malicious_input)
        assert result == 0.0

        # Lambda expression
        malicious_input = "(lambda: __import__('os').system('rm -rf /'))()"
        result = processor._parse_frame_rate(malicious_input)
        assert result == 0.0

    def test_malformed_fraction_formats(self, processor):
        """Test handling of malformed fraction inputs."""
        # Multiple slashes - should fail gracefully
        assert processor._parse_frame_rate("30/1/2") == 0.0

        # Spaces in fraction
        assert processor._parse_frame_rate("30 / 1") == 30.0

        # Extra whitespace
        assert processor._parse_frame_rate("  30/1  ") == 30.0

    def test_negative_values(self, processor):
        """Test handling of negative values."""
        # Negative values should still parse (though unusual)
        assert processor._parse_frame_rate("-30/1") == -30.0
        assert processor._parse_frame_rate("30/-1") == -30.0

    def test_very_large_values(self, processor):
        """Test handling of very large numeric values."""
        # Should not crash or cause overflow
        result = processor._parse_frame_rate("1000000/1")
        assert result == 1000000.0

    def test_float_division_precision(self, processor):
        """Test floating point division precision."""
        # Ensure proper floating point division
        result = processor._parse_frame_rate("1/3")
        assert abs(result - 0.333333) < 0.00001


class TestSecurityRegression:
    """Tests to ensure the eval() vulnerability stays fixed."""

    def test_eval_not_used(self):
        """Verify that eval() is not used in the codebase."""
        import inspect
        import ast
        import textwrap
        from dayflow.core.video_processor import VideoProcessor

        # Get the source code of the _parse_frame_rate method
        source = inspect.getsource(VideoProcessor._parse_frame_rate)

        # Dedent to remove indentation
        source = textwrap.dedent(source)

        # Parse the source to get the AST (Abstract Syntax Tree)
        tree = ast.parse(source)

        # Check that no Call nodes contain eval or exec
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in ['eval', 'exec'], \
                        f"Dangerous function {node.func.id}() found in _parse_frame_rate"

    def test_get_video_info_uses_safe_parser(self):
        """Verify that get_video_info uses the safe parser."""
        import inspect
        from dayflow.core.video_processor import VideoProcessor

        # Get the source code of get_video_info
        source = inspect.getsource(VideoProcessor.get_video_info)

        # Ensure it uses the safe parser
        assert "_parse_frame_rate" in source, "get_video_info should use _parse_frame_rate"
        assert "eval(" not in source, "eval() should not be used in get_video_info"
