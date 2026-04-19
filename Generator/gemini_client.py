"""
Google Gemini client wrapper.
Supports Gemini 1.5 Flash/Pro with potential free tier usage.
"""
import os
import sys
import time
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Scraper.config import GEMINI_CONFIG

try:
    from google import genai
    from google.genai import types
    from tenacity import retry, stop_after_attempt, wait_exponential
except ImportError as e:
    raise ImportError(f"Missing required packages. Run: pip install google-genai tenacity\n{e}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiClient:
    """Google Gemini client for synthetic text generation."""
    
    # Pricing per 1M tokens (Gemini 1.5 Flash - free tier available)
    PRICING = {
        'gemini-1.5-flash': {'input': 0.075, 'output': 0.30},   # After free tier
        'gemini-1.5-flash-8b': {'input': 0.0375, 'output': 0.15},
    }
    
    def __init__(self):
        """Initialize Gemini client."""
        if not GEMINI_CONFIG['api_key']:
            raise ValueError("Gemini API key not configured. Check .env file.")
        
        self.client = genai.Client(api_key=GEMINI_CONFIG['api_key'])
        self.model_name = GEMINI_CONFIG['model']
        
        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.generation_count = 0
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        return len(text) // 4
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def generate_post(
        self,
        prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 500,
    ) -> Dict[str, Any]:
        """
        Generate a single synthetic post.
        
        Args:
            prompt: The full prompt including system instructions and examples
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
        
        Returns:
            Dictionary with generated text and metadata
        """
        # Configure generation parameters
        generation_config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        try:
            start_time = time.time()
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=generation_config,
            )
            
            elapsed_time = time.time() - start_time
            
            # Extract result
            generated_text = response.text
            
            # Estimate tokens (Gemini doesn't always return usage)
            input_tokens_est = self.estimate_tokens(prompt)
            output_tokens_est = self.estimate_tokens(generated_text)
            
            # Try to get actual token counts if available
            try:
                if hasattr(response, 'usage_metadata'):
                    input_tokens = response.usage_metadata.prompt_token_count
                    output_tokens = response.usage_metadata.candidates_token_count
                else:
                    input_tokens = input_tokens_est
                    output_tokens = output_tokens_est
            except:
                input_tokens = input_tokens_est
                output_tokens = output_tokens_est
            
            # Calculate cost (may be $0 if within free tier)
            cost = self._calculate_cost(input_tokens, output_tokens)
            
            # Update tracking
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_cost_usd += cost
            self.generation_count += 1
            
            logger.info(f"Generated post with Gemini: {output_tokens} tokens, ${cost:.4f}, {elapsed_time:.2f}s")
            
            return {
                'text': generated_text,
                'model_name': self.model_name,
                'model_family': 'google',
                'model_type': 'gemini',
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'cost_usd': cost,
                'temperature': temperature,
                'generation_timestamp': datetime.utcnow().isoformat(),
                'elapsed_seconds': elapsed_time,
                'batch_processed': False,
            }
        
        except Exception as e:
            logger.error(f"Error generating post with Gemini: {e}")
            raise
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for token usage."""
        # Use pricing if available, otherwise assume free tier
        model_pricing = self.PRICING.get(self.model_name, self.PRICING['gemini-1.5-flash'])
        cost = (input_tokens / 1_000_000 * model_pricing['input']) + \
               (output_tokens / 1_000_000 * model_pricing['output'])
        return cost
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get summary of total costs and usage."""
        return {
            'total_generations': self.generation_count,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_input_tokens + self.total_output_tokens,
            'total_cost_usd': self.total_cost_usd,
            'avg_cost_per_generation': self.total_cost_usd / max(self.generation_count, 1),
            'estimated_cost_per_1k_generations': self.total_cost_usd / max(self.generation_count, 1) * 1000,
            'note': 'May be $0 if using free tier'
        }
    
    def reset_cost_tracking(self):
        """Reset cost tracking counters."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.generation_count = 0
        logger.info("Cost tracking reset")


# Example usage
if __name__ == "__main__":
    # Test the client
    client = GeminiClient()
    
    test_prompt = """You are a Reddit user posting in programming subreddits. Your style is casual and helpful.

Generate a Reddit post about learning Python."""
    
    try:
        result = client.generate_post(test_prompt, temperature=0.9, max_tokens=200)
        print(f"\nGenerated text:\n{result['text']}\n")
        print(f"Metadata: {json.dumps({k: v for k, v in result.items() if k != 'text'}, indent=2)}")
        print(f"\nCost summary: {json.dumps(client.get_cost_summary(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
