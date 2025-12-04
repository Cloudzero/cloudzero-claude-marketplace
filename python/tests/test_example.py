# Copyright (c) CloudZero - ALL RIGHTS RESERVED - PROPRIETARY AND CONFIDENTIAL
# Unauthorized copying of this file and/or project, via any medium is strictly prohibited.
# Direct all questions to legal@cloudzero.com
#
# CHANGELOG: 2025-11-17 - Initial creation (erik.peterson)

"""Example test file for demonstrating pytest setup."""


def test_example():
    """Example test that always passes."""
    assert True


def test_version_exists():
    """Test that package version is defined."""
    from src import __version__

    assert __version__ is not None
    assert isinstance(__version__, str)
