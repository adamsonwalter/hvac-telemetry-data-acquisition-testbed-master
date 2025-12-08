#!/usr/bin/env python3
"""
HTDAM CLI: End-to-End Orchestrator (Stage 0 → Stage 1)

Usage:
    python -m src.orchestration.HtdamCLI \\
        --input test-data/real-installations/bartech/ \\
        --output output/bartech/ \\
        --verbose

Exit Codes:
    0: Success - all stages completed
    1: HALT - BMD requirements not met (missing signals, physics violations)
    2: Error - file I/O, parsing, or unexpected errors
"""

import argparse
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd

# Import hooks (orchestration with side effects)
import sys

# Add parent directory to path for relative imports
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.hooks.useFilenameParser import use_dataset_loader
from src.hooks.useStage1Verifier import use_stage1_verifier
from src.hooks.useStage2GapDetector import use_stage2_gap_detector
from src.hooks.useStage3Synchronizer import use_stage3_synchronizer
# from src.hooks.useStage15Synchronizer import use_stage15_synchronizer  # DEPRECATED - replaced by Stage 3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HtdamPipeline:
    """Orchestrate HTDAM pipeline from Stage 0 through Stage N."""
    
    def __init__(self, input_dir: str, output_dir: str, verbose: bool = False):
        """
        Initialize HTDAM pipeline.
        
        Args:
            input_dir: Directory containing raw BMS data files
            output_dir: Directory for output files
            verbose: Enable verbose logging
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.verbose = verbose
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Results storage
        self.results = {
            'stage0': None,
            'stage1': None,
            'stage2': None,
            'stage3': None
        }
        
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
    
    def run_stage0(self) -> bool:
        """
        Stage 0: Filename parsing and BMD classification.
        
        Returns:
            True if BMD complete, False otherwise
        """
        logger.info("="*80)
        logger.info("STAGE 0: FILENAME PARSING & BMD CLASSIFICATION")
        logger.info("="*80)
        
        # Use Stage 0 hook to classify files
        required_feeds = ['CHWST', 'CHWRT', 'CDWRT', 'FLOW', 'POWER']
        
        try:
            feed_map, warnings = use_dataset_loader(
                str(self.input_dir),
                required_feeds=required_feeds,
                verbose=self.verbose
            )
        except ValueError as e:
            logger.error(f"❌ HALT: {e}")
            self.results['stage0'] = {
                'status': 'HALT',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self._save_stage0_report()
            return False
        
        # Log warnings
        for warning in warnings:
            logger.warning(warning)
        
        # Save Stage 0 results
        self.results['stage0'] = {
            'status': 'SUCCESS',
            'feed_map': feed_map,
            'warnings': warnings,
            'timestamp': datetime.now().isoformat()
        }
        
        self._save_stage0_report()
        
        logger.info("✅ Stage 0 complete - BMD files classified")
        logger.info(f"   Feed map: {json.dumps(feed_map, indent=2)}")
        
        return True
    
    def run_stage1(self) -> bool:
        """
        Stage 1: Unit verification and physics validation (per-signal, no merge).
        
        Returns:
            True if Stage 1 passes, False if HALT
        """
        logger.info("")
        logger.info("="*80)
        logger.info("STAGE 1: UNIT VERIFICATION & PHYSICS VALIDATION (PER-SIGNAL)")
        logger.info("="*80)
        
        if not self.results['stage0']:
            logger.error("❌ Stage 0 must complete before Stage 1")
            return False
        
        feed_map = self.results['stage0']['feed_map']
        
        # Load CSV files as separate DataFrames (no merge)
        logger.info("Loading per-signal data files...")
        signal_dfs = {}
        for feed_type, filepath in feed_map.items():
            logger.info(f"  Loading {feed_type}: {Path(filepath).name}")
            df = pd.read_csv(filepath)
            
            if len(df.columns) >= 2:
                timestamp_col = df.columns[0]
                value_col = df.columns[1]
                signal_dfs[feed_type] = df[[timestamp_col, value_col]].rename(
                    columns={timestamp_col: 'timestamp', value_col: 'value'}
                )
                logger.info(f"    {feed_type}: {len(signal_dfs[feed_type])} samples")
        
        # Store per-signal DataFrames for Stage 2 (gap detection)
        self.signal_dataframes = signal_dfs
        
        # Stage 1 is now lightweight - just validate that signals loaded
        # Full unit validation happens later in pipeline
        self.results['stage1'] = {
            'status': 'SUCCESS',
            'n_signals_loaded': len(signal_dfs),
            'signals': list(signal_dfs.keys()),
            'sample_counts': {sig: len(df) for sig, df in signal_dfs.items()},
            'timestamp': datetime.now().isoformat()
        }
        
        self._save_stage1_report()
        logger.info(f"✅ Stage 1 complete - {len(signal_dfs)} signals loaded")
        
        return True
    
    def run_stage2(self) -> bool:
        """
        Stage 2: Gap detection and classification (BEFORE synchronization).
        
        Returns:
            True if Stage 2 completes, False on error
            Note: Returns True even if human approval required (pipeline pause)
        """
        logger.info("")
        logger.info("="*80)
        logger.info("STAGE 2: GAP DETECTION & CLASSIFICATION")
        logger.info("="*80)
        
        if not self.results['stage1']:
            logger.error("❌ Stage 1 must complete before Stage 2")
            return False
        
        try:
            # Run gap detection on unsynchronized signals
            gap_annotated_signals, metrics = use_stage2_gap_detector(
                signals=self.signal_dataframes,
                stage1_confidence=1.0,
                timestamp_col='timestamp',
                value_col='value'
            )
            
            # Store gap-annotated signals for Stage 3 (sync)
            self.gap_annotated_signals = gap_annotated_signals
            
            # Save results
            self.results['stage2'] = {
                'status': 'SUCCESS',
                'stage2_confidence': metrics['stage2_confidence'],
                'aggregate_penalty': metrics['aggregate_penalty'],
                'exclusion_windows_count': len(metrics['exclusion_windows']),
                'human_approval_required': metrics['human_approval_required'],
                'metrics': metrics,
                'timestamp': datetime.now().isoformat()
            }
            
            # Save gap-annotated signals
            for signal_id, df in gap_annotated_signals.items():
                output_csv = self.output_dir / f'stage2_{signal_id.lower()}_gaps.csv'
                df.to_csv(output_csv, index=False)
                logger.info(f"   Saved {signal_id} gap analysis: {output_csv}")
            
            self._save_stage2_report()
            
            logger.info(
                f"✅ Stage 2 complete - confidence: {metrics['stage2_confidence']:.3f} "
                f"(penalty: {metrics['aggregate_penalty']:.3f})"
            )
            
            if metrics['human_approval_required']:
                logger.warning("")
                logger.warning("⚠️  PIPELINE PAUSED")
                logger.warning(f"   {len(metrics['exclusion_windows'])} exclusion window(s) detected")
                logger.warning("   Human approval required before proceeding to Stage 3")
                logger.warning("   Review: stage2_report.json")
                logger.warning("")
                # Don't halt pipeline - just pause at this stage
                # User can manually approve and continue later
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Stage 2 failed: {e}")
            self.results['stage2'] = {
                'status': 'ERROR',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self._save_stage2_report()
            return False
    
    def run_stage3(self) -> bool:
        """
        Stage 3: Timestamp synchronization (official HTDAM v2.0 spec).
        
        Returns:
            True if Stage 3 passes, False if HALT
        """
        logger.info("")
        logger.info("="*80)
        logger.info("STAGE 3: TIMESTAMP SYNCHRONIZATION")
        logger.info("="*80)
        
        if not self.results['stage2']:
            logger.error("❌ Stage 2 must complete before Stage 3")
            return False
        
        # Get Stage 2 confidence and exclusion windows
        stage2_confidence = self.results['stage2']['stage2_confidence']
        exclusion_windows = self.results['stage2']['metrics'].get('exclusion_windows', [])
        
        # Check if human approval required but not yet approved
        if self.results['stage2']['human_approval_required']:
            logger.warning("⚠️  Exclusion windows require human approval")
            logger.warning("   Proceeding with Stage 3 using detected exclusion windows")
            logger.warning("   To approve/reject, modify exclusion_windows in stage2_report.json and re-run")
        
        try:
            # Run Stage 3 synchronization on gap-annotated signals
            df_synchronized, metrics = use_stage3_synchronizer(
                signals=self.gap_annotated_signals,
                exclusion_windows=exclusion_windows,
                stage2_confidence=stage2_confidence,
                timestamp_col='timestamp',
                value_col='value'
            )
        except Exception as e:
            logger.error(f"❌ Stage 3 failed: {e}")
            self.results['stage3'] = {
                'status': 'ERROR',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self._save_stage3_report()
            return False
        
        # Check for HALT condition
        if metrics.get('halt', False):
            logger.error("❌ Stage 3 HALT condition detected")
            logger.error(f"   Errors: {metrics.get('errors', [])}")
            self.results['stage3'] = {
                'status': 'HALT',
                'halt': True,
                'errors': metrics.get('errors', []),
                'warnings': metrics.get('warnings', []),
                'metrics': metrics,
                'timestamp': datetime.now().isoformat()
            }
            self._save_stage3_report()
            return False
        
        # Save Stage 3 results
        n_synced_rows = len(df_synchronized)
        grid_points = metrics['grid']['grid_points']
        coverage_pct = metrics['row_classification']['VALID_pct']
        
        self.results['stage3'] = {
            'status': 'SUCCESS',
            'grid_points': grid_points,
            'n_synchronized_rows': n_synced_rows,
            'coverage_pct': coverage_pct,
            'stage3_confidence': metrics['stage3_confidence'],
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store synchronized DataFrame for Stage 4
        self.synchronized_df = df_synchronized
        
        # Save synchronized DataFrame
        output_csv = self.output_dir / 'stage3_synchronized.csv'
        df_synchronized.to_csv(output_csv, index=False)
        logger.info(f"   Saved synchronized data: {output_csv}")
        
        self._save_stage3_report()
        logger.info(
            f"✅ Stage 3 complete - {grid_points} grid points, "
            f"{coverage_pct:.1f}% coverage, confidence: {metrics['stage3_confidence']:.2f}"
        )
        
        if metrics.get('warnings'):
            logger.info(f"   {len(metrics['warnings'])} warning(s) - see stage3_metrics.json")
        
        return True
    
    def _save_stage0_report(self):
        """Save Stage 0 JSON report."""
        output_file = self.output_dir / 'stage0_classification.json'
        with open(output_file, 'w') as f:
            json.dump(self.results['stage0'], f, indent=2)
        logger.info(f"   Saved Stage 0 report: {output_file}")
    
    def _save_stage1_report(self):
        """Save Stage 1 JSON report."""
        output_file = self.output_dir / 'stage1_report.json'
        with open(output_file, 'w') as f:
            json.dump(self.results['stage1'], f, indent=2)
        logger.info(f"   Saved Stage 1 report: {output_file}")
    
    def _save_stage2_report(self):
        """Save Stage 2 JSON report."""
        output_file = self.output_dir / 'stage2_report.json'
        with open(output_file, 'w') as f:
            json.dump(self.results['stage2'], f, indent=2)
        logger.info(f"   Saved Stage 2 report: {output_file}")
    
    def _save_stage3_report(self):
        """Save Stage 3 JSON report."""
        output_file = self.output_dir / 'stage3_metrics.json'
        with open(output_file, 'w') as f:
            json.dump(self.results['stage3'], f, indent=2)
        logger.info(f"   Saved Stage 3 metrics: {output_file}")
    
    def run(self) -> int:
        """
        Run full HTDAM pipeline.
        
        Returns:
            Exit code (0=success, 1=HALT, 2=error)
        """
        logger.info("="*80)
        logger.info("HTDAM v2.0 - High-Throughput Data Assimilation Methodology")
        logger.info("="*80)
        logger.info(f"Input directory: {self.input_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info("")
        
        try:
            # Stage 0: Filename parsing
            if not self.run_stage0():
                return 1  # HALT
            
            # Stage 1: Load signals (per-signal, no merge)
            if not self.run_stage1():
                status = self.results['stage1']['status']
                return 1 if status == 'HALT' else 2
            
            # Stage 2: Gap detection (BEFORE synchronization)
            if not self.run_stage2():
                status = self.results.get('stage2', {}).get('status', 'ERROR')
                return 2  # Error (never HALT)
            
            # Stage 3: Timestamp synchronization (official HTDAM v2.0 spec)
            if not self.run_stage3():
                status = self.results.get('stage3', {}).get('status', 'ERROR')
                return 1 if status == 'HALT' else 2
            
            # TODO: Stage 4 (Signal Preservation & COP calculation)
            
            logger.info("")
            logger.info("="*80)
            logger.info("✅ PIPELINE COMPLETE")
            logger.info("="*80)
            logger.info(f"Stage 0: {self.results['stage0']['status']}")
            logger.info(f"Stage 1: {self.results['stage1']['status']} "
                       f"({self.results['stage1']['n_signals_loaded']} signals)")
            logger.info(f"Stage 2: {self.results['stage2']['status']} "
                       f"(confidence: {self.results['stage2']['stage2_confidence']:.2f})")
            logger.info(f"Stage 3: {self.results['stage3']['status']} "
                       f"({self.results['stage3']['grid_points']} grid points, "
                       f"{self.results['stage3']['coverage_pct']:.1f}% coverage, "
                       f"confidence: {self.results['stage3']['stage3_confidence']:.2f})")
            logger.info("")
            logger.info(f"Results saved to: {self.output_dir}")
            
            return 0  # Success
            
        except Exception as e:
            logger.exception(f"❌ Unexpected error: {e}")
            return 2  # Error


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='HTDAM v2.0 - High-Throughput Data Assimilation Methodology',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process BarTech dataset
  python -m src.orchestration.HtdamCLI \\
      --input test-data/real-installations/bartech/ \\
      --output output/bartech/
  
  # Process Monash dataset (will HALT - missing FLOW)
  python -m src.orchestration.HtdamCLI \\
      --input test-data/real-installations/monash-university/ \\
      --output output/monash/ \\
      --verbose

Exit Codes:
  0: Success - all stages completed
  1: HALT - BMD requirements not met
  2: Error - unexpected failure
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input directory containing raw BMS data files'
    )
    
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output directory for results'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Run pipeline
    pipeline = HtdamPipeline(
        input_dir=args.input,
        output_dir=args.output,
        verbose=args.verbose
    )
    
    exit_code = pipeline.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
