from openai import OpenAI
from typing import Dict


# Map prompts with keys in config.prompts.yml
class _PROMPT_MAPPING:
    REFINE_TEXT_SYSTEM = "refine_text_system"
    REFINE_TEXT_USER = "refine_text_user"


class LLM:
    def __init__(self, prompts: Dict[str, str], **openai_kwargs):
        """Initialize OpenAI client with API key."""

        self.prompts = prompts
        self.client = OpenAI(**openai_kwargs)

    def refine_text(self, text: str, context: str = "") -> str:
        """
        Extract meaningful phrases from a text that are related to the given context.

        Args:
            text (str): The full text to process
            context (str): The title/context to use as reference

        Returns:
            str: Cleaned and filtered text
        """
        if not text:
            raise ValueError("text must be provided")

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": self.prompts[_PROMPT_MAPPING.REFINE_TEXT_SYSTEM],
                    },
                    {
                        "role": "user",
                        "content": self.prompts[
                            _PROMPT_MAPPING.REFINE_TEXT_USER
                        ].format(text=text, context=context),
                    },
                ],
                temperature=0.3,
                max_tokens=500,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            raise Exception(f"Error processing description: {str(e)}")
