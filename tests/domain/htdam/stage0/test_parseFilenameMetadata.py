#!/usr/bin/env python3
"""
Unit tests for parseFilenameMetadata.py

Tests industry-standard HVAC filename parsing with focus on trap avoidance.
NO MOCKS NEEDED - pure function testing!
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / 'src'))

from domain.htdam.stage0.parseFilenameMetadata import (
    parse_filename_metadata,
    ASHRAE_ABBREVIATIONS
)


class TestFilenameParsingBasics:
    """Test basic filename parsing functionality."""
    
    def test_chwst_with_validation(self):
        """Test CHWST detection with descriptive text validation."""
        filepath = "Site_160_Ann_St_Level_22_Chiller_2_CHWST_Leaving_Chilled_Water_Temperature_Sensor.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['ashrae_standard'] == 'CHWST'
        assert result['sensor_type'] == 'CHWST'
        assert result['confidence'] == 1.0  # High - validated by "Leaving"
        assert result['parsing_method'] == 'ashrae_abbrev_validated'
    
    def test_chwrt_with_validation(self):
        """Test CHWRT detection with descriptive text validation."""
        filepath = "Site_Level_22_Chiller_2_CHWRT_Entering_Chilled_Water_Temperature_Sensor.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['ashrae_standard'] == 'CHWRT'
        assert result['sensor_type'] == 'CHWRT'
        assert result['confidence'] == 1.0  # High - validated by "Entering"
        assert result['parsing_method'] == 'ashrae_abbrev_validated'
    
    def test_load_simple(self):
        """Test LOAD detection in simple filename."""
        filepath = "Building_Chiller_2_Load.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['ashrae_standard'] == 'LOAD'
        assert result['sensor_type'] == 'LOAD'
        assert result['confidence'] >= 0.75  # Medium-high confidence
    
    def test_power_with_validation(self):
        """Test POWER detection with descriptive text."""
        filepath = "Site_Equipment_POWER_Electrical_Demand_Kilowatts.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['ashrae_standard'] == 'POWER'
        assert result['confidence'] == 1.0  # High - validated by "Kilowatts"


class TestChillerTrapAvoidance:
    """
    Critical tests: "Ch" in "Chiller" must NOT be detected as CHWST/CHWRT.
    This is the PRIMARY trap to avoid.
    """
    
    def test_chiller_does_not_trigger_chwst(self):
        """CRITICAL: 'Ch' in 'Chiller' must NOT match CHWST."""
        filepath = "Site_Level_22_Chiller_2_Load.csv"
        result = parse_filename_metadata(filepath)
        
        # Must detect LOAD, not CHWST
        assert result['ashrae_standard'] == 'LOAD'
        assert result['ashrae_standard'] != 'CHWST'
        assert result['ashrae_standard'] != 'CHWRT'
        
        # "Chiller" should be in equipment, not sensor type
        # (equipment parsing would be in extract_building_equipment function)
    
    def test_chiller_word_vs_chwst_abbrev(self):
        """Test distinction between 'Chiller' (equipment) and 'CHWST' (sensor)."""
        # Filename with both "Chiller" AND "CHWST"
        filepath = "Site_Chiller_2_CHWST_Leaving_Temperature.csv"
        result = parse_filename_metadata(filepath)
        
        # Must detect CHWST (complete segment), not be confused by "Ch" in "Chiller"
        assert result['ashrae_standard'] == 'CHWST'
        assert result['confidence'] == 1.0  # Validated by "Leaving"
    
    def test_multiple_ch_words_no_false_positive(self):
        """Test filename with multiple words containing 'Ch'."""
        filepath = "China_Chemical_Plant_Chiller_Chamber_Load.csv"
        result = parse_filename_metadata(filepath)
        
        # Must detect LOAD only, not be confused by multiple "Ch" occurrences
        assert result['ashrae_standard'] == 'LOAD'
        assert 'Ch' not in result['ashrae_standard']  # No partial matches


class TestRealWorldPatterns:
    """Test with real-world industry filename patterns."""
    
    def test_bartech_style_chwst(self):
        """Test industry-standard pattern (similar to test dataset)."""
        filepath = "Company_160_Ann_St_Level_22_MSSB_Chiller_2_CHWST_Leaving_Chilled_Water_Temperature_Sensor.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['ashrae_standard'] == 'CHWST'
        assert result['confidence'] == 1.0
        assert result['building'] == 'Company'
    
    def test_bartech_style_chwrt(self):
        """Test industry-standard pattern for CHWRT."""
        filepath = "Company_160_Ann_St_Level_22_MSSB_Chiller_2_CHWRT_Entering_Chilled_Water_Temperature_Sensor.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['ashrae_standard'] == 'CHWRT'
        assert result['confidence'] == 1.0
    
    def test_bartech_style_load(self):
        """Test industry-standard pattern for Load."""
        filepath = "Company_160_Ann_St_Level_22_MSSB_Chiller_2_Load.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['ashrae_standard'] == 'LOAD'
        # "Ch" in "Chiller" correctly ignored!
        assert result['confidence'] >= 0.75


class TestEdgeCases:
    """Test edge cases and ambiguous filenames."""
    
    def test_no_ashrae_abbreviation(self):
        """Test filename without ASHRAE abbreviation."""
        filepath = "Building_Equipment_Temperature.csv"
        result = parse_filename_metadata(filepath)
        
        # Should try descriptive text parsing
        assert result['confidence'] <= 0.75  # Lower confidence without abbreviation
    
    def test_multiple_ashrae_in_filename(self):
        """Test filename with multiple ASHRAE abbreviations (ambiguous)."""
        filepath = "Site_CHWST_vs_CHWRT_Comparison.csv"
        result = parse_filename_metadata(filepath)
        
        # Should use first match
        assert result['ashrae_standard'] in ['CHWST', 'CHWRT']
        # Note: This is ambiguous - in real use, would need manual review
    
    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        filepath = "Site_Equipment_chwst_temperature.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['ashrae_standard'] == 'CHWST'
        assert result['sensor_type'] == 'CHWST'
    
    def test_abbreviated_filename(self):
        """Test very short filename."""
        filepath = "CHWST.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['ashrae_standard'] == 'CHWST'
        assert result['confidence'] >= 0.85


class TestDescriptiveTextFallback:
    """Test parsing when ASHRAE abbreviation is not present."""
    
    def test_leaving_water_temp_without_abbrev(self):
        """Test detection from 'Leaving' keyword without CHWST abbreviation."""
        filepath = "Site_Chiller_Leaving_Chilled_Water_Temperature.csv"
        result = parse_filename_metadata(filepath)
        
        # Should detect CHWST from descriptive text
        assert result['ashrae_standard'] == 'CHWST'
        assert result['parsing_method'] == 'descriptive_text'
        assert result['confidence'] == 0.75  # Medium - no explicit abbreviation
    
    def test_entering_water_temp_without_abbrev(self):
        """Test detection from 'Entering' keyword without CHWRT abbreviation."""
        filepath = "Site_Entering_Chilled_Water_Temp.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['ashrae_standard'] == 'CHWRT'
        assert result['parsing_method'] == 'descriptive_text'
    
    def test_power_from_kilowatt_keyword(self):
        """Test POWER detection from 'kilowatt' keyword."""
        filepath = "Building_Demand_Kilowatts.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['ashrae_standard'] == 'POWER'
        assert result['parsing_method'] == 'descriptive_text'


class TestSegmentExtraction:
    """Test extraction of building/location/equipment segments."""
    
    def test_segments_extracted(self):
        """Test that filename segments are properly extracted."""
        filepath = "Company_160_Ann_St_Level_22_MSSB_Chiller_2_CHWST_Leaving_Chilled_Water_Temperature_Sensor.csv"
        result = parse_filename_metadata(filepath)
        
        # Segments should be split by underscore
        assert 'segments' in result
        assert len(result['segments']) > 0
        assert 'Company' in result['segments']
        assert 'CHWST' in result['segments']
    
    def test_raw_filename_preserved(self):
        """Test that raw filename is preserved in metadata."""
        filepath = "/path/to/Site_CHWST_Temp.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['raw_filename'] == 'Site_CHWST_Temp.csv'


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
