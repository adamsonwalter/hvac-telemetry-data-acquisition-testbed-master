#!/usr/bin/env python3
"""
Pure function: Parse HVAC sensor metadata from CSV filename.

This module contains ZERO side effects:
- NO logging
- NO file I/O
- NO global state
- Pure parsing logic only

Implements proven priority-based regex matching from TELEMETRY_PARSING_SPEC.md.
See docs/TELEMETRY_PARSING_SPEC.md for complete specification and rationale.
"""

import re
from typing import Dict, List, Tuple, Optional


# Priority-based Feed Type Detection
# Based on proven specification: docs/TELEMETRY_PARSING_SPEC.md v1.1
# Patterns are evaluated sequentially - FIRST MATCH WINS

# Feed Type definitions (ASHRAE standard)
FEED_TYPES = {
    'CDWRT': 'Condenser Water Return Temperature',
    'CHWST': 'Chilled Water Supply Temperature',
    'CHWRT': 'Chilled Water Return Temperature',
    'POWER': 'Electrical Power',
    'FLOW': 'Chilled Water Flow Rate',
}

# Priority-ordered regex patterns
# Critical: CDWRT is checked FIRST because COND/CDW are highly specific
PATTERNS = [
    # Priority 1: CDWRT - Condenser terms are highly specific
    ('CDWRT', r'COND|CDW'),
    
    # Priority 2: CHWST - Supply/Leaving side
    ('CHWST', r'CHW.*SUPPLY|CHWST|CHW.*ST|SUPPLY.*TEMP|LEAVING.*TEMP|CHW.*LEAV'),
    
    # Priority 3: CHWRT - Return/Entering side
    ('CHWRT', r'CHW.*RETURN|CHWRT|CHW.*RT|RETURN.*TEMP|ENTERING.*TEMP|CHW.*ENT'),
    
    # Priority 4: POWER - Electrical consumption
    # Note: LOAD is classified as POWER (see spec section 4.4)
    ('POWER', r'POWER|KW|KILOWATT|WATT|ENERGY|ELEC|DEMAND|LOAD'),
    
    # Priority 5: FLOW - Volumetric flow rate
    ('FLOW', r'FLOW|GPM|LPS|L/S|LITRE|GALLON|RATE'),
]


def parse_filename_metadata(
    filepath: str
) -> Dict:
    """
    Pure function: Detect HVAC feed type from filename using priority-based regex.
    
    ZERO SIDE EFFECTS - pure parsing logic only.
    
    Implements proven specification from docs/TELEMETRY_PARSING_SPEC.md v1.1
    
    Algorithm:
    1. Normalize filename to UPPERCASE
    2. Strip file extension (.csv, .xlsx, .txt)
    3. Evaluate patterns sequentially (first match wins)
    4. Extract building/location/equipment metadata (heuristic)
    
    Args:
        filepath: Path to sensor CSV/XLSX file
    
    Returns:
        Dict with:
        - feed_type: 'CDWRT' | 'CHWST' | 'CHWRT' | 'POWER' | 'FLOW' | None
        - ashrae_standard: Standard ASHRAE name (e.g., 'Chilled Water Supply Temperature')
        - confidence: float [0, 1]
            1.0 = Exact ASHRAE abbreviation match
            0.8 = Strong pattern match (e.g., CHW_SUPPLY)
            0.6 = Generic pattern match (e.g., SUPPLY_TEMP)
            0.0 = No match (unknown)
        - parsing_method: 'priority_regex' | 'unknown'
        - matched_pattern: The regex pattern that matched (for debugging)
        - building: Building identifier (heuristic, may be None)
        - location: Location/floor identifier (heuristic, may be None)
        - equipment: Equipment identifier (heuristic, may be None)
        - segments: List of filename segments (split by underscore)
        - raw_filename: Original filename
    
    Priority Order (critical for disambiguation):
    1. CDWRT: COND|CDW (checked first - highly specific)
    2. CHWST: CHW.*SUPPLY|CHWST|LEAVING.*TEMP
    3. CHWRT: CHW.*RETURN|CHWRT|ENTERING.*TEMP
    4. POWER: POWER|KW|ENERGY|DEMAND|LOAD (note: LOAD→POWER)
    5. FLOW: FLOW|GPM|LPS|RATE
    
    Examples:
        >>> parse_filename_metadata("Chiller_1_CHW_Supply_Temp.csv")
        {'feed_type': 'CHWST', 'confidence': 1.0, ...}
        
        >>> parse_filename_metadata("Condenser_Water_Return.csv")
        {'feed_type': 'CDWRT', 'confidence': 0.8, ...}
        
        >>> parse_filename_metadata("Water_Flow.csv")
        {'feed_type': 'FLOW', 'confidence': 0.6, ...}
        
        >>> parse_filename_metadata("Chiller_Status.csv")
        {'feed_type': None, 'confidence': 0.0, ...}
    """
    # Step 1: Extract filename without path
    filename = filepath.split('/')[-1]
    
    # Step 2: Strip file extension
    filename_no_ext = re.sub(r'\.(csv|xlsx|txt)$', '', filename, flags=re.IGNORECASE)
    
    # Step 3: Normalize to UPPERCASE for case-insensitive matching
    filename_upper = filename_no_ext.upper()
    
    # Step 4: Split into segments for metadata extraction
    segments = filename_no_ext.split('_')
    
    # Step 5: Priority-based pattern matching (first match wins)
    detected_feed_type = None
    matched_pattern = None
    confidence = 0.0
    
    for feed_type, pattern in PATTERNS:
        if re.search(pattern, filename_upper):
            detected_feed_type = feed_type
            matched_pattern = pattern
            
            # Confidence scoring based on match quality
            if feed_type in filename_upper:  # Exact abbreviation present
                confidence = 1.0
            elif pattern in ['COND|CDW', r'CHW.*SUPPLY', r'CHW.*RETURN']:  # Strong indicators
                confidence = 0.8
            else:  # Generic patterns (FLOW, RATE, POWER)
                confidence = 0.6
            
            break  # First match wins - stop searching
    
    # Step 6: Extract building/location/equipment metadata (heuristic)
    building, location, equipment = _extract_metadata_heuristic(segments)
    
    # Step 7: Build result
    result = {
        'feed_type': detected_feed_type,
        'ashrae_standard': FEED_TYPES.get(detected_feed_type) if detected_feed_type else None,
        'confidence': confidence,
        'parsing_method': 'priority_regex' if detected_feed_type else 'unknown',
        'matched_pattern': matched_pattern,
        'building': building,
        'location': location,
        'equipment': equipment,
        'segments': segments,
        'raw_filename': filename
    }
    
    return result


def _extract_metadata_heuristic(
    segments: List[str]
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Pure function: Extract building, location, equipment from filename segments.
    
    ZERO SIDE EFFECTS - heuristic parsing only.
    
    Args:
        segments: List of filename segments (split by underscore)
    
    Returns:
        Tuple of (building, location, equipment)
        Each may be None if not detected
    
    Heuristics:
    - Building: First segment(s) before location/equipment keywords
    - Location: Segments with "Level", "Floor", "Zone" keywords + following number
    - Equipment: Segments with "Chiller", "Pump", "Tower" keywords + following ID
    
    Examples:
        >>> _extract_metadata_heuristic(['BarTech', '160', 'Ann', 'St', 'Level', '22', 'Chiller', '2'])
        ('BarTech', 'Level_22', 'Chiller_2')
        
        >>> _extract_metadata_heuristic(['Site_A', 'Pump', '1', 'Flow'])
        ('Site_A', None, 'Pump_1')
    """
    building = None
    location = None
    equipment = None
    
    # Location keywords
    location_keywords = ['level', 'floor', 'zone', 'room', 'area']
    location_idx = None
    
    for i, seg in enumerate(segments):
        if any(kw in seg.lower() for kw in location_keywords):
            # Found location - grab this segment + next if it's a number
            location_parts = [seg]
            if i + 1 < len(segments) and segments[i + 1].isdigit():
                location_parts.append(segments[i + 1])
            location = '_'.join(location_parts)
            location_idx = i
            break
    
    # Equipment keywords
    equipment_keywords = ['chiller', 'pump', 'tower', 'fan', 'boiler', 'ahu', 'cooler']
    equipment_idx = None
    
    for i, seg in enumerate(segments):
        if any(kw in seg.lower() for kw in equipment_keywords):
            # Found equipment - grab this segment + next if it looks like an ID
            equipment_parts = [seg]
            if i + 1 < len(segments):
                next_seg = segments[i + 1]
                # Include next segment if it's a number or short identifier
                if next_seg.isdigit() or len(next_seg) <= 3:
                    equipment_parts.append(next_seg)
            equipment = '_'.join(equipment_parts)
            equipment_idx = i
            break
    
    # Building is first segment(s) before location/equipment
    first_keyword_idx = None
    if location_idx is not None:
        first_keyword_idx = location_idx
    if equipment_idx is not None and (first_keyword_idx is None or equipment_idx < first_keyword_idx):
        first_keyword_idx = equipment_idx
    
    if first_keyword_idx is not None and first_keyword_idx > 0:
        building = segments[0]  # Just use first segment for building
    elif len(segments) > 0:
        building = segments[0]  # Default to first segment
    
    return building, location, equipment


def detect_feed_type(filename: str) -> Optional[str]:
    """
    Simplified interface: Just return feed type string.
    
    This matches the reference implementation in TELEMETRY_PARSING_SPEC.md
    
    Args:
        filename: Filename to classify
    
    Returns:
        'CDWRT' | 'CHWST' | 'CHWRT' | 'POWER' | 'FLOW' | None
    
    Examples:
        >>> detect_feed_type('Chiller_1_CHW_Supply_Temp.csv')
        'CHWST'
        >>> detect_feed_type('Condenser_Water_Return.csv')
        'CDWRT'
        >>> detect_feed_type('Chiller_Status.csv')
        None
    """
    result = parse_filename_metadata(filename)
    return result['feed_type']
