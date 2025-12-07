#!/usr/bin/env python3
"""
Test new hooks vs functions architecture against synthetic test data.

This demonstrates the power of the new architecture:
- Uses hooks for orchestration (file I/O, logging)
- Uses pure functions for logic (detection, normalization)
- Easy to test and validate
"""

import sys
import glob
import pandas as pd
from pathlib import Path

# Import our new architecture
from src.hooks.useBmsPercentDecoder import use_bms_percent_decoder
from src.domain.decoder.formatDecoderReport import format_decoder_report
from src.domain.validator.calculateValidationScore import (
    calculate_validation_score,
    format_score_report,
    ValidationScore
)

def test_all_synthetic_files():
    """Test decoder against all synthetic CSV files."""
    
    # Find all test CSV files (exclude _decoded.csv files)
    csv_files = [f for f in glob.glob("Test_*.csv") 
                 if not f.endswith("_decoded.csv")]
    
    if not csv_files:
        print("❌ No test CSV files found")
        return False
    
    print("=" * 80)
    print(f"Testing New Architecture Against {len(csv_files)} Synthetic Files")
    print("=" * 80)
    print()
    
    results = []
    
    for filepath in sorted(csv_files):
        print(f"\n{'='*80}")
        print(f"Testing: {filepath}")
        print('='*80)
        
        try:
            # Hook: orchestrate decoding (handles file I/O, logging)
            df, metadata = use_bms_percent_decoder(
                filepath,
                signal_name=Path(filepath).stem
            )
            
            # Validate results
            normalized = df['normalized'].dropna()
            
            # Calculate validation score
            score, level, issues, recommendations = calculate_validation_score(metadata)
            
            result = {
                'file': filepath,
                'status': 'PASS',
                'detected_type': metadata['detected_type'],
                'confidence': metadata['confidence'],
                'scaling_factor': metadata['scaling_factor'],
                'original_min': metadata['original_min'],
                'original_max': metadata['original_max'],
                'normalized_min': float(normalized.min()) if len(normalized) > 0 else None,
                'normalized_max': float(normalized.max()) if len(normalized) > 0 else None,
                'count': len(df),
                'validation_score': score,
                'validation_level': level,
                'issues': issues,
                'recommendations': recommendations
            }
            
            # Display compact summary
            print(f"✅ SUCCESS")
            print(f"   Detected: {result['detected_type']}")
            print(f"   Confidence: {result['confidence']}")
            print(f"   Validation Score: {score}/100 ({level.value})")
            print(f"   Scaling: {result['scaling_factor']:.2f}")
            print(f"   Original range: [{result['original_min']:.2f}, {result['original_max']:.2f}]")
            print(f"   Normalized range: [{result['normalized_min']:.4f}, {result['normalized_max']:.4f}]")
            print(f"   Points: {result['count']}")
            if issues:
                print(f"   ⚠️  Issues: {len(issues)}")
            
        except Exception as e:
            result = {
                'file': filepath,
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"❌ FAILED: {e}")
        
        results.append(result)
    
    # Summary report
    print("\n" + "=" * 80)
    print("SUMMARY REPORT")
    print("=" * 80)
    
    passed = [r for r in results if r['status'] == 'PASS']
    failed = [r for r in results if r['status'] == 'FAIL']
    
    print(f"\nTotal files tested: {len(results)}")
    print(f"✅ Passed: {len(passed)}")
    print(f"❌ Failed: {len(failed)}")
    
    if passed:
        print("\n📊 Detection Statistics:")
        detection_counts = {}
        confidence_counts = {}
        score_levels = {}
        
        for r in passed:
            det_type = r['detected_type']
            confidence = r['confidence']
            detection_counts[det_type] = detection_counts.get(det_type, 0) + 1
            confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1
            
            if 'validation_level' in r:
                level = r['validation_level'].value
                score_levels[level] = score_levels.get(level, 0) + 1
        
        print("\n  Detection Types:")
        for det_type, count in sorted(detection_counts.items()):
            print(f"    {det_type}: {count}")
        
        print("\n  Confidence Levels:")
        for conf, count in sorted(confidence_counts.items()):
            print(f"    {conf}: {count}")
        
        print("\n  Validation Score Levels:")
        for level, count in sorted(score_levels.items()):
            print(f"    {level}: {count}")
        
        if any('validation_score' in r for r in passed):
            scores = [r['validation_score'] for r in passed if 'validation_score' in r]
            avg_score = sum(scores) / len(scores) if scores else 0
            print(f"\n  Average Validation Score: {avg_score:.1f}/100")
    
    if failed:
        print("\n❌ Failed Files:")
        for r in failed:
            print(f"  - {r['file']}: {r['error']}")
    
    print("\n" + "=" * 80)
    
    # Detailed results table
    print("\nDETAILED RESULTS:")
    print("-" * 80)
    print(f"{'File':<40} {'Type':<25} {'Conf':<8} {'Status':<6}")
    print("-" * 80)
    
    for r in results:
        if r['status'] == 'PASS':
            det_type_short = r['detected_type'][:24]
            print(f"{r['file']:<40} {det_type_short:<25} {r['confidence']:<8} ✅")
        else:
            print(f"{r['file']:<40} {'ERROR':<25} {'N/A':<8} ❌")
    
    print("-" * 80)
    
    # Pass/fail determination
    success_rate = len(passed) / len(results) * 100 if results else 0
    print(f"\n🎯 Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("✅ EXCELLENT - Architecture working as expected!")
        return True
    elif success_rate >= 75:
        print("⚠️  GOOD - Some edge cases need attention")
        return True
    else:
        print("❌ NEEDS WORK - Multiple failures detected")
        return False


if __name__ == "__main__":
    success = test_all_synthetic_files()
    sys.exit(0 if success else 1)
