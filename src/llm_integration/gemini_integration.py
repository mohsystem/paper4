# import google.generativeai as genai
# from vertexai.generative_models import GenerativeModel
from google import genai
from google.genai import types

class GeminiIntegration:
    def __init__(self, model_name="gemini-2.5-pro"):
        # Configure your API key
        self.client = genai.Client(api_key="")
        # genai.configure(api_key="")
        # https://console.cloud.google.com/vertex-ai/generative/language/create/text?createType=code&project=gen-lang-client-0375481745
        # https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models?_gl=1*x4pqgs*_ga*MTYyMTczNjUwMC4xNzE5MzE0MjQz*_ga_WH2QY8WWF5*MTcyMDIyMDU0NC44LjEuMTcyMDIyMDU0NS41OS4wLjA.&_ga=2.122733579.-1621736500.1719314243
        self.model_name=model_name
        # Initialize the model
        # self.model = genai.GenerativeModel(model_name)
        # self.model = GenerativeModel(
        #     model_name,
        #     system_instruction=[
        #     ],
        # )

    def generate_content(self, prompt):
        response = self.client.models.generate_content(
            model=self.model_name, contents=prompt,
            config=types.GenerateContentConfig(
                temperature=1
            )
        )
        # response = self.model.generate_content(
        #     contents=prompt,
        #     generation_config={
        #         "temperature": 0.9,
        #         "top_p": 0.9,
        #         "max_output_tokens": 16096,
        #     },
        #     safety_settings=[
        #         {
        #             "category": "HARM_CATEGORY_HATE_SPEECH",
        #             "threshold": "BLOCK_ONLY_HIGH",
        #         },
        #     ],
        # )
        return response.text
