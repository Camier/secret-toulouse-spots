#!/usr/bin/env python3
"""
Unit tests for session manager
"""

import pytest
import json
from pathlib import Path
from scrapers.session_manager import SessionManager


class TestSessionManager:
    """Test session state management"""
    
    @pytest.fixture
    def temp_session_dir(self, tmp_path):
        """Create temporary session directory"""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir()
        return session_dir
    
    @pytest.fixture
    def session_manager(self, temp_session_dir, monkeypatch):
        """Create session manager with temp directory"""
        monkeypatch.setattr(Path, "mkdir", lambda self, **kwargs: None)
        manager = SessionManager("test_scraper")
        manager.state_file = temp_session_dir / "test_scraper_state.json"
        return manager
    
    @pytest.mark.unit
    def test_save_session_state(self, session_manager):
        """Test saving session state"""
        state = {
            "cookies": {"session_id": "abc123"},
            "last_run": "2024-01-15T10:00:00",
            "custom_data": {"page": 1}
        }
        
        session_manager.save_session_state(state)
        
        # Verify file was created
        assert session_manager.state_file.exists()
        
        # Verify content
        with open(session_manager.state_file) as f:
            saved_state = json.load(f)
        
        assert saved_state == state
    
    @pytest.mark.unit
    def test_load_session_state(self, session_manager):
        """Test loading session state"""
        # Create state file
        state = {
            "cookies": {"auth_token": "xyz789"},
            "last_run": "2024-01-15T12:00:00"
        }
        
        with open(session_manager.state_file, 'w') as f:
            json.dump(state, f)
        
        # Load state
        loaded_state = session_manager.load_session_state()
        
        assert loaded_state == state
    
    @pytest.mark.unit
    def test_load_nonexistent_state(self, session_manager):
        """Test loading when no state file exists"""
        loaded_state = session_manager.load_session_state()
        assert loaded_state is None
    
    @pytest.mark.unit
    def test_update_session_state(self, session_manager):
        """Test updating existing session state"""
        # Initial state
        initial_state = {
            "cookies": {"session": "old"},
            "page": 1
        }
        session_manager.save_session_state(initial_state)
        
        # Update state
        new_state = {
            "cookies": {"session": "new"},
            "page": 2,
            "last_item": "item123"
        }
        session_manager.save_session_state(new_state)
        
        # Verify update
        loaded = session_manager.load_session_state()
        assert loaded == new_state
    
    @pytest.mark.unit
    def test_clear_session_state(self, session_manager):
        """Test clearing session state"""
        # Create state
        session_manager.save_session_state({"data": "test"})
        assert session_manager.state_file.exists()
        
        # Clear state
        session_manager.clear_session_state()
        assert not session_manager.state_file.exists()
    
    @pytest.mark.unit
    def test_get_session_age(self, session_manager):
        """Test getting session age"""
        from datetime import datetime, timedelta
        
        # No session
        age = session_manager.get_session_age()
        assert age is None
        
        # Create session with timestamp
        past_time = (datetime.now() - timedelta(hours=2)).isoformat()
        session_manager.save_session_state({
            "last_run": past_time
        })
        
        age = session_manager.get_session_age()
        assert age is not None
        assert 7000 < age.total_seconds() < 7400  # ~2 hours
    
    @pytest.mark.unit
    def test_is_session_expired(self, session_manager):
        """Test session expiration check"""
        from datetime import datetime, timedelta
        
        # No session - considered expired
        assert session_manager.is_session_expired(max_age_hours=1) is True
        
        # Recent session
        session_manager.save_session_state({
            "last_run": datetime.now().isoformat()
        })
        assert session_manager.is_session_expired(max_age_hours=1) is False
        
        # Old session
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        session_manager.save_session_state({
            "last_run": old_time
        })
        assert session_manager.is_session_expired(max_age_hours=24) is True