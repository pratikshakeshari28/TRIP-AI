import os
import time
 
from dotenv import load_dotenv
from google import genai
from google.genai import types
 
load_dotenv()
 
 
class LLMError(Exception):
    pass
 
 
def _model_list():
    primary = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    fallbacks = os.getenv("GEMINI_FALLBACK_MODELS", "").split(",")
    models = [primary] + [m.strip() for m in fallbacks if m.strip()]
    return list(dict.fromkeys(models))
 
 
REQUEST_TIMEOUT_MS = 15000
 
_TIMEOUT = ("timed out", "timeout", "deadline")
_RETRYABLE = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "INTERNAL")
_MODEL_MISSING = ("404", "NOT_FOUND")
 
_client = None
 
 
def is_configured():
    return bool(os.getenv("GEMINI_API_KEY"))
 
 
def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise LLMError("GEMINI_API_KEY is not set. Add it to your .env file.")
        _client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
        )
    return _client
 
 
def generate_response(prompt, system_instruction=None, temperature=0.6, retries=2):
    client = _get_client()
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
    )
 
    last_error = "unknown error"
 
    for model in _model_list():
        for attempt in range(retries):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )
                text = (response.text or "").strip()
                if text:
                    return text
                last_error = f"{model} returned an empty response"
                break
 
            except Exception as error:
                message = str(error)
                last_error = message
 
                if any(word in message.lower() for word in _TIMEOUT):
                    raise LLMError("Gemini took longer than 15 seconds to answer.") from error
 
                if any(code in message for code in _MODEL_MISSING):
                    break
 
                if any(code in message for code in _RETRYABLE):
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    break
 
                raise LLMError(f"Gemini request failed: {message}") from error
 
    raise LLMError(f"Gemini is unavailable right now: {last_error}")
 
