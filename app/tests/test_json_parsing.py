import unittest
from utils import parse_json_from_response

class TestJsonParsing(unittest.TestCase):
    def test_unescaped_quotes(self):
        # This JSON is invalid because of quotes around "情境认知教育基金会" inside the string
        invalid_json = """
        [
            {
                "name": "Test",
                "bio": "He founded the "Foundation" successfully."
            }
        ]
        """
        result = parse_json_from_response(invalid_json)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        # dirtyjson might keep the quotes or strip them depending on implementation, 
        # but it should parse.
        # Actually dirtyjson handles unquoted keys well, but unescaped double quotes inside double quotes 
        # are tricky even for it. Let's see.
        # If dirtyjson fails, we might need a regex fix.
        
    def test_valid_json(self):
        valid_json = '[{"name": "Test"}]'
        result = parse_json_from_response(valid_json)
        self.assertEqual(result[0]['name'], "Test")

if __name__ == '__main__':
    unittest.main()
