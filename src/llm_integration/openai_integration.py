import os
from openai import OpenAI

class OpenAIIntegration:
    def __init__(self):
        api_key = ''
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
        self.client = OpenAI(api_key=api_key)
        os.environ['OPENAI_API_KEY'] = ''

    def get_chat_completion(self, messages, selected_model="gpt-4o", temperature=1):
        # https://platform.openai.com/docs/models
        return self.client.chat.completions.create(
            max_completion_tokens=32096,
            temperature=temperature,
            model=selected_model,
            messages=messages,
        )

    def get_completion_content(self, prompt, selected_model="gpt-4o"):
        # Backward-compatible wrapper for older callers.
        return self.get_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            selected_model=selected_model,
        )
#
# from openai import OpenAI
# client = OpenAI()

# completion = client.chat.completions.create(
#     model="gpt-4o",
#     messages=[
#         {"role": "user", "content": "Write java code to sum two numbers"}
#     ]
# )
#
# print(completion.choices[0].message.content)
