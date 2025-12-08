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
        Stage 1: Unit verification and physics validation.
        
        Returns:
            True if Stage 1 passes, False if HALT
        """
        logger.info("")
        logger.info("="*80)
        logger.info("STAGE 1: UNIT VERIFICATION & PHYSICS VALIDATION")
        logger.info("="*80)
        
        if not self.results['stage0']:
            logger.error("❌ Stage 0 must complete before Stage 1")
            return False
        
        feed_map = self.results['stage0']['feed_map']
        
        # Load CSV files into single DataFrame
        logger.info("Loading data files...")
        dfs = {}
        for feed_type, filepath in feed_map.items():
            logger.info(f"  Loading {feed_type}: {Path(filepath).name}")
            df = pd.read_csv(filepath)
            # Assume timestamp column is first, data column is second
            # TODO: Make this configurable
            if len(df.columns) >= 2:
                timestamp_col = df.columns[0]
                value_col = df.columns[1]
                dfs[feed_type] = df[[timestamp_col, value_col]].rename(
                    columns={timestamp_col: 'timestamp', value_col: feed_type}
                )
        
        # Merge on timestamp (naive merge - Stage 3 will handle synchronization)
        logger.info("Merging time-series data...")
        df_merged = dfs['CHWST'][['timestamp']].copy()
        for feed_type, df in dfs.items():
            df_merged = df_merged.merge(
                df[['timestamp', feed_type]],
                on='timestamp',
                how='outer'
            )
        
        logger.info(f"  Merged shape: {df_merged.shape}")
        logger.info(f"  Date range: {df_merged['timestamp'].min()} to {df_merged['timestamp'].max()}")
        
        # Create signal mappings (map BMD channels to DataFrame columns)
        signal_mappings = {
            'CHWST': 'CHWST',
            'CHWRT': 'CHWRT',
            'CDWRT': 'CDWRT',
            'FLOW': 'FLOW',
            'POWER': 'POWER'
        }
        
        # Run Stage 1 verification
        logger.info("Running Stage 1 verification...")
        try:
            df_verified, metrics = use_stage1_verifier(
                df_merged,
                signal_mappings
            )
        except Exception as e:
            logger.error(f"❌ Stage 1 failed: {e}")
            self.results['stage1'] = {
                'status': 'ERROR',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self._save_stage1_report()
            return False
        
        # Check HALT conditions
        stage1_confidence = metrics['confidence']['stage1_confidence']
        halt_reason = metrics.get('halt_reason')
        
        if halt_reason:
            logger.error(f"❌ HALT: {halt_reason}")
            self.results['stage1'] = {
                'status': 'HALT',
                'halt_reason': halt_reason,
                'confidence': stage1_confidence,
                'metrics': metrics,
                'timestamp': datetime.now().isoformat()
            }
            self._save_stage1_report()
            return False
        
        # Save Stage 1 results
        self.results['stage1'] = {
            'status': 'SUCCESS',
            'confidence': stage1_confidence,
            'metrics': metrics,
            'verified_data_shape': df_verified.shape,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save verified DataFrame
        output_csv = self.output_dir / 'stage1_verified.csv'
        df_verified.to_csv(output_csv, index=False)
        logger.info(f"   Saved verified data: {output_csv}")
        
        self._save_stage1_report()
        
        logger.info(f"✅ Stage 1 complete - confidence: {stage1_confidence:.2f}")
        
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
            
            # Stage 1: Unit verification
            if not self.run_stage1():
                status = self.results['stage1']['status']
                return 1 if status == 'HALT' else 2
            
            # TODO: Stage 2 (load normalization + COP calculation)
            # TODO: Stage 3 (timestamp synchronization)
            
            logger.info("")
            logger.info("="*80)
            logger.info("✅ PIPELINE COMPLETE")
            logger.info("="*80)
            logger.info(f"Stage 0: {self.results['stage0']['status']}")
            logger.info(f"Stage 1: {self.results['stage1']['status']} "
                       f"(confidence: {self.results['stage1']['confidence']:.2f})")
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
