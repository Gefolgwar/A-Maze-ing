"""Unit tests for config/settings parsing and output file format."""

import os
from typing import Dict, List

import pytest

# We import from the entry-point module.
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from a_maze_ing import parse_config, parse_settings, write_output  # noqa: E402


class TestParseConfig:
    """Tests for config.txt parsing."""

    def test_valid_config(self, tmp_path: object) -> None:
        """A properly formatted config should parse successfully."""
        cfg: str = (
            "WIDTH=20\n"
            "HEIGHT=15\n"
            "SEED=42\n"
            "PERFECT=True\n"
            "ENTRY=0,0\n"
            "EXIT=19,14\n"
            "OUTPUT_FILE=output_maze.txt\n"
        )
        p = os.path.join(str(tmp_path), "config.txt")
        with open(p, "w") as fh:
            fh.write(cfg)

        result: Dict[str, str] = parse_config(p)
        assert result["WIDTH"] == "20"
        assert result["HEIGHT"] == "15"
        assert result["SEED"] == "42"
        assert result["PERFECT"] == "True"
        assert result["ENTRY"] == "0,0"
        assert result["EXIT"] == "19,14"
        assert result["OUTPUT_FILE"] == "output_maze.txt"

    def test_missing_key_raises(self, tmp_path: object) -> None:
        """Missing a required key should raise ValueError."""
        cfg: str = "WIDTH=20\nHEIGHT=15\n"  # Missing many keys
        p = os.path.join(str(tmp_path), "config.txt")
        with open(p, "w") as fh:
            fh.write(cfg)
        with pytest.raises(ValueError, match="Missing required"):
            parse_config(p)

    def test_file_not_found(self) -> None:
        """Non-existent config file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_config("/nonexistent/config.txt")

    def test_malformed_line(self, tmp_path: object) -> None:
        """A line without '=' should raise ValueError."""
        cfg: str = "WIDTH=20\nBADLINE\n"
        p = os.path.join(str(tmp_path), "config.txt")
        with open(p, "w") as fh:
            fh.write(cfg)
        with pytest.raises(ValueError, match="Malformed"):
            parse_config(p)

    def test_comments_ignored(self, tmp_path: object) -> None:
        """Lines starting with # should be skipped."""
        cfg: str = (
            "# This is a comment\n"
            "WIDTH=20\n"
            "HEIGHT=15\n"
            "SEED=42\n"
            "PERFECT=True\n"
            "ENTRY=0,0\n"
            "EXIT=19,14\n"
            "OUTPUT_FILE=output_maze.txt\n"
        )
        p = os.path.join(str(tmp_path), "config.txt")
        with open(p, "w") as fh:
            fh.write(cfg)
        result: Dict[str, str] = parse_config(p)
        assert "# This is a comment" not in result


class TestParseSettings:
    """Tests for settings.ini parsing."""

    def test_valid_settings(self, tmp_path: object) -> None:
        """Proper INI content should be parsed."""
        ini: str = (
            "[UI]\n"
            "WallColor=#FFFFFF\n"
            "PathColor=#00FF00\n"
        )
        p = os.path.join(str(tmp_path), "settings.ini")
        with open(p, "w") as fh:
            fh.write(ini)
        result: Dict[str, str] = parse_settings(p)
        assert result["wallcolor"] == "#FFFFFF"
        assert result["pathcolor"] == "#00FF00"

    def test_missing_file_returns_empty(self) -> None:
        """Non-existent settings file should return empty dict."""
        result: Dict[str, str] = parse_settings("/nonexistent/settings.ini")
        assert result == {}


class TestOutputFile:
    """Tests for maze output file format."""

    def test_output_format(self, tmp_path: object) -> None:
        """Output file should match the expected format."""
        grid: List[List[int]] = [
            [0x9, 0x3, 0x5],
            [0xA, 0xC, 0x6],
            [0xC, 0x5, 0x6],
        ]
        p = os.path.join(str(tmp_path), "output.txt")
        write_output(p, grid, entry=(0, 0), exit_cell=(2, 2), solution="E E S S")

        with open(p, "r") as fh:
            lines: List[str] = fh.readlines()

        # Hex rows.
        assert lines[0].strip() == "935"
        assert lines[1].strip() == "AC6"
        assert lines[2].strip() == "C56"
        # Empty separator line.
        assert lines[3].strip() == ""
        # Entry/Exit.
        assert "Entry:" in lines[4]
        assert "Exit:" in lines[5]
        # Solution.
        assert lines[6].strip() == "EESS"
