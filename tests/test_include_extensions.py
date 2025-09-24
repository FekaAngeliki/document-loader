"""Test the include_extensions functionality in FileSystemSource"""

import pytest
import tempfile
from pathlib import Path
from src.implementations.file_system_source import FileSystemSource


class TestIncludeExtensions:
    """Test cases for include_extensions feature"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files with various extensions
            files = [
                "document.pdf",
                "spreadsheet.xlsx",
                "text.txt",
                "image.jpg",
                "backup.bak",
                "temp.tmp",
                "UPPERCASE.PDF",
                "mixed.Docx"
            ]
            
            for filename in files:
                Path(tmpdir, filename).touch()
            
            # Create subdirectory with more files
            subdir = Path(tmpdir, "subdir")
            subdir.mkdir()
            Path(subdir, "nested.pdf").touch()
            Path(subdir, "nested.txt").touch()
            
            yield tmpdir
    
    def test_include_extensions_only(self, temp_dir):
        """Test using only include_extensions"""
        config = {
            "root_path": temp_dir,
            "include_extensions": [".pdf", ".xlsx"]
        }
        
        source = FileSystemSource(config)
        
        # Test individual files
        assert source._should_include("document.pdf") is True
        assert source._should_include("spreadsheet.xlsx") is True
        assert source._should_include("text.txt") is False
        assert source._should_include("image.jpg") is False
    
    def test_include_extensions_case_insensitive(self, temp_dir):
        """Test that extension matching is case-insensitive"""
        config = {
            "root_path": temp_dir,
            "include_extensions": [".pdf", ".docx"]
        }
        
        source = FileSystemSource(config)
        
        # Should match regardless of case
        assert source._should_include("UPPERCASE.PDF") is True
        assert source._should_include("mixed.Docx") is True
    
    def test_include_and_exclude_extensions(self, temp_dir):
        """Test combining include and exclude extensions"""
        config = {
            "root_path": temp_dir,
            "include_extensions": [".pdf", ".txt", ".xlsx"],
            "exclude_extensions": [".tmp", ".bak"]
        }
        
        source = FileSystemSource(config)
        
        # Include extensions allow these
        assert source._should_include("document.pdf") is True
        assert source._should_include("text.txt") is True
        
        # Exclude extensions reject these even if extension not in include list
        assert source._should_include("backup.bak") is False
        assert source._should_include("temp.tmp") is False
        
        # Not in include list
        assert source._should_include("image.jpg") is False
    
    def test_include_extensions_with_patterns(self, temp_dir):
        """Test include_extensions combined with patterns"""
        config = {
            "root_path": temp_dir,
            "include_patterns": ["subdir/**"],
            "include_extensions": [".pdf"]
        }
        
        source = FileSystemSource(config)
        
        # Must match both pattern and extension
        assert source._should_include("subdir/nested.pdf") is True
        assert source._should_include("subdir/nested.txt") is False
        assert source._should_include("document.pdf") is False  # Not in pattern
    
    def test_extension_normalization(self, temp_dir):
        """Test that extensions are normalized (with or without dot)"""
        config = {
            "root_path": temp_dir,
            "include_extensions": ["pdf", ".xlsx"]  # Mixed with/without dot
        }
        
        source = FileSystemSource(config)
        
        # Both should work regardless of input format
        assert source._should_include("document.pdf") is True
        assert source._should_include("spreadsheet.xlsx") is True
    
    def test_empty_include_extensions(self, temp_dir):
        """Test that empty include_extensions allows all files"""
        config = {
            "root_path": temp_dir,
            "include_extensions": []
        }
        
        source = FileSystemSource(config)
        
        # All files should be allowed with default pattern "*"
        assert source._should_include("document.pdf") is True
        assert source._should_include("text.txt") is True
        assert source._should_include("image.jpg") is True
    
    def test_precedence_exclude_before_include(self, temp_dir):
        """Test that exclude_extensions is checked before include_extensions"""
        config = {
            "root_path": temp_dir,
            "include_extensions": [".pdf", ".bak"],
            "exclude_extensions": [".bak"]
        }
        
        source = FileSystemSource(config)
        
        # Even though .bak is in include_extensions, exclude takes precedence
        assert source._should_include("document.pdf") is True
        assert source._should_include("backup.bak") is False
    
    @pytest.mark.asyncio
    async def test_list_files_with_include_extensions(self, temp_dir):
        """Test that list_files respects include_extensions"""
        config = {
            "root_path": temp_dir,
            "include_extensions": [".pdf", ".txt"]
        }
        
        source = FileSystemSource(config)
        await source.initialize()
        
        files = await source.list_files()
        file_names = [f.uri for f in files]
        
        # Should only include PDF and TXT files
        assert "document.pdf" in file_names
        assert "text.txt" in file_names
        assert "subdir/nested.pdf" in file_names
        assert "subdir/nested.txt" in file_names
        assert "UPPERCASE.PDF" in file_names
        
        # Should not include other extensions
        assert "spreadsheet.xlsx" not in file_names
        assert "image.jpg" not in file_names
        assert "backup.bak" not in file_names