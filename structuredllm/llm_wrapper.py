import os
import time
from typing import TypeVar
from dotenv import load_dotenv
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)



def google_structured_request(
    model: str,
    system_prompt: str,
    prompt: str,
    response_model: type[T],
    skip_cache: bool = False,
    timeout: float = 10,
) -> T:
    """
    Our new LLM Request wrapper for Google's Gemini.
    Includes rate limiting through timeout parameter.

    Args:
        model: Name of the model to use
        system_prompt: System prompt to guide the model
        prompt: User prompt/question
        response_model: Pydantic model class for response validation
        skip_cache: Whether to skip caching
        timeout: Number of seconds to wait before making the request
    """
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    # Implement rate limiting
    timeouts = timeout or 10
    time.sleep(timeouts)

    import google.generativeai as genai
    genai.configure(api_key=api_key)

    # Initialize model
    model = genai.GenerativeModel('gemini-1.5-flash-002')

    # Combine system and user prompts
    full_prompt = f"{system_prompt}\n\n{prompt}"

    # print("Using raw schema:", response_model)  # Debug print

    for attempt in range(3):  # Try up to 3 times
        try:
            result = model.generate_content(
                full_prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type='application/json',
                    response_schema=response_model
                ),
            )

            # Extract JSON string from response
            json_str = result.text

            # Import json here to handle the parsing
            import json

            try:
                # Parse the JSON string into a dict
                response_dict = json.loads(json_str)
            except json.JSONDecodeError as e:
                if attempt == 2:  # Last attempt
                    raise ValueError(f'Failed to parse JSON response after 3 attempts: {str(e)}') from e
                print(f"JSON parse error on attempt {attempt + 1}: {str(e)}")
                time.sleep(timeout)  # Wait before retry
                continue

            try:
                # Create and return the Pydantic model instance
                return response_model(**response_dict)
            except ValueError as e:
                if attempt == 2:  # Last attempt
                    raise ValueError(f'Validation failed after 3 attempts: {str(e)}') from e
                print(f"Validation error on attempt {attempt + 1}: {str(e)}")
                time.sleep(timeout)  # Wait before retry
                continue

        except Exception as e:
            if attempt == 2:  # Last attempt
                print(f"Error occurred: {str(e)}")  # Debug print
                raise ValueError(f'Failed to generate valid response after 3 attempts: {str(e)}') from e
            print(f"Error on attempt {attempt + 1}: {str(e)}")
            time.sleep(timeout)  # Wait before retry
