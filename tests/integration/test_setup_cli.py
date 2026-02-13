"""Integration tests for CLI setup script.

Tests the interactive profile creation workflow, input validation,
and profile persistence.
"""

import tempfile
import os
import pytest
from unittest.mock import patch
from io import StringIO


class TestSetupCLIProfileCreation:
    """Test CLI setup script profile creation flow."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        # Initialize schema
        from src.lib.database import initialize_database
        initialize_database(path)

        yield path

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    def test_profile_creation_flow(self, temp_db):
        """Test complete profile creation flow (T018)."""
        # This test will fail until we implement src/cli/setup_plants.py
        from src.cli.setup_plants import prompt_plant_name, prompt_sensor_channel, prompt_moisture_threshold
        from src.lib.database import create_plant_profile, load_all_profiles

        # Simulate user input
        with patch('builtins.input', side_effect=['Basil']):
            plant_name = prompt_plant_name(temp_db)
            assert plant_name == 'Basil'

        with patch('builtins.input', side_effect=['0']):
            sensor_channel = prompt_sensor_channel(temp_db)
            assert sensor_channel == 0

        with patch('builtins.input', side_effect=['45.0']):
            threshold = prompt_moisture_threshold()
            assert threshold == 45.0

        # Create profile
        create_plant_profile(plant_name, sensor_channel, threshold, temp_db)

        # Verify profile was created
        profiles = load_all_profiles(temp_db)
        assert len(profiles) == 1
        assert profiles[0].plant_name == 'Basil'


class TestSetupCLIInputValidation:
    """Test CLI input validation."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        from src.lib.database import initialize_database
        initialize_database(path)

        yield path

        if os.path.exists(path):
            os.unlink(path)

    def test_empty_plant_name_rejected(self, temp_db):
        """Test that empty plant name is rejected and prompts again (T019)."""
        from src.cli.setup_plants import prompt_plant_name

        # Simulate empty input, then valid input
        with patch('builtins.input', side_effect=['', 'Basil']):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                plant_name = prompt_plant_name(temp_db)

                # Should prompt again after empty input
                output = mock_stdout.getvalue()
                assert '❌' in output or 'cannot be empty' in output.lower()
                assert plant_name == 'Basil'

    def test_long_plant_name_rejected(self, temp_db):
        """Test that plant name > 50 characters is rejected (T019)."""
        from src.cli.setup_plants import prompt_plant_name

        long_name = 'A' * 51  # 51 characters
        valid_name = 'Basil'

        # Simulate long input, then valid input
        with patch('builtins.input', side_effect=[long_name, valid_name]):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                plant_name = prompt_plant_name(temp_db)

                # Should prompt again after long input
                output = mock_stdout.getvalue()
                assert '❌' in output or 'too long' in output.lower()
                assert plant_name == valid_name

    def test_invalid_moisture_threshold_rejected(self, temp_db):
        """Test that invalid threshold values are rejected (T019)."""
        from src.cli.setup_plants import prompt_moisture_threshold

        # Simulate invalid inputs, then valid input
        with patch('builtins.input', side_effect=['-10', '150', '45.0']):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                threshold = prompt_moisture_threshold()

                # Should prompt again after invalid inputs
                output = mock_stdout.getvalue()
                assert '❌' in output or 'must be' in output.lower()
                assert threshold == 45.0

    def test_duplicate_plant_name_rejected(self, temp_db):
        """Test that duplicate plant names are rejected."""
        from src.cli.setup_plants import prompt_plant_name
        from src.lib.database import create_plant_profile

        # Create existing profile
        create_plant_profile('Basil', 0, 45.0, temp_db)

        # Try to create duplicate, then use different name
        with patch('builtins.input', side_effect=['Basil', 'Tomato']):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                plant_name = prompt_plant_name(temp_db)

                # Should prompt again after duplicate
                output = mock_stdout.getvalue()
                assert '❌' in output or 'already exists' in output.lower()
                assert plant_name == 'Tomato'

    def test_duplicate_sensor_channel_rejected(self, temp_db):
        """Test that duplicate sensor channels are rejected."""
        from src.cli.setup_plants import prompt_sensor_channel
        from src.lib.database import create_plant_profile

        # Create existing profile on channel 0
        create_plant_profile('Basil', 0, 45.0, temp_db)

        # Try to use channel 0 again, then use channel 1
        with patch('builtins.input', side_effect=['0', '1']):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                channel = prompt_sensor_channel(temp_db)

                # Should prompt again after duplicate channel
                output = mock_stdout.getvalue()
                assert '❌' in output or 'already assigned' in output.lower()
                assert channel == 1


class TestSetupCLIProfilePersistence:
    """Test profile persistence across database reconnections."""

    def test_profile_persistence_across_restarts(self):
        """Test that profiles persist across database reconnections (T020)."""
        from src.lib.database import initialize_database, create_plant_profile, load_all_profiles

        # Create temporary database
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        try:
            # Initialize and create profile
            initialize_database(path)
            create_plant_profile('Basil', 0, 45.0, path)

            # Verify profile exists
            profiles1 = load_all_profiles(path)
            assert len(profiles1) == 1
            assert profiles1[0].plant_name == 'Basil'

            # Simulate restart by loading profiles again (new connection)
            profiles2 = load_all_profiles(path)
            assert len(profiles2) == 1
            assert profiles2[0].plant_name == 'Basil'
            assert profiles2[0].sensor_channel == 0
            assert profiles2[0].acceptable_moisture_level == 45.0

        finally:
            if os.path.exists(path):
                os.unlink(path)
