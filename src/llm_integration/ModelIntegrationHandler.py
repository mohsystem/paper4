# model_integration_handler.py

import re
import logging

# Use package-relative imports so this module works when `src` is on `sys.path`
# (e.g., running `python src/app.py`) without requiring a non-existent top-level
# package like `code_generation`.
from .claude_integration import ClaudeIntegration
from .gemini_integration import GeminiIntegration
from .mistral_integration import MistralIntegration
from .openai_integration import OpenAIIntegration
from .perplexity_integration import PerplexityIntegration


class ModelIntegrationHandler:
    """
    This class encapsulates the logic for interacting with different LLM integrations.
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def generate_model_response(
            self,
            active_integration: list,
            gemini_model: list,
            mistral_model: list,
            claude_model: list,
            openai_model: list,
            perplexity_model: list,
            instruction_message: str,
            prompt_description: str,
    ) -> str:
        """
        Decide which model integration to call based on active_integration, then
        return the generated text (model response) as a string.
        """

        # Initialize return values
        model_response = ""
        generated_text = ""

        # Unpack relevant elements for readability
        active_provider, active_model_name = active_integration[0], active_integration[1]

        # 1. Gemini Integration
        if active_provider == gemini_model[0]:
            model_name = gemini_model[1]
            processor = GeminiIntegration(model_name)
            try:
                generated_text = processor.generate_content(instruction_message + prompt_description)
                model_response = generated_text
                # self.logger.info(generated_text)
                print(generated_text)
            except Exception as e:
                print(f"An error occurred while generating content (Gemini): {e}")
                self.logger.error(f"Error (Gemini): {e}")

        # 2. Mistral Integration
        elif active_provider == mistral_model[0]:
            model_name = mistral_model[1]
            processor = MistralIntegration(model_name)
            try:
                generated_text = processor.generate_content(instruction_message + prompt_description)
                model_response = generated_text
                # self.logger.info(generated_text)
                print(generated_text)
            except Exception as e:
                print(f"An error occurred while generating content (Mistral): {e}")
                self.logger.error(f"Error (Mistral): {e}")

        # 3. Claude Integration
        elif active_provider == claude_model[0]:
            model_name = claude_model[1]
            processor = ClaudeIntegration(model_name)
            try:
                # Some Claude integrations might expect two arguments:
                generated_text = processor.generate_content(instruction_message, prompt_description)
                # If it returns a list, join into one string
                model_response = ",".join(map(str, generated_text))
                model_response = re.sub(r"\\'", "'", model_response)
                # self.logger.info(model_response)
                print(model_response)
            except Exception as e:
                print(f"An error occurred while generating content (Claude): {e}")
                self.logger.error(f"Error (Claude): {e}")

        # 4. OpenAI Integration
        elif active_provider == openai_model[0]:
            selected_model = openai_model[1]
            openAIIntegration = OpenAIIntegration()
            try:
                completion = openAIIntegration.get_completion_content(
                    instruction_message + prompt_description,
                    selected_model
                )
                model_response = completion.choices[0].message.content
                print(model_response)
                # self.logger.info(model_response)
            except Exception as e:
                print(f"An error occurred while generating content (OpenAI): {e}")
                self.logger.error(f"Error (OpenAI): {e}")

        # 5. Perplexity Integration
        elif active_provider == perplexity_model[0]:
            selected_model = perplexity_model[1]
            perplexityIntegration = PerplexityIntegration()
            try:
                completion = perplexityIntegration.get_completion_content(
                    instruction_message + prompt_description,
                    selected_model
                )
                model_response = completion.choices[0].message.content
                print(model_response)
                # self.logger.info(model_response)
            except Exception as e:
                print(f"An error occurred while generating content (Perplexity): {e}")
                self.logger.error(f"Error (Perplexity): {e}")

        # 6. Unsupported Model
        else:
            print(f"Unsupported active integration: {active_integration}")
            self.logger.info(f"Unsupported active integration: {active_integration}")

        return model_response
