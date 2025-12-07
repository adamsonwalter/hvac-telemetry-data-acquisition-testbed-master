#!/usr/bin/env python3
"""
Hook: Orchestrate filename parsing with ALL side effects.

This module contains ALL side effects:
- Logging
- File I/O
- Progress tracking
- Error handling

Calls pure functions from domain layer for business logic.

Core Principle: "State lives in hooks; App orchestrates."
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

# Import pure function from domain layer
from domain.htdam.stage0.parseFilenameMetadata import (
    parse_filename_metadata,
    detect_feed_type,
    FEED_TYPES
)

# Setup logger (side effect!)
logger = logging.getLogger(__name__)


def use_filename_parser(
    filepaths: List[str],
    verbose: bool = False
) -> Tuple[Dict[str, Dict], Dict[str, List[str]]]:
    """
    Hook: Parse multiple filenames and classify by feed type.
    
    ALL SIDE EFFECTS HERE:
    - Logging
    - File validation (checks if files exist)
    - Progress tracking
    
    Args:
        filepaths: List of file paths to parse
        verbose: Enable verbose logging
    
    Returns:
        Tuple of:
        - results: Dict mapping filepath → parse result metadata
        - classification: Dict mapping feed_type → list of filepaths
    
    Example:
        >>> results, classification = use_filename_parser([
        ...     'data/CHWST.csv',
        ...     'data/CHWRT.csv',
        ...     'data/Power.csv'
        ... ])
        >>> classification['CHWST']
        ['data/CHWST.csv']
        >>> classification['POWER']
        ['data/Power.csv']
    """
    logger.info(f"Starting filename parsing for {len(filepaths)} files")
    
    results = {}
    classification = {
        'CHWST': [],
        'CHWRT': [],
        'CDWRT': [],
        'POWER': [],
        'FLOW': [],
        'UNKNOWN': []
    }
    
    # Validate files exist (side effect: file I/O)
    valid_files = []
    for filepath in filepaths:
        if not Path(filepath).exists():
            logger.warning(f"File not found: {filepath}")
            continue
        valid_files.append(filepath)
    
    logger.info(f"Found {len(valid_files)}/{len(filepaths)} valid files")
    
    # Parse each file (calls pure function)
    for i, filepath in enumerate(valid_files, 1):
        if verbose:
            logger.info(f"[{i}/{len(valid_files)}] Parsing: {Path(filepath).name}")
        
        # Call pure function (NO side effects)
        result = parse_filename_metadata(filepath)
        
        # Store result
        results[filepath] = result
        
        # Classify by feed type
        feed_type = result['feed_type'] if result['feed_type'] else 'UNKNOWN'
        classification[feed_type].append(filepath)
        
        # Log result (side effect)
        if verbose or result['confidence'] < 0.8:
            logger.info(
                f"  → {feed_type} (confidence: {result['confidence']:.2f})"
            )
        
        if result['confidence'] < 0.6:
            logger.warning(
                f"  ⚠️  Low confidence - manual review recommended: {filepath}"
            )
    
    # Summary logging (side effect)
    logger.info("Classification summary:")
    for feed_type, files in classification.items():
        if files:
            logger.info(f"  {feed_type}: {len(files)} file(s)")
    
    return results, classification


def use_filename_parser_single(
    filepath: str,
    verbose: bool = False
) -> Dict:
    """
    Hook: Parse a single filename with logging.
    
    ALL SIDE EFFECTS HERE:
    - Logging
    - File validation
    
    Args:
        filepath: Path to file
        verbose: Enable verbose logging
    
    Returns:
        Parse result metadata dict
    
    Example:
        >>> result = use_filename_parser_single('data/CHWST.csv')
        >>> result['feed_type']
        'CHWST'
    """
    logger.info(f"Parsing filename: {Path(filepath).name}")
    
    # Validate file exists (side effect: file I/O)
    if not Path(filepath).exists():
        logger.error(f"File not found: {filepath}")
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # Call pure function (NO side effects)
    result = parse_filename_metadata(filepath)
    
    # Log result (side effect)
    feed_type = result['feed_type'] if result['feed_type'] else 'UNKNOWN'
    logger.info(
        f"Detected: {feed_type} "
        f"(confidence: {result['confidence']:.2f}, "
        f"method: {result['parsing_method']})"
    )
    
    if verbose:
        logger.info(f"ASHRAE standard: {result['ashrae_standard']}")
        logger.info(f"Building: {result['building']}")
        logger.info(f"Location: {result['location']}")
        logger.info(f"Equipment: {result['equipment']}")
    
    if result['confidence'] < 0.6:
        logger.warning("⚠️  Low confidence - manual review recommended")
    
    return result


def use_dataset_loader(
    directory: str,
    required_feeds: Optional[List[str]] = None,
    verbose: bool = False
) -> Tuple[Dict[str, str], List[str]]:
    """
    Hook: Load dataset from directory and classify files by feed type.
    
    ALL SIDE EFFECTS HERE:
    - Logging
    - File I/O (scanning directory)
    - Validation against required feeds
    
    Args:
        directory: Path to directory containing data files
        required_feeds: Optional list of required feed types (e.g., ['CHWST', 'CHWRT', 'POWER'])
        verbose: Enable verbose logging
    
    Returns:
        Tuple of:
        - feed_map: Dict mapping feed_type → filepath (one file per feed type)
        - warnings: List of warning messages
    
    Raises:
        ValueError: If required feeds are missing
    
    Example:
        >>> feed_map, warnings = use_dataset_loader(
        ...     'test-data/bartech/',
        ...     required_feeds=['CHWST', 'CHWRT', 'CDWRT', 'POWER', 'FLOW']
        ... )
        >>> feed_map['CHWST']
        'test-data/bartech/...CHWST...csv'
    """
    logger.info(f"Loading dataset from: {directory}")
    
    # Scan directory for CSV/XLSX files (side effect: file I/O)
    data_dir = Path(directory)
    if not data_dir.exists():
        logger.error(f"Directory not found: {directory}")
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    csv_files = list(data_dir.glob("*.csv"))
    xlsx_files = list(data_dir.glob("*.xlsx"))
    all_files = csv_files + xlsx_files
    
    logger.info(f"Found {len(csv_files)} CSV and {len(xlsx_files)} XLSX files")
    
    if not all_files:
        logger.warning(f"No data files found in: {directory}")
        return {}, ["No data files found"]
    
    # Parse filenames
    results, classification = use_filename_parser(
        [str(f) for f in all_files],
        verbose=verbose
    )
    
    # Build feed map (one file per feed type)
    feed_map = {}
    warnings = []
    
    for feed_type in ['CHWST', 'CHWRT', 'CDWRT', 'POWER', 'FLOW']:
        files = classification.get(feed_type, [])
        
        if not files:
            warnings.append(f"No {feed_type} file found")
            logger.warning(f"Missing feed type: {feed_type}")
        elif len(files) > 1:
            # Multiple files for same feed type - pick highest confidence
            best_file = max(files, key=lambda f: results[f]['confidence'])
            feed_map[feed_type] = best_file
            warnings.append(
                f"Multiple {feed_type} files found - using highest confidence: "
                f"{Path(best_file).name}"
            )
            logger.warning(warnings[-1])
        else:
            feed_map[feed_type] = files[0]
            logger.info(f"✓ {feed_type}: {Path(files[0]).name}")
    
    # Validate required feeds
    if required_feeds:
        missing = [ft for ft in required_feeds if ft not in feed_map]
        if missing:
            error_msg = f"Missing required feed types: {', '.join(missing)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    logger.info(f"Dataset loading complete: {len(feed_map)} feed types mapped")
    
    return feed_map, warnings


def use_filename_parser_report(
    filepaths: List[str],
    output_path: Optional[str] = None
) -> str:
    """
    Hook: Generate classification report for multiple files.
    
    ALL SIDE EFFECTS HERE:
    - Logging
    - File I/O (writing report)
    
    Args:
        filepaths: List of file paths to parse
        output_path: Optional path to save report (CSV format)
    
    Returns:
        Report as formatted string
    
    Example:
        >>> report = use_filename_parser_report(['data/CHWST.csv', 'data/CHWRT.csv'])
        >>> print(report)
    """
    logger.info(f"Generating classification report for {len(filepaths)} files")
    
    # Parse filenames
    results, classification = use_filename_parser(filepaths, verbose=False)
    
    # Build report
    lines = []
    lines.append("=" * 80)
    lines.append("Filename Classification Report")
    lines.append("=" * 80)
    lines.append(f"Total files: {len(filepaths)}")
    lines.append("")
    
    lines.append("Classification Summary:")
    for feed_type, files in sorted(classification.items()):
        lines.append(f"  {feed_type}: {len(files)} file(s)")
    lines.append("")
    
    lines.append("Detailed Results:")
    lines.append("-" * 80)
    lines.append(f"{'Filename':<40} {'Feed Type':<10} {'Confidence':<12} {'Building':<20}")
    lines.append("-" * 80)
    
    for filepath, result in sorted(results.items()):
        filename = Path(filepath).name
        feed_type = result['feed_type'] if result['feed_type'] else 'UNKNOWN'
        confidence = f"{result['confidence']:.2f}"
        building = result['building'] if result['building'] else 'N/A'
        
        lines.append(f"{filename:<40} {feed_type:<10} {confidence:<12} {building:<20}")
    
    lines.append("=" * 80)
    
    report = "\n".join(lines)
    
    # Save to file if requested (side effect: file I/O)
    if output_path:
        logger.info(f"Saving report to: {output_path}")
        with open(output_path, 'w') as f:
            f.write(report)
        logger.info("✓ Report saved")
    
    return report
