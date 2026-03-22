import unittest
import json
# Import the Flask 'app' object from your main app.py file
from app import app 

class TestGlideGuruAPI(unittest.TestCase):
    def setUp(self):
        # Create the fake browser client
        self.client = app.test_client()
        # Ensure Flask catches errors rather than crashing the test runner
        app.config['TESTING'] = True 

    def test_index_page(self):
        """Test if the main HTML page loads successfully."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        # Check if your tagline is actually in the HTML
        self.assertIn(b"Beautiful flight routing", response.data)

    def test_search_api_success(self):
        """Test a valid flight search via the API."""
        payload = {
            "start": "SIN",
            "goal": "YFS",
            "mode": "Shortest",
            "max_hops": 4,
            "limit": 3
        }
        response = self.client.post('/api/search', json=payload)
        
        # 1. Did the server respond with OK?
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        
        # 2. Did it return the 'options' array and 'has_more' boolean?
        self.assertIn("options", data)
        self.assertIn("has_more", data)
        
        # 3. If there are routes, check the structure of the first one
        if len(data["options"]) > 0:
            first_option = data["options"][0]
            self.assertIn("price", first_option)
            self.assertIn("path", first_option)
            self.assertEqual(first_option["path"][0], "SIN")
            self.assertEqual(first_option["path"][-1], "YFS")

    def test_search_api_invalid_airport(self):
        """Test how the API handles fake airport codes."""
        payload = {
            "start": "FAKE1",
            "goal": "FAKE2",
            "mode": "Shortest"
        }
        response = self.client.post('/api/search', json=payload)
        
        # It should return a 400 Bad Request error, not crash the server!
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertEqual(data.get("error"), "Invalid airport")

    def test_export_json(self):
        """Test if the JSON export endpoint works correctly."""
        # Using URL parameters just like the real frontend does
        url = '/export/json?id=1&start=SIN&goal=YFS&mode=Shortest&max_hops=4'
        response = self.client.get(url)
        
        # If it returns 200, the server successfully generated the file
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/json')
        
        # Ensure the exported file contains the correct start and end points
        data = json.loads(response.data)
        self.assertEqual(data["path"][0], "SIN")
        self.assertEqual(data["path"][-1], "YFS")

if __name__ == '__main__':
    unittest.main()