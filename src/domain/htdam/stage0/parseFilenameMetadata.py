#!/usr/bin/env python3
"""
"""Pure function: Parse HVAC sensor metadata from CSV filename.

This module contains ZERO side effects:
- NO logging
- NO file I/O
- NO global state
- Pure parsing logic only

Handles GENERIC pattern: separate CSV per sensor with metadata embedded in filename.
NO assumptions about structure - just looks for ASHRAE abbreviations and descriptive text.
"""

import re
from typing import Dict, List, Tuple


# ASHRAE standard sensor abbreviations (complete segment matches only)
ASHRAE_ABBREVIATIONS = {
    'CHWST': 'Chilled Water Supply Temperature',
    'CHWRT': 'Chilled Water Return Temperature',
    'CDWST': 'Condenser Water Supply Temperature',
    'CDWRT': 'Condenser Water Return Temperature',
    'CHWF': 'Chilled Water Flow',
    'CDWF': 'Condenser Water Flow',
    'POWER': 'Electrical Power',
    'LOAD': 'Chiller Load',
}

# Descriptive text patterns that confirm ASHRAE abbreviation
DESCRIPTIVE_PATTERNS = {
    'CHWST': r'(?i)(leaving|supply|chw.*supply|chilled.*water.*supply)',
    'CHWRT': r'(?i)(entering|return|chw.*return|chilled.*water.*return)',
    'CDWST': r'(?i)(cdw.*supply|cond.*water.*supply|entering.*condenser)',
    'CDWRT': r'(?i)(cdw.*return|cond.*water.*return|leaving.*condenser)',
    'CHWF': r'(?i)(chw.*flow|chilled.*water.*flow|evap.*flow)',
    'CDWF': r'(?i)(cdw.*flow|cond.*water.*flow)',
    'POWER': r'(?i)(power|kilowatt|kw|electrical|demand)',
    'LOAD': r'(?i)(load|capacity|ton|refrigeration)',
}


def parse_filename_metadata(
    filepath: str
) -> Dict:
    """
    Pure function: Extract HVAC sensor metadata from filename.
    
    ZERO SIDE EFFECTS - pure parsing logic only.
    
    Args:
        filepath: Path to sensor CSV file
    
    Returns:
        Dict with:
        - sensor_type: 'CHWST', 'CHWRT', 'CDWRT', 'LOAD', 'POWER', etc.
        - ashrae_standard: Standard ASHRAE name
        - building: Building identifier (heuristic, may be None)
        - location: Location/floor identifier (heuristic, may be None)
        - equipment: Equipment identifier (heuristic, may be None)
        - confidence: float [0, 1]
        - parsing_method: 'ashrae_abbrev' | 'descriptive_text' | 'ambiguous'
        - segments: List of all filename segments
    
    GENERIC Approach - NO assumptions about structure:
    - Splits filename by underscore
    - Looks for ASHRAE abbreviations as complete segments
    - Validates with descriptive text if present
    - Does NOT assume any particular order or structure
    
    Parsing Strategy (generic, no structure assumptions):
    1. Extract filename without path/extension
    2. Split by underscore → segments
    3. Look for ASHRAE abbreviations as COMPLETE segments:
       - "CHWST" (complete segment) → ✅ Match
       - "Ch" in "Chiller" → ❌ NOT a match (substring, not complete segment)
    4. Validate with descriptive text if available in other segments
    5. If ambiguous → flag for manual review
    
    Key Principle: Match COMPLETE segments only, not substrings
    
    Examples:
        >>> filepath = "Site_..._CHWST_Leaving_Chilled_Water_Temperature_Sensor.csv"
        >>> result = parse_filename_metadata(filepath)
        >>> result['ashrae_standard']
        'CHWST'
        >>> result['confidence']
        1.0  # High: CHWST + "Leaving" confirm each other
        
        >>> filepath = "Site_..._Chiller_2_Load.csv"
        >>> result = parse_filename_metadata(filepath)
        >>> result['ashrae_standard']
        'LOAD'  # "Ch" in "Chiller" correctly ignored
        >>> result['confidence']
        0.85  # Medium: "Load" is generic, needs context
    """
    # Extract filename without path and extension
    filename = filepath.split('/')[-1]
    filename_no_ext = filename.replace('.csv', '').replace('.xlsx', '')
    
    # Split into segments
    segments = filename_no_ext.split('_')
    
    # Initialize result
    result = {
        'sensor_type': None,
        'ashrae_standard': None,
        'building': None,
        'location': None,
        'equipment': None,
        'confidence': 0.0,
        'parsing_method': 'none',
        'segments': segments,
        'raw_filename': filename
    }
    
    # Strategy 1: Look for ASHRAE abbreviations as complete segments
    ashrae_matches = []
    for i, segment in enumerate(segments):
        # Check if segment is exact ASHRAE abbreviation (case-insensitive)
        segment_upper = segment.upper()
        if segment_upper in ASHRAE_ABBREVIATIONS:
            ashrae_matches.append((i, segment_upper))
    
    # If we found ASHRAE abbreviation(s)
    if ashrae_matches:
        # Use first match (usually the sensor type appears once)
        segment_idx, ashrae_abbrev = ashrae_matches[0]
        
        result['sensor_type'] = ashrae_abbrev
        result['ashrae_standard'] = ashrae_abbrev
        result['parsing_method'] = 'ashrae_abbrev'
        result['confidence'] = 0.85  # Base confidence
        
        # Try to extract building/location/equipment from segments before ASHRAE
        if segment_idx >= 1:
            result['building'] = segments[0]
        if segment_idx >= 2:
            result['location'] = segments[1]
        if segment_idx >= 3:
            # Equipment is segments between location and ASHRAE
            result['equipment'] = '_'.join(segments[2:segment_idx])
        
        # Strategy 2: Validate with descriptive text (segments after ASHRAE)
        if segment_idx < len(segments) - 1:
            descriptive_text = '_'.join(segments[segment_idx + 1:])
            
            # Check if descriptive text confirms ASHRAE abbreviation
            if ashrae_abbrev in DESCRIPTIVE_PATTERNS:
                pattern = DESCRIPTIVE_PATTERNS[ashrae_abbrev]
                if re.search(pattern, descriptive_text):
                    result['confidence'] = 1.0  # High confidence - confirmed by description
                    result['parsing_method'] = 'ashrae_abbrev_validated'
    
    # Strategy 3: If no ASHRAE abbreviation, look in descriptive text
    if not ashrae_matches:
        full_text = '_'.join(segments)
        
        for ashrae_abbrev, pattern in DESCRIPTIVE_PATTERNS.items():
            if re.search(pattern, full_text):
                result['sensor_type'] = ashrae_abbrev
                result['ashrae_standard'] = ashrae_abbrev
                result['parsing_method'] = 'descriptive_text'
                result['confidence'] = 0.75  # Medium confidence - no explicit abbreviation
                break
    
    # If still no match, flag as ambiguous
    if result['sensor_type'] is None:
        result['parsing_method'] = 'ambiguous'
        result['confidence'] = 0.0
    
    return result


def extract_building_equipment(
    segments: List[str],
    ashrae_index: int
) -> Tuple[str, str, str]:
    """
    Pure function: Extract building, location, equipment from filename segments.
    
    ZERO SIDE EFFECTS
    
    Args:
        segments: List of filename segments (split by underscore)
        ashrae_index: Index where ASHRAE abbreviation was found
    
    Returns:
        Tuple of (building, location, equipment)
    
    Heuristic:
    - Building: First segment (or first few if compound)
    - Location: Segment with "Level", "Floor", "Zone" keywords
    - Equipment: Segments with "Chiller", "Pump", "Tower" keywords
    
    Examples:
        >>> segments = ['Company', '160', 'Ann', 'St', 'Level', '22', 'Chiller', '2', 'CHWST']
        >>> extract_building_equipment(segments, 8)
        ('Company_160_Ann_St', 'Level_22', 'Chiller_2')
    """
    building = None
    location = None
    equipment = None
    
    # Scan segments before ASHRAE index
    before_ashrae = segments[:ashrae_index]
    
    # Look for location keywords
    location_keywords = ['level', 'floor', 'zone', 'room', 'area']
    location_segments = []
    for i, seg in enumerate(before_ashrae):
        if any(kw in seg.lower() for kw in location_keywords):
            # Location is this segment + next (e.g., "Level" + "22")
            location_segments.append(seg)
            if i + 1 < len(before_ashrae):
                location_segments.append(before_ashrae[i + 1])
            break
    
    if location_segments:
        location = '_'.join(location_segments)
    
    # Look for equipment keywords
    equipment_keywords = ['chiller', 'pump', 'tower', 'fan', 'boiler', 'ahu']
    equipment_segments = []
    for i, seg in enumerate(before_ashrae):
        if any(kw in seg.lower() for kw in equipment_keywords):
            # Equipment is this segment + next (e.g., "Chiller" + "2")
            equipment_segments.append(seg)
            if i + 1 < len(before_ashrae):
                equipment_segments.append(before_ashrae[i + 1])
            break
    
    if equipment_segments:
        equipment = '_'.join(equipment_segments)
    
    # Building is everything else before location/equipment
    if location_segments or equipment_segments:
        # Find first index of location or equipment segments
        first_special_idx = len(before_ashrae)
        if location_segments:
            first_special_idx = min(first_special_idx, before_ashrae.index(location_segments[0]))
        if equipment_segments:
            first_special_idx = min(first_special_idx, before_ashrae.index(equipment_segments[0]))
        
        building = '_'.join(before_ashrae[:first_special_idx])
    else:
        # No special segments found, building is first segment
        building = before_ashrae[0] if before_ashrae else None
    
    return building, location, equipment
