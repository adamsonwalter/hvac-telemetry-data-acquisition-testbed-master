#!/usr/bin/env python3
"""
Unit tests for parseFilenameMetadata.py

Tests proven priority-based regex matching from TELEMETRY_PARSING_SPEC.md v1.1
NO MOCKS NEEDED - pure function testing!
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / 'src'))

from domain.htdam.stage0.parseFilenameMetadata import (
    parse_filename_metadata,
    detect_feed_type,
    FEED_TYPES,
    PATTERNS
)


class TestPriorityBasedMatching:
    """Test priority-based pattern matching - first match wins."""
    
    def test_cdwrt_priority_first(self):
        """CDWRT is checked first - condenser terms are highly specific."""
        filepath = "Condenser_Water_Return_Temp.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['feed_type'] == 'CDWRT'
        assert result['ashrae_standard'] == 'Condenser Water Return Temperature'
        assert result['confidence'] == 0.8  # Strong pattern match
        assert result['matched_pattern'] == r'COND|CDW'
    
    def test_chwst_exact_abbreviation(self):
        """CHWST with exact abbreviation gets confidence 1.0."""
        filepath = "Chiller_1_CHWST_Sensor.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['feed_type'] == 'CHWST'
        assert result['confidence'] == 1.0  # Exact abbreviation
        assert result['parsing_method'] == 'priority_regex'
    
    def test_chwst_supply_pattern(self):
        """CHWST detected from CHW_Supply pattern."""
        filepath = "CHW_Supply_Temp.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['feed_type'] == 'CHWST'
        assert result['confidence'] == 0.8  # Strong pattern
    
    def test_chwrt_exact_abbreviation(self):
        """CHWRT with exact abbreviation."""
        filepath = "Chiller_CHWRT_Entering_Water_Temp.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['feed_type'] == 'CHWRT'
        assert result['confidence'] == 1.0
    
    def test_power_from_load(self):
        """LOAD is classified as POWER per spec section 4.4."""
        filepath = "Chiller_2_Load.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['feed_type'] == 'POWER'
        assert result['ashrae_standard'] == 'Electrical Power'
        assert result['confidence'] == 0.6  # Generic pattern
    
    def test_flow_from_water_flow(self):
        """FLOW detected from Water_Flow pattern."""
        filepath = "Chiller_Water_Flow.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['feed_type'] == 'FLOW'
        assert result['ashrae_standard'] == 'Chilled Water Flow Rate'
        assert result['confidence'] == 1.0  # FLOW in filename


class TestChillerTrapAvoidance:
    """
    Critical: 'Ch' in 'Chiller' must NOT trigger false CHWST/CHWRT matches.
    This validates the uppercase + regex approach.
    """
    
    def test_chiller_does_not_trigger_chwst(self):
        """'Chiller' contains 'Ch' but should NOT match CHWST."""
        filepath = "Site_Chiller_2_Load.csv"
        result = parse_filename_metadata(filepath)
        
        # Must detect POWER (from LOAD), not CHWST
        assert result['feed_type'] == 'POWER'
        assert result['feed_type'] != 'CHWST'
        assert result['feed_type'] != 'CHWRT'
    
    def test_chiller_with_explicit_chwst(self):
        """Filename with both 'Chiller' and 'CHWST' - CHWST wins."""
        filepath = "Chiller_2_CHWST_Leaving_Temp.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['feed_type'] == 'CHWST'
        assert result['confidence'] == 1.0
    
    def test_multiple_ch_words(self):
        """Multiple words with 'Ch' should not cause false positives."""
        filepath = "China_Chemical_Chiller_Chamber_Status.csv"
        result = parse_filename_metadata(filepath)
        
        # STATUS has no match - should return None
        assert result['feed_type'] is None
        assert result['confidence'] == 0.0


class TestRealWorldFilenames:
    """Test with real industry filename patterns from test dataset."""
    
    def test_bartech_chwst(self):
        """Real BarTech CHWST filename."""
        filepath = "BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_CHWST_Leaving_Chilled_Water_Temperature_Sensor.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['feed_type'] == 'CHWST'
        assert result['confidence'] == 1.0
        assert result['building'] == 'BarTech'
        assert result['location'] == 'Level_22'
        assert result['equipment'] == 'Chiller_2'
    
    def test_bartech_chwrt(self):
        """Real BarTech CHWRT filename."""
        filepath = "BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_CHWRT_Entering_Chilled_Water_Temperature_Sensor.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['feed_type'] == 'CHWRT'
        assert result['confidence'] == 1.0
    
    def test_bartech_cdwrt(self):
        """Real BarTech CDWRT filename."""
        filepath = "BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_CDWRT_Entering_Condenser_Water_Temperature_Sensor.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['feed_type'] == 'CDWRT'
        assert result['confidence'] == 1.0
    
    def test_bartech_water_flow(self):
        """Real BarTech Water_Flow filename - tricky case."""
        filepath = "BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_Water_Flow.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['feed_type'] == 'FLOW'
        assert result['confidence'] == 1.0  # FLOW in uppercase filename
    
    def test_bartech_load(self):
        """Real BarTech Load filename - classified as POWER."""
        filepath = "BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_Load.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['feed_type'] == 'POWER'  # LOAD→POWER per spec
        assert result['confidence'] == 0.6
    
    def test_bartech_status_unknown(self):
        """Real BarTech Status filename - should be unknown."""
        filepath = "BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_Status.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['feed_type'] is None
        assert result['confidence'] == 0.0
        assert result['parsing_method'] == 'unknown'


class TestBMSVendorPatterns:
    """Test common BMS vendor naming conventions from spec section 6."""
    
    def test_honeywell_chwst(self):
        """Honeywell: CHW_Supply_Temp."""
        assert detect_feed_type('CHW_Supply_Temp.csv') == 'CHWST'
    
    def test_honeywell_chwrt(self):
        """Honeywell: CHW_Return_Temp."""
        assert detect_feed_type('CHW_Return_Temp.csv') == 'CHWRT'
    
    def test_honeywell_cdwrt(self):
        """Honeywell: CDW_Return_Temp."""
        assert detect_feed_type('CDW_Return_Temp.csv') == 'CDWRT'
    
    def test_johnson_controls_chwst(self):
        """Johnson Controls: Leaving_Chilled_Water_Temp (LWT)."""
        assert detect_feed_type('Leaving_Chilled_Water_Temp.csv') == 'CHWST'
    
    def test_johnson_controls_chwrt(self):
        """Johnson Controls: Entering_Chilled_Water_Temp (EWT)."""
        assert detect_feed_type('Entering_Chilled_Water_Temp.csv') == 'CHWRT'
    
    def test_siemens_chwst(self):
        """Siemens: CHW_ST."""
        assert detect_feed_type('CHW_ST.csv') == 'CHWST'
    
    def test_siemens_chwrt(self):
        """Siemens: CHW_RT."""
        assert detect_feed_type('CHW_RT.csv') == 'CHWRT'
    
    def test_siemens_power(self):
        """Siemens: Power_kW."""
        assert detect_feed_type('Power_kW.csv') == 'POWER'
    
    def test_trane_chwst(self):
        """Trane: CHWST."""
        assert detect_feed_type('CHWST.csv') == 'CHWST'
    
    def test_trane_flow(self):
        """Trane: Evap_Flow."""
        assert detect_feed_type('Evap_Flow.csv') == 'FLOW'


class TestFlowPatterns:
    """Test flow detection with various patterns."""
    
    def test_flow_keyword(self):
        """Detect from FLOW keyword."""
        assert detect_feed_type('CHW_Flow_Rate.csv') == 'FLOW'
    
    def test_gpm_unit(self):
        """Detect from GPM unit."""
        assert detect_feed_type('Flow_Sensor_GPM.csv') == 'FLOW'
    
    def test_lps_unit(self):
        """Detect from LPS unit."""
        assert detect_feed_type('Chiller_LPS.csv') == 'FLOW'
    
    def test_rate_keyword(self):
        """Detect from RATE keyword."""
        assert detect_feed_type('Water_Flow_Rate.csv') == 'FLOW'


class TestPowerPatterns:
    """Test power detection with various patterns."""
    
    def test_power_keyword(self):
        """Detect from POWER keyword."""
        assert detect_feed_type('Chiller_Power_Consumption.csv') == 'POWER'
    
    def test_kw_unit(self):
        """Detect from kW unit."""
        assert detect_feed_type('Total_kW.csv') == 'POWER'
    
    def test_electrical_keyword(self):
        """Detect from ELECTRICAL keyword."""
        assert detect_feed_type('Electrical_Demand.csv') == 'POWER'
    
    def test_load_as_power(self):
        """LOAD keyword classified as POWER."""
        assert detect_feed_type('Cooling_Load.csv') == 'POWER'
    
    def test_energy_keyword(self):
        """Detect from ENERGY keyword."""
        assert detect_feed_type('Energy_Meter_Chiller_1.csv') == 'POWER'


class TestEdgeCases:
    """Test edge cases and ambiguous patterns."""
    
    def test_unknown_filename(self):
        """Filename with no matching pattern."""
        result = parse_filename_metadata('Chiller_Status.csv')
        
        assert result['feed_type'] is None
        assert result['confidence'] == 0.0
        assert result['parsing_method'] == 'unknown'
        assert result['matched_pattern'] is None
    
    def test_case_insensitive(self):
        """Matching is case-insensitive via uppercase normalization."""
        assert detect_feed_type('chwst_sensor.csv') == 'CHWST'
        assert detect_feed_type('CHW_SUPPLY.csv') == 'CHWST'
        assert detect_feed_type('Chw_Return.csv') == 'CHWRT'
    
    def test_abbreviated_filename(self):
        """Very short filename."""
        result = parse_filename_metadata('CHWST.csv')
        
        assert result['feed_type'] == 'CHWST'
        assert result['confidence'] == 1.0
    
    def test_ambiguous_supply_and_return(self):
        """Filename with both SUPPLY and RETURN - first match wins."""
        # Per spec: first occurrence determines classification
        result = parse_filename_metadata('CHW_Supply_and_Return.csv')
        
        # CHWST checked before CHWRT in priority order
        assert result['feed_type'] == 'CHWST'
    
    def test_file_extension_stripped_csv(self):
        """CSV extensions are properly stripped."""
        assert detect_feed_type('CHWST.csv') == 'CHWST'
        assert detect_feed_type('chwst.csv') == 'CHWST'
        assert detect_feed_type('CHW_Supply.csv') == 'CHWST'
    
    def test_file_extension_stripped_xlsx(self):
        """XLSX extensions are properly stripped."""
        assert detect_feed_type('CHWST.xlsx') == 'CHWST'
        assert detect_feed_type('chwst.XLSX') == 'CHWST'
        assert detect_feed_type('CHW_Supply.xlsx') == 'CHWST'
    
    def test_file_extension_stripped_txt(self):
        """TXT extensions are properly stripped."""
        assert detect_feed_type('CHWST.txt') == 'CHWST'
        assert detect_feed_type('CHW_Return.TXT') == 'CHWRT'


class TestMetadataExtraction:
    """Test building/location/equipment heuristic extraction."""
    
    def test_metadata_extraction_full(self):
        """Extract all metadata: building, location, equipment."""
        filepath = "BarTech_160_Ann_St_Level_22_Chiller_2_CHWST.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['building'] == 'BarTech'
        assert result['location'] == 'Level_22'
        assert result['equipment'] == 'Chiller_2'
    
    def test_metadata_no_location(self):
        """Extract metadata when location keyword not present."""
        filepath = "Site_A_Pump_1_Flow.csv"
        result = parse_filename_metadata(filepath)
        
        assert result['building'] == 'Site'
        assert result['location'] is None
        assert result['equipment'] == 'Pump_1'
    
    def test_segments_preserved(self):
        """Segments are preserved for debugging."""
        result = parse_filename_metadata('A_B_C_CHWST.csv')
        
        assert result['segments'] == ['A', 'B', 'C', 'CHWST']
    
    def test_raw_filename_preserved(self):
        """Raw filename preserved without path."""
        result = parse_filename_metadata('/path/to/CHWST.csv')
        
        assert result['raw_filename'] == 'CHWST.csv'


class TestXLSXFiles:
    """Test XLSX file handling (multi-column format)."""
    
    def test_xlsx_chwst(self):
        """XLSX file with CHWST pattern."""
        result = parse_filename_metadata('Monash_Chiller_Data_CHWST.xlsx')
        assert result['feed_type'] == 'CHWST'
        assert result['confidence'] == 1.0
    
    def test_xlsx_chwrt(self):
        """XLSX file with CHWRT pattern."""
        result = parse_filename_metadata('Building_A_CHW_Return.xlsx')
        assert result['feed_type'] == 'CHWRT'
        assert result['confidence'] == 0.8
    
    def test_xlsx_power(self):
        """XLSX file with power data."""
        result = parse_filename_metadata('Chiller_Power_kW.xlsx')
        assert result['feed_type'] == 'POWER'
    
    def test_xlsx_flow(self):
        """XLSX file with flow data."""
        result = parse_filename_metadata('CHW_Flow_GPM.xlsx')
        assert result['feed_type'] == 'FLOW'
    
    def test_xlsx_mixed_case_extension(self):
        """XLSX with mixed case extension."""
        assert detect_feed_type('CHWST.XlSx') == 'CHWST'
        assert detect_feed_type('Power.XLSX') == 'POWER'
    
    def test_xlsx_multisheet_assumption(self):
        """XLSX files may contain multiple sensors per sheet."""
        # Note: parseFilenameMetadata only looks at filename
        # Multi-sheet/multi-column handling happens in hooks layer
        result = parse_filename_metadata('Monash_All_Sensors.xlsx')
        assert result['feed_type'] is None  # Generic name, no sensor type
        assert result['confidence'] == 0.0


class TestSimplifiedInterface:
    """Test simplified detect_feed_type() interface."""
    
    def test_detect_feed_type_chwst(self):
        """Simplified interface returns just feed type string."""
        assert detect_feed_type('CHWST.csv') == 'CHWST'
    
    def test_detect_feed_type_chwrt(self):
        assert detect_feed_type('CHWRT.csv') == 'CHWRT'
    
    def test_detect_feed_type_cdwrt(self):
        assert detect_feed_type('Condenser_Water_Return.csv') == 'CDWRT'
    
    def test_detect_feed_type_power(self):
        assert detect_feed_type('Power_kW.csv') == 'POWER'
    
    def test_detect_feed_type_flow(self):
        assert detect_feed_type('CHW_Flow.csv') == 'FLOW'
    
    def test_detect_feed_type_unknown(self):
        """Unknown returns None."""
        assert detect_feed_type('Status.csv') is None


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
