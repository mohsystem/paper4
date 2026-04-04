import os
from openai import OpenAI


class OpenAIIntegration:
    def __init__(self):
        os.environ['OPENAI_API_KEY'] = ''
        # os.environ['OPENAI_API_KEY'] = '' #my account
        self.client = OpenAI()


    def get_chat_completion(self, messages, selected_model="gpt-4o", temperature=1):
        return self.client.chat.completions.create(
            max_completion_tokens=32096,
            temperature=temperature,
            model=selected_model,
            messages=messages,
        )

    def get_completion_content(self, prompt, selected_model="gpt-4o"):
        # https://platform.openai.com/settings/organization/limits
        # https://platform.openai.com/docs/models
        completion = self.client.chat.completions.create(
            max_completion_tokens=32096,
            # top_p=0.90,
            temperature=1,
            model=selected_model,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return completion
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