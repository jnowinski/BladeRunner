"""
Azure OpenAI client wrapper for GPT-5-mini and GPT-4.1-nano.
Supports both real-time and batch API processing with cost tracking.
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
from Scraper.config import AZURE_OPENAI_CONFIG, GENERATION_CONFIG

try:
    from openai import AzureOpenAI
    import tiktoken
    from tenacity import retry, stop_after_attempt, wait_exponential
except ImportError as e:
    raise ImportError(f"Missing required packages. Run: pip install openai tiktoken tenacity\n{e}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AzureOpenAIClient:
    """
    Azure OpenAI client for synthetic text generation.
    Supports GPT-5-mini (real-time) and GPT-4.1-nano (batch).
    """
    
    # Pricing per 1M tokens
    PRICING = {
        'gpt-5.4-nano': {'input': 0.10, 'output': 0.40},
        'gpt-4.1-mini': {'input': 0.075, 'output': 0.30},
    }
    
    def __init__(self):
        """Initialize Azure OpenAI client."""
        if not AZURE_OPENAI_CONFIG['api_key'] or not AZURE_OPENAI_CONFIG['endpoint']:
            raise ValueError("Azure OpenAI credentials not configured. Check .env file.")
        
        self.client = AzureOpenAI(
            api_key=AZURE_OPENAI_CONFIG['api_key'],
            api_version=AZURE_OPENAI_CONFIG['api_version'],
            azure_endpoint=AZURE_OPENAI_CONFIG['endpoint']
        )
        
        self.deployments = AZURE_OPENAI_CONFIG['deployments']
        self.use_batch = GENERATION_CONFIG['use_batch_when_available']
        
        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.generation_count = 0
        
        # Try to load tokenizer for cost estimation
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"Could not load tiktoken encoder: {e}")
            self.tokenizer = None
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a text string."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Rough estimation: ~4 chars per token
            return len(text) // 4
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def generate_post(
        self,
        prompt: str = None,
        model: str = 'gpt41_mini',
        temperature: float = 0.9,
        max_tokens: int = 500,
        use_batch: Optional[bool] = None,
        system: str = None,
        user_message: str = None,
    ) -> Dict[str, Any]:
        """
        Generate a single synthetic post.

        Args:
            prompt: Legacy single-string prompt (will be parsed into messages)
            model: 'gpt54_nano' or 'gpt41_mini'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum output tokens
            system: System prompt (preferred over prompt)
            user_message: User message content (preferred over prompt)
        """
        deployment_name = self.deployments.get(model)
        if not deployment_name:
            raise ValueError(f"Unknown model: {model}. Use 'gpt54_nano' or 'gpt41_mini'")

        # Build messages: prefer explicit system/user_message over legacy prompt string
        if system and user_message:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ]
        elif prompt:
            messages = self._parse_prompt(prompt)
        else:
            raise ValueError("Provide either 'system'+'user_message' or 'prompt'")

        try:
            start_time = time.time()

            # gpt-5.4-nano requires max_completion_tokens instead of max_tokens
            token_kwargs = {}
            if 'gpt-5.4' in deployment_name:
                token_kwargs['max_completion_tokens'] = max_tokens
            else:
                token_kwargs['max_tokens'] = max_tokens

            response = self.client.chat.completions.create(
                model=deployment_name,
                messages=messages,
                temperature=temperature,
                n=1,
                **token_kwargs
            )

            elapsed_time = time.time() - start_time
            
            # Extract result
            generated_text = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            
            # Get actual token usage
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            # Calculate cost
            if 'gpt-5.4-nano' in deployment_name:
                pricing_key = 'gpt-5.4-nano'
            elif 'gpt-4.1-mini' in deployment_name:
                pricing_key = 'gpt-4.1-mini'
            else:
                pricing_key = 'gpt-4.1-mini'
            
            cost = self._calculate_cost(input_tokens, output_tokens, pricing_key)
            
            # Update tracking
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_cost_usd += cost
            self.generation_count += 1
            
            logger.info(f"Generated post with {model}: {output_tokens} tokens, ${cost:.4f}, {elapsed_time:.2f}s")
            
            return {
                'text': generated_text,
                'model_name': deployment_name,
                'model_family': 'openai',
                'model_type': model,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'cost_usd': cost,
                'temperature': temperature,
                'finish_reason': finish_reason,
                'generation_timestamp': datetime.utcnow().isoformat(),
                'elapsed_seconds': elapsed_time,
                'batch_processed': False,
            }
        
        except Exception as e:
            logger.error(f"Error generating post with {model}: {e}")
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
            # Treat entire prompt as user message
            return [{"role": "user", "content": prompt}]
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int, model_key: str) -> float:
        """Calculate cost in USD for token usage."""
        if model_key not in self.PRICING:
            logger.warning(f"Unknown pricing for {model_key}, using gpt-5-mini rates")
            model_key = 'gpt-5-mini'
        
        pricing = self.PRICING[model_key]
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
    client = AzureOpenAIClient()
    
    test_prompt = """System: You are a Reddit user posting in programming subreddits. Your style is casual and helpful.

User: Generate a Reddit post about learning Python."""
    
    try:
        result = client.generate_post(test_prompt, model='gpt5_mini', temperature=0.9, max_tokens=200)
        print(f"\nGenerated text:\n{result['text']}\n")
        print(f"Metadata: {json.dumps({k: v for k, v in result.items() if k != 'text'}, indent=2)}")
        print(f"\nCost summary: {json.dumps(client.get_cost_summary(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
