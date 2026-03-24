import os
from google import genai
from google.genai import errors

class UnderwriterEngine:
    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID")
        # Start with your preferred location from env
        self.preferred_location = os.getenv("GCP_LOCATION", "asia-southeast1")
        
        self._init_client(self.preferred_location)

    def _init_client(self, location):
        self.location = location
        self.client = genai.Client(
            vertexai=True,
            project=self.project_id,
            location=self.location
        )

    def generate_test(self):
        model_id = 'gemini-3.1-flash-lite-preview'
        try:
            print(f"Attempting connection in [{self.location}]...")
            response = self.client.models.generate_content(
                model=model_id,
                contents='Environment variable test: Success.'
            )
            print(f"SUCCESS! Gemini responded from {self.location}")
            print("-" * 30)
            print(response.text)
        
        except errors.ClientError as e:
            # If Singapore (404) fails, automatically try 'global'
            if "404" in str(e) and self.location != "global":
                print(f"Model not found in {self.location}. Falling back to [global]...")
                self._init_client("global")
                self.generate_test() # Retry
            else:
                print(f"CRITICAL FAILURE: {e}")

if __name__ == "__main__":
    engine = UnderwriterEngine()
    engine.generate_test()