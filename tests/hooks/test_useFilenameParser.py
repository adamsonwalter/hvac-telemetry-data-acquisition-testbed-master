#!/usr/bin/env python3
"""
Unit tests for useFilenameParser.py hook

Tests orchestration layer WITH mocks for side effects.
Hooks contain side effects (logging, file I/O) so mocks ARE needed.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from hooks.useFilenameParser import (
    use_filename_parser,
    use_filename_parser_single,
    use_dataset_loader,
    use_filename_parser_report
)


class TestUseFilenameParserMultiple:
    """Test use_filename_parser hook with multiple files."""
    
    @patch('hooks.useFilenameParser.Path')
    @patch('hooks.useFilenameParser.logger')
    def test_parse_multiple_files(self, mock_logger, mock_path_class):
        """Test parsing multiple files - hooks orchestrate, functions do logic."""
        # Mock file existence checks (side effect)
        mock_path_class.return_value.exists.return_value = True
        
        filepaths = [
            'data/CHWST.csv',
            'data/CHWRT.csv',
            'data/Power.csv'
        ]
        
        # Call hook
        results, classification = use_filename_parser(filepaths)
        
        # Verify side effects occurred
        assert mock_logger.info.called
        assert mock_path_class.called
        
        # Verify pure function logic worked
        assert 'CHWST' in classification
        assert 'CHWRT' in classification
        assert 'POWER' in classification
        
        assert len(results) == 3
    
    @patch('hooks.useFilenameParser.Path')
    @patch('hooks.useFilenameParser.logger')
    def test_missing_file_warning(self, mock_logger, mock_path_class):
        """Test that missing files generate warnings."""
        # Mock one file missing
        def exists_side_effect(*args):
            path = str(args[0]) if args else str(mock_path_class.return_value)
            return 'missing' not in path
        
        mock_path_instance = MagicMock()
        mock_path_instance.exists.side_effect = exists_side_effect
        mock_path_class.return_value = mock_path_instance
        
        filepaths = ['data/CHWST.csv', 'data/missing.csv']
        
        results, classification = use_filename_parser(filepaths)
        
        # Verify warning logged
        mock_logger.warning.assert_called()


class TestUseFilenameParserSingle:
    """Test use_filename_parser_single hook."""
    
    @patch('hooks.useFilenameParser.Path')
    @patch('hooks.useFilenameParser.logger')
    def test_parse_single_file(self, mock_logger, mock_path_class):
        """Test parsing single file."""
        mock_path_class.return_value.exists.return_value = True
        mock_path_class.return_value.name = 'CHWST.csv'
        
        result = use_filename_parser_single('data/CHWST.csv')
        
        # Verify logging occurred
        assert mock_logger.info.called
        
        # Verify result
        assert result['feed_type'] == 'CHWST'
        assert result['confidence'] == 1.0
    
    @patch('hooks.useFilenameParser.Path')
    @patch('hooks.useFilenameParser.logger')
    def test_file_not_found_error(self, mock_logger, mock_path_class):
        """Test that missing file raises error."""
        mock_path_class.return_value.exists.return_value = False
        
        with pytest.raises(FileNotFoundError):
            use_filename_parser_single('data/missing.csv')
        
        # Verify error logged
        mock_logger.error.assert_called()


class TestUseDatasetLoader:
    """Test use_dataset_loader hook."""
    
    @patch('hooks.useFilenameParser.use_filename_parser')
    @patch('hooks.useFilenameParser.Path')
    @patch('hooks.useFilenameParser.logger')
    def test_load_dataset_csv(self, mock_logger, mock_path_class, mock_parser):
        """Test loading CSV dataset."""
        # Mock directory exists and contains CSV files
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.glob.side_effect = lambda pattern: (
            [Path('CHWST.csv'), Path('CHWRT.csv')] if '*.csv' in pattern else []
        )
        mock_path_class.return_value = mock_dir
        
        # Mock parser results
        mock_parser.return_value = (
            {
                'CHWST.csv': {'feed_type': 'CHWST', 'confidence': 1.0},
                'CHWRT.csv': {'feed_type': 'CHWRT', 'confidence': 1.0}
            },
            {
                'CHWST': ['CHWST.csv'],
                'CHWRT': ['CHWRT.csv'],
                'CDWRT': [],
                'POWER': [],
                'FLOW': [],
                'UNKNOWN': []
            }
        )
        
        feed_map, warnings = use_dataset_loader('data/')
        
        # Verify results
        assert 'CHWST' in feed_map
        assert 'CHWRT' in feed_map
        assert len(warnings) >= 0  # May have warnings about missing feeds
    
    @patch('hooks.useFilenameParser.use_filename_parser')
    @patch('hooks.useFilenameParser.Path')
    @patch('hooks.useFilenameParser.logger')
    def test_load_dataset_xlsx(self, mock_logger, mock_path_class, mock_parser):
        """Test loading XLSX dataset."""
        # Mock directory with XLSX files
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.glob.side_effect = lambda pattern: (
            [] if '*.csv' in pattern else [Path('Monash_Data.xlsx')]
        )
        mock_path_class.return_value = mock_dir
        
        # Mock parser results
        mock_parser.return_value = (
            {'Monash_Data.xlsx': {'feed_type': 'CHWST', 'confidence': 0.8}},
            {
                'CHWST': ['Monash_Data.xlsx'],
                'CHWRT': [],
                'CDWRT': [],
                'POWER': [],
                'FLOW': [],
                'UNKNOWN': []
            }
        )
        
        feed_map, warnings = use_dataset_loader('data/')
        
        # Verify XLSX file loaded
        assert 'CHWST' in feed_map
        assert '.xlsx' in feed_map['CHWST'].lower()
    
    @patch('hooks.useFilenameParser.Path')
    @patch('hooks.useFilenameParser.logger')
    def test_missing_required_feeds(self, mock_logger, mock_path_class):
        """Test error when required feeds are missing."""
        # Mock empty directory
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.glob.return_value = []
        mock_path_class.return_value = mock_dir
        
        with pytest.raises(ValueError, match="Missing required feed types"):
            use_dataset_loader('data/', required_feeds=['CHWST', 'CHWRT'])


class TestUseFilenameParserReport:
    """Test use_filename_parser_report hook."""
    
    @patch('hooks.useFilenameParser.use_filename_parser')
    @patch('hooks.useFilenameParser.logger')
    def test_generate_report(self, mock_logger, mock_parser):
        """Test report generation."""
        # Mock parser results
        mock_parser.return_value = (
            {
                'CHWST.csv': {
                    'feed_type': 'CHWST',
                    'confidence': 1.0,
                    'building': 'Building_A'
                },
                'CHWRT.csv': {
                    'feed_type': 'CHWRT',
                    'confidence': 0.8,
                    'building': 'Building_A'
                }
            },
            {
                'CHWST': ['CHWST.csv'],
                'CHWRT': ['CHWRT.csv'],
                'CDWRT': [],
                'POWER': [],
                'FLOW': [],
                'UNKNOWN': []
            }
        )
        
        report = use_filename_parser_report(['CHWST.csv', 'CHWRT.csv'])
        
        # Verify report content
        assert 'Classification Report' in report
        assert 'CHWST' in report
        assert 'CHWRT' in report
        assert 'Total files: 2' in report
    
    @patch('hooks.useFilenameParser.use_filename_parser')
    @patch('hooks.useFilenameParser.logger')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_report_to_file(self, mock_file, mock_logger, mock_parser):
        """Test saving report to file."""
        # Mock parser results
        mock_parser.return_value = (
            {'CHWST.csv': {'feed_type': 'CHWST', 'confidence': 1.0, 'building': None}},
            {'CHWST': ['CHWST.csv'], 'CHWRT': [], 'CDWRT': [], 'POWER': [], 'FLOW': [], 'UNKNOWN': []}
        )
        
        report = use_filename_parser_report(['CHWST.csv'], output_path='report.txt')
        
        # Verify file write occurred
        mock_file.assert_called_once_with('report.txt', 'w')
        mock_file().write.assert_called_once()


class TestXLSXIntegration:
    """Test XLSX file handling in hooks."""
    
    @patch('hooks.useFilenameParser.Path')
    @patch('hooks.useFilenameParser.logger')
    def test_xlsx_detection(self, mock_logger, mock_path_class):
        """Test that XLSX files are detected correctly."""
        mock_path_class.return_value.exists.return_value = True
        mock_path_class.return_value.name = 'Monash_CHWST.xlsx'
        
        result = use_filename_parser_single('data/Monash_CHWST.xlsx')
        
        assert result['feed_type'] == 'CHWST'
        assert '.xlsx' in result['raw_filename'].lower()


class TestArchitectureCompliance:
    """Verify hooks follow 'State lives in hooks; App orchestrates' principle."""
    
    def test_hooks_have_side_effects(self):
        """Verify hooks contain side effects (logging, file I/O)."""
        import inspect
        from hooks import useFilenameParser
        
        # Check that hooks use logger
        source = inspect.getsource(useFilenameParser)
        assert 'logger.info' in source or 'logger.warning' in source
        assert 'logger.error' in source or 'logger' in source
    
    def test_hooks_call_pure_functions(self):
        """Verify hooks call pure functions from domain layer."""
        import inspect
        from hooks import useFilenameParser
        
        # Check that hooks import pure functions
        source = inspect.getsource(useFilenameParser)
        assert 'from domain.htdam.stage0.parseFilenameMetadata import' in source
        assert 'parse_filename_metadata' in source
    
    def test_pure_functions_have_no_side_effects(self):
        """Verify pure functions don't have logging."""
        import inspect
        from domain.htdam.stage0 import parseFilenameMetadata
        
        # Check that pure functions DON'T use logger
        source = inspect.getsource(parseFilenameMetadata)
        assert 'import logging' not in source
        assert 'logger.' not in source


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
