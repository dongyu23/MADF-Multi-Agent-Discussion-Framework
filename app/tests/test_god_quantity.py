import unittest
from unittest.mock import MagicMock
import json
from app.agent.god import God

class TestGodAgentQuantity(unittest.TestCase):
    def setUp(self):
        self.god = God()

    def _mock_response(self, n):
        """Helper to create a mock response with n personas"""
        personas = []
        for i in range(n):
            personas.append({
                "name": f"Persona {i}",
                "title": "Test Title",
                "bio": "Test Bio",
                "theories": ["T1", "T2"],
                "stance": "Test Stance",
                "system_prompt": "Test Prompt"
            })
        
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(personas)))
        ]
        return mock_response

    def test_quantity_parsing_explicit_digit(self):
        prompt = "生成3位角色"
        expected_n = 3
        
        import app.agent.god as god_module
        original_get_chat = god_module.get_chat_completion
        
        mock_get_chat = MagicMock()
        mock_get_chat.return_value = self._mock_response(expected_n)
        god_module.get_chat_completion = mock_get_chat
        
        try:
            personas = self.god.generate_personas(prompt, n=1)
            
            # Verify prompt content contains default instruction
            call_args = mock_get_chat.call_args
            messages = call_args[0][0]
            user_content = messages[1]['content']
            self.assertIn("默认生成 1 位角色", user_content)
            self.assertIn("如果指定了数量，请严格按照该数量生成", user_content)
            
            # Verify result (which comes from mock)
            self.assertEqual(len(personas), expected_n)
            
        finally:
            god_module.get_chat_completion = original_get_chat

    def test_quantity_parsing_chinese_numeral(self):
        prompt = "创建五名角色"
        expected_n = 5
        
        import app.agent.god as god_module
        original_get_chat = god_module.get_chat_completion
        
        mock_get_chat = MagicMock()
        mock_get_chat.return_value = self._mock_response(expected_n)
        god_module.get_chat_completion = mock_get_chat
        
        try:
            personas = self.god.generate_personas(prompt, n=1)
            
            # Verify prompt content contains default instruction
            call_args = mock_get_chat.call_args
            messages = call_args[0][0]
            user_content = messages[1]['content']
            self.assertIn("默认生成 1 位角色", user_content)
            
            # Verify result
            self.assertEqual(len(personas), expected_n)
            
        finally:
            god_module.get_chat_completion = original_get_chat

    def test_quantity_parsing_no_explicit(self):
        prompt = "生成一些角色"
        default_n = 2
        
        import app.agent.god as god_module
        original_get_chat = god_module.get_chat_completion
        
        mock_get_chat = MagicMock()
        mock_get_chat.return_value = self._mock_response(default_n)
        god_module.get_chat_completion = mock_get_chat
        
        try:
            personas = self.god.generate_personas(prompt, n=default_n)
            
            # Verify prompt content contains default instruction
            call_args = mock_get_chat.call_args
            messages = call_args[0][0]
            user_content = messages[1]['content']
            self.assertIn(f"默认生成 {default_n} 位角色", user_content)
            
            # Verify result
            self.assertEqual(len(personas), default_n)
            
        finally:
            god_module.get_chat_completion = original_get_chat
            
    def test_quantity_parsing_complex_sentence(self):
        prompt = "生成有关认知心理学的3位角色"
        expected_n = 3
        
        import app.agent.god as god_module
        original_get_chat = god_module.get_chat_completion
        
        mock_get_chat = MagicMock()
        mock_get_chat.return_value = self._mock_response(expected_n)
        god_module.get_chat_completion = mock_get_chat
        
        try:
            personas = self.god.generate_personas(prompt, n=1)
            
            # Verify prompt content contains default instruction
            call_args = mock_get_chat.call_args
            messages = call_args[0][0]
            user_content = messages[1]['content']
            self.assertIn("默认生成 1 位角色", user_content)
            
            # Verify result
            self.assertEqual(len(personas), expected_n)
            
        finally:
            god_module.get_chat_completion = original_get_chat

if __name__ == '__main__':
    unittest.main()
