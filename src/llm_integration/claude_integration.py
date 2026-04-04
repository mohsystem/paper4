import anthropic


class ClaudeIntegration:
    def __init__(self, model_name):
        # https://docs.anthropic.com/en/docs/about-claude/models
        # https://console.anthropic.com/settings/plans
        self.model = model_name
        SESSION_KEY = ""
        self.client = anthropic.Anthropic(api_key=SESSION_KEY,)

    def generate_content(self, prompt_system, prompt_desc):
        message = self.client.messages.create(
            model=self.model,
            max_tokens=16096,
            temperature=1,
            system=prompt_system,
            messages=[
                {
                    "role": "user",
                    "content": prompt_desc
                }
            ]
        )
        print(message.content)

        return message.content
