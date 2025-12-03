#!/usr/bin/env python3
"""
CLI Orchestrator: Universal BMS Percent Decoder

Entry point for command-line usage.
Orchestrates hooks and pure functions.
"""

import sys
import argparse
import logging

# Import hooks
from ..hooks.useBmsPercentDecoder import (
    use_bms_percent_decoder,
    save_decoded_file,
    decode_and_report
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """
    CLI entry point for BMS percent decoder.
    
    Examples:
        python -m src.orchestration.DecoderCLI pump_vsd.csv
        python -m src.orchestration.DecoderCLI pump_vsd.csv --signal-name "Pump_1_VSD"
        python -m src.orchestration.DecoderCLI pump_vsd.csv --output decoded_output.csv
    """
    parser = argparse.ArgumentParser(
        description="Universal BMS Percent Decoder - Automatically detect and normalize BMS percentage signals",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s pump_vsd.csv
  %(prog)s pump_vsd.csv --signal-name "Pump_1_VSD"
  %(prog)s data.csv --timestamp-col time --value-col signal
  %(prog)s input.csv --output custom_output.csv
  %(prog)s input.csv --no-save  # Print report only, don't save file
        """
    )
    
    parser.add_argument(
        "filepath",
        help="Path to BMS CSV file"
    )
    
    parser.add_argument(
        "--signal-name",
        help="Signal name for logging (auto-detected from filename if not provided)"
    )
    
    parser.add_argument(
        "--timestamp-col",
        default="save_time",
        help="Name of timestamp column (default: save_time)"
    )
    
    parser.add_argument(
        "--value-col",
        default="value",
        help="Name of value column (default: value)"
    )
    
    parser.add_argument(
        "--output",
        help="Output file path (default: input_decoded.csv)"
    )
    
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save decoded file, only print report"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all logging except errors"
    )
    
    args = parser.parse_args()
    
    # Adjust logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    
    try:
        logger.info("=" * 80)
        logger.info("Universal BMS Percent Decoder")
        logger.info("=" * 80)
        
        # Hook: Decode file
        df, metadata = use_bms_percent_decoder(
            args.filepath,
            signal_name=args.signal_name,
            timestamp_col=args.timestamp_col,
            value_col=args.value_col
        )
        
        # Import pure function for report formatting
        from ..domain.decoder.formatDecoderReport import format_decoder_report
        
        # Pure function: Generate report
        report = format_decoder_report(df, metadata)
        print("\n" + report)
        
        # Hook: Save decoded file (unless --no-save)
        if not args.no_save:
            output_path = args.output or args.filepath.replace(".csv", "_decoded.csv")
            save_decoded_file(df, output_path)
        else:
            logger.info("Skipping file save (--no-save flag)")
        
        logger.info("=" * 80)
        logger.info("Decoding complete")
        logger.info("=" * 80)
        
        return 0
        
    except FileNotFoundError:
        logger.error(f"File not found: {args.filepath}")
        return 1
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return 1
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
