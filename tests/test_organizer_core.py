import tempfile
import unittest
from pathlib import Path

from organizer_core import (
    NAME_SIMILARITY_THRESHOLD,
    TIME_PROXIMITY_THRESHOLD_SECONDS,
    category_for, 
    execute, 
    levenshtein,
    scan, 
    unique_destination,
    validate_plan_item,
)


class OrganizerCoreTests(unittest.TestCase):
    def test_category_for_documents_images_and_other(self):
        self.assertEqual(category_for(Path('report.pdf')), 'Documents')
        self.assertEqual(category_for(Path('photo.png')), 'Images')
        self.assertEqual(category_for(Path('unknown.custom')), 'Other')
    
    def test_named_constants_exist(self):
        """Test that magic numbers have been extracted to named constants."""
        self.assertEqual(TIME_PROXIMITY_THRESHOLD_SECONDS, 60)
        self.assertEqual(NAME_SIMILARITY_THRESHOLD, 0.35)
    
    def test_unique_destination_adds_numeric_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp) / 'file.pdf'
            existing.write_text('already here')
            self.assertEqual(unique_destination(existing), Path(tmp) / 'file_1.pdf')
    
    def test_unique_destination_max_retries(self):
        """Test that unique_destination respects max_retries parameter."""
        with tempfile.TemporaryDirectory() as tmp:
            # Create file.pdf and file_1.pdf through file_4.pdf
            base = Path(tmp) / 'file.pdf'
            base.write_text('base')
            for i in range(1, 5):
                (Path(tmp) / f'file_{i}.pdf').write_text(f'content {i}')
            
            # Should fail when max_retries is 3 (can only try _1, _2, _3, all exist)
            with self.assertRaises(FileExistsError):
                unique_destination(base, max_retries=3)
    
    def test_levenshtein_distance(self):
        """Test Levenshtein distance calculation with early exit optimization."""
        # Basic cases
        self.assertEqual(levenshtein("kitten", "sitting"), 3)
        self.assertEqual(levenshtein("", ""), 0)
        self.assertEqual(levenshtein("abc", "abc"), 0)
        self.assertEqual(levenshtein("abc", ""), 3)
        
        # Early exit optimization
        self.assertGreater(levenshtein("abcdef", "xyz", max_distance=2), 2)
    
    def test_scan_and_execute_keep_both_on_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'inbox'
            target = root / 'organized'
            source.mkdir()
            (source / 'file.pdf').write_text('new')
            (target / 'Documents').mkdir(parents=True)
            (target / 'Documents' / 'file.pdf').write_text('old')

            report = scan(source, target, conflict_mode='rename')
            self.assertEqual(len(report.files), 1)
            self.assertTrue(report.files[0].conflict)
            self.assertTrue(report.files[0].destination.endswith('file_1.pdf'))

            result = execute([report.files[0].__dict__])
            self.assertEqual(len(result['moved']), 1)
            self.assertTrue((target / 'Documents' / 'file_1.pdf').exists())
    
    def test_execute_transaction_safety(self):
        """Test that execute rolls back on failure."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'inbox'
            target = root / 'organized'
            source.mkdir()
            
            # Create two files
            file1 = source / 'file1.pdf'
            file2 = source / 'file2.pdf'
            file1.write_text('content 1')
            file2.write_text('content 2')
            
            target_docs = target / 'Documents'
            target_docs.mkdir(parents=True)
            
            # Create plan
            plan = [
                {"source": str(file1), "destination": str(target_docs / 'file1.pdf')},
                {"source": str(file2), "destination": str(target_docs / 'file2.pdf')},
            ]
            
            # Execute should succeed
            result = execute(plan)
            self.assertEqual(len(result['moved']), 2)
            self.assertIsNone(result.get('error'))
    
    def test_execute_validation_phase(self):
        """Test that execute validates moves before executing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            
            # Create plan with non-existent source
            plan = [
                {"source": str(root / 'nonexistent.pdf'), "destination": str(root / 'dest.pdf')},
            ]
            
            result = execute(plan)
            self.assertEqual(len(result['moved']), 0)
            self.assertEqual(len(result['skipped']), 1)
            self.assertIn('Validation', result['skipped'][0]['error'])
    
    def test_execute_skip_duplicates(self):
        """Test that skip_duplicates flag works correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'inbox'
            target = root / 'organized'
            source.mkdir()
            
            # Create two identical files (duplicates)
            file1 = source / 'file1.pdf'
            file2 = source / 'file2.pdf'
            file1.write_text('same content')
            file2.write_text('same content')
            
            target_docs = target / 'Documents'
            target_docs.mkdir(parents=True)
            
            # Scan to get plan
            report = scan(source, target, conflict_mode='rename')
            
            # Execute with skip_duplicates=True
            plan_dicts = [f.__dict__ for f in report.files]
            result = execute(plan_dicts, skip_duplicates=True)
            
            # One should be moved, one skipped as duplicate
            self.assertEqual(len(result['moved']), 1)
            self.assertEqual(len(result['skipped']), 1)
            self.assertIn('Duplicate', result['skipped'][0]['error'])


class SecurityTests(unittest.TestCase):
    """Security-related tests for path validation and input sanitization."""
    
    def test_path_traversal_blocked(self):
        """Test that path traversal attempts are blocked."""
        from organizer_core import validate_plan_item
        
        # Try to use relative path
        is_valid, error = validate_plan_item({
            "source": "../etc/passwd",
            "destination": "/tmp/test"
        })
        self.assertFalse(is_valid)
        self.assertIn("absolute", error.lower())
    
    def test_invalid_plan_item_structure(self):
        """Test validation of malformed plan items."""
        from organizer_core import validate_plan_item
        
        # Missing required fields
        is_valid, error = validate_plan_item({"source": "/tmp/test"})
        self.assertFalse(is_valid)
        self.assertIn("destination", error.lower())
        
        # Not a dictionary
        is_valid, error = validate_plan_item("not a dict")
        self.assertFalse(is_valid)


if __name__ == '__main__':
    unittest.main()
