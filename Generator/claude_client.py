"""
Anthropic Claude client wrapper with Message Batches API support.
Supports Claude 3.5 Sonnet with batch processing for cost savings.
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
from Scraper.config import CLAUDE_CONFIG, GENERATION_CONFIG

try:
    from anthropic import Anthropic
    from tenacity import retry, stop_after_attempt, wait_exponential
except ImportError as e:
    raise ImportError(f"Missing required packages. Run: pip install anthropic tenacity\n{e}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClaudeClient:
    """
    Anthropic Claude client for synthetic text generation.
    Supports Claude 3.5 Sonnet with batch processing (50% discount).
    """
    
    # Pricing per 1M tokens (Claude 3.5 Sonnet)
    PRICING = {
        'realtime': {'input': 3.00, 'output': 15.00},
        'batch': {'input': 1.50, 'output': 7.50},  # 50% discount
    }
    
    def __init__(self):
        """Initialize Claude client."""
        if not CLAUDE_CONFIG['api_key']:
            raise ValueError("Claude API key not configured. Check .env file.")
        
        self.client = Anthropic(api_key=CLAUDE_CONFIG['api_key'])
        self.model = CLAUDE_CONFIG['model']
        self.use_batch = GENERATION_CONFIG['use_batch_when_available']
        
        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.generation_count = 0
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        # Claude uses similar tokenization to GPT, ~4 chars per token
        return len(text) // 4
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def generate_post(
        self,
        system: str,
        messages: list,
        temperature: float = 0.9,
        max_tokens: int = 500,
        use_batch: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Generate a single synthetic post using Anthropic's recommended message structure.
        Args:
            system: The system prompt string
            messages: List of user messages (examples + generation instruction)
            temperature: Sampling temperature (0-1 for Claude)
            max_tokens: Maximum output tokens
            use_batch: Override batch setting (None = use config default)
        Returns:
            Dictionary with generated text and metadata
        """
        should_use_batch = (use_batch if use_batch is not None else self.use_batch)
        if should_use_batch:
            logger.warning("Batch processing not yet implemented. Using real-time API.")
            should_use_batch = False
        try:
            start_time = time.time()
            response = self.client.messages.create(
                model=self.model,
                system=system if system else "You are a helpful assistant.",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            elapsed_time = time.time() - start_time
            generated_text = response.content[0].text
            stop_reason = response.stop_reason
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            pricing_mode = 'batch' if should_use_batch else 'realtime'
            cost = self._calculate_cost(input_tokens, output_tokens, pricing_mode)
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_cost_usd += cost
            self.generation_count += 1
            logger.info(f"Generated post with Claude: {output_tokens} tokens, ${cost:.4f}, {elapsed_time:.2f}s")
            return {
                'text': generated_text,
                'model_name': self.model,
                'model_family': 'anthropic',
                'model_type': 'claude',
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'cost_usd': cost,
                'temperature': temperature,
                'stop_reason': stop_reason,
                'generation_timestamp': datetime.utcnow().isoformat(),
                'elapsed_seconds': elapsed_time,
                'batch_processed': should_use_batch,
            }
        except Exception as e:
            logger.error(f"Error generating post with Claude: {e}")
            raise
    
    def _parse_prompt(self, prompt: str) -> tuple:
        """
        Parse prompt into system and user messages.
        Expected format: 'System: ...\n\nUser: ...' or just user message.
        """
        if 'System:' in prompt and 'User:' in prompt:
            parts = prompt.split('User:', 1)
            system_part = parts[0].replace('System:', '').strip()
            user_part = parts[1].strip()
            return system_part, user_part
        else:
            return None, prompt
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int, pricing_mode: str) -> float:
        """Calculate cost in USD for token usage."""
        pricing = self.PRICING[pricing_mode]
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
    client = ClaudeClient()
    
    test_prompt = """System: You are a Reddit user posting in programming subreddits. Your style is casual and helpful.

User: Generate a Reddit post about learning Python."""
    
    try:
        result = client.generate_post(test_prompt, temperature=0.9, max_tokens=200)
        print(f"\nGenerated text:\n{result['text']}\n")
        print(f"Metadata: {json.dumps({k: v for k, v in result.items() if k != 'text'}, indent=2)}")
        print(f"\nCost summary: {json.dumps(client.get_cost_summary(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
