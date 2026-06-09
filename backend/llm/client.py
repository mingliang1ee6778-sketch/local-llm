from openai import OpenAI


class LLMClient:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.base_url,
            timeout=settings.request_timeout_seconds,
        )

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.settings.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=self.settings.max_output_tokens,
        )
        return response.choices[0].message.content or ""
