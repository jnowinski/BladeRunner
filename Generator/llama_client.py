"""
Groq client wrapper for Llama models.
Supports Llama 3.3 70B with fast inference and free tier.
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
from Scraper.config import GROQ_CONFIG

try:
    from groq import Groq
    from tenacity import retry, stop_after_attempt, wait_exponential
except ImportError as e:
    raise ImportError(f"Missing required packages. Run: pip install groq tenacity\n{e}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LlamaClient:
    """
    Groq client for Llama models.
    Very fast inference with generous free tier.
    """
    
    # Pricing (Groq typically has free tier, paid tier is very cheap)
    PRICING = {
        'free_tier': {'input': 0.0, 'output': 0.0},
        'paid': {'input': 0.05, 'output': 0.10},  # Approximate if using paid
    }
    
    def __init__(self):
        """Initialize Groq client."""
        if not GROQ_CONFIG['api_key']:
            raise ValueError("Groq API key not configured. Check .env file.")
        
        self.client = Groq(api_key=GROQ_CONFIG['api_key'])
        self.model = GROQ_CONFIG['model']
        
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
        # Parse prompt into system and user messages
        messages = self._parse_prompt(prompt)
        
        try:
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            elapsed_time = time.time() - start_time
            
            # Extract result
            generated_text = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            
            # Get token usage
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            # Calculate cost (likely $0 on free tier)
            cost = self._calculate_cost(input_tokens, output_tokens)
            
            # Update tracking
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_cost_usd += cost
            self.generation_count += 1
            
            logger.info(f"Generated post with Llama (Groq): {output_tokens} tokens, ${cost:.4f}, {elapsed_time:.2f}s")
            
            return {
                'text': generated_text,
                'model_name': self.model,
                'model_family': 'meta',
                'model_type': 'llama',
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'cost_usd': cost,
                'temperature': temperature,
                'finish_reason': finish_reason,
                'generation_timestamp': datetime.utcnow().isoformat(),
                'elapsed_seconds': elapsed_time,
                'batch_processed': False,
                'inference_provider': 'groq',
            }
        
        except Exception as e:
            logger.error(f"Error generating post with Llama: {e}")
            raise
    
    def _parse_prompt(self, prompt: str) -> List[Dict[str, str]]:
        """
        Parse prompt into messages format.
        Expected format: 'System: ...\n\nUser: ...' or just user message.
        """
        if 'System:' in prompt and 'User:' in prompt:
            parts = prompt.split('User:', 1)
            system_part = parts[0].replace('System:', '').strip()
            user_part = parts[1].strip()
            
            return [
                {"role": "system", "content": system_part},
                {"role": "user", "content": user_part}
            ]
        else:
            return [{"role": "user", "content": prompt}]
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for token usage (typically $0 on free tier)."""
        # Assuming free tier for most use cases
        pricing = self.PRICING['free_tier']
        cost = (input_tokens / 1_000_000 * pricing['input']) + \
               (output_tokens / 1_000_000 * pricing['output'])
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
            'note': 'Likely $0 if using Groq free tier'
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
    client = LlamaClient()
    
    test_prompt = """System: You are a Reddit user posting in programming subreddits. Your style is casual and helpful.

User: Generate a Reddit post about learning Python."""
    
    try:
        result = client.generate_post(test_prompt, temperature=0.9, max_tokens=200)
        print(f"\nGenerated text:\n{result['text']}\n")
        print(f"Metadata: {json.dumps({k: v for k, v in result.items() if k != 'text'}, indent=2)}")
        print(f"\nCost summary: {json.dumps(client.get_cost_summary(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
