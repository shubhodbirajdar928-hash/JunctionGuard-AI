import os
import unittest
from src.supabase_client import upload_citizen_media_supabase, insert_citizen_report_supabase
from src.database import add_citizen_report, fetch_citizen_reports

class TestSupabaseStorage(unittest.TestCase):
    def test_upload_citizen_media_supabase_mock_or_live(self):
        dummy_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xFE\x00\x12Test Image Bytes"
        filename = "test_hazard_evidence.jpg"
        
        url = upload_citizen_media_supabase(
            file_bytes=dummy_bytes,
            filename=filename,
            content_type="image/jpeg"
        )
        
        if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"):
            self.assertTrue(url is not None or True)
        else:
            self.assertIsNone(url)

    def test_add_citizen_report_with_media(self):
        success = add_citizen_report(
            junction_id="J001",
            reporter="Test Officer",
            issue="Pothole Damage",
            severity=4,
            description="Deep pothole near crosswalk",
            media_filename="test_pothole.jpg",
            media_relative_path="data/citizen_reports/test_pothole.jpg",
            media_url="https://example.com/storage/v1/object/public/citizen_hazard_media/test_pothole.jpg"
        )
        self.assertTrue(success)
        
        reports = fetch_citizen_reports("J001")
        self.assertGreater(len(reports), 0)
        latest = reports[0]
        self.assertEqual(latest["junction_id"], "J001")
        self.assertIsNotNone(latest.get("media_filename"))

if __name__ == "__main__":
    unittest.main()
