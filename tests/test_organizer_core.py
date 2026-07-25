import tempfile
import unittest
from pathlib import Path

from organizer_core import category_for, execute, scan, unique_destination


class OrganizerCoreTests(unittest.TestCase):
    def test_category_for_documents_images_and_other(self):
        self.assertEqual(category_for(Path('report.pdf')), 'Documents')
        self.assertEqual(category_for(Path('photo.png')), 'Images')
        self.assertEqual(category_for(Path('unknown.custom')), 'Other')

    def test_unique_destination_adds_numeric_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp) / 'file.pdf'
            existing.write_text('already here')
            self.assertEqual(unique_destination(existing), Path(tmp) / 'file_1.pdf')

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


if __name__ == '__main__':
    unittest.main()
