import openai
from ..config import LLM_API_KEY, LLM_API_URL, LLM_MODEL_NAME

class LLMClient:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_API_URL
        )
        self.model = LLM_MODEL_NAME

    def chat_completion(self, messages, tools=None):
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto" if tools else None
        )
