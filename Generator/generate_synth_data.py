"""
Main synthetic data generation pipeline.
Generates synthetic social media posts using multiple AI models with platform-specific examples.
"""
import sqlite3
import json
import random
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from Scraper.config import DATABASE_CONFIG, GENERATION_CONFIG

# Import model clients
from Generator.claude_client import ClaudeClient
from Generator.gemini_client import GeminiClient
from Generator.llama_client import LlamaClient
from Generator.azure_client import AzureOpenAIClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent / 'generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SyntheticDataGenerator:
    """Generates synthetic social media posts using multiple AI models."""
    
    def __init__(self):
        """Initialize generator with model clients and configuration."""
        self.db_path = DATABASE_CONFIG['db_path']
        self.model_distribution = GENERATION_CONFIG['model_distribution']
        self.samples_per_prompt = GENERATION_CONFIG.get('samples_per_prompt', 12)
        
        # Initialize model clients (only active ones)
        self.clients = {}
        if self.model_distribution.get('gpt54_nano', 0) > 0 or self.model_distribution.get('gpt41_mini', 0) > 0:
            azure_client = AzureOpenAIClient()
            if self.model_distribution.get('gpt54_nano', 0) > 0:
                self.clients['gpt54_nano'] = azure_client
                logger.info("✅ GPT-5.4-nano (Azure) client initialized")
            if self.model_distribution.get('gpt41_mini', 0) > 0:
                self.clients['gpt41_mini'] = azure_client
                logger.info("✅ GPT-4.1-mini (Azure) client initialized")
        if self.model_distribution.get('claude', 0) > 0:
            self.clients['claude'] = ClaudeClient()
            logger.info("✅ Claude client initialized")
        if self.model_distribution.get('gemini', 0) > 0:
            self.clients['gemini'] = GeminiClient()
            logger.info("✅ Gemini client initialized")
        if self.model_distribution.get('llama', 0) > 0:
            self.clients['llama'] = LlamaClient()
            logger.info("✅ Llama client initialized")
        
        # Load prompt templates
        templates_path = Path(__file__).parent / 'prompt_templates.json'
        with open(templates_path, 'r', encoding='utf-8-sig') as f:
            self.prompt_data = json.load(f)
        self.templates = self.prompt_data['templates']
        logger.info(f"✅ Loaded prompt templates for {len(self.templates)} platforms")
        
        # Track generation stats
        self.total_generated = 0
        self.total_cost = 0.0
        self.generation_start_time = None
    
    def select_model(self) -> str:
        """Select a model based on distribution percentages."""
        active_models = [m for m, pct in self.model_distribution.items() if pct > 0]
        weights = [self.model_distribution[m] for m in active_models]
        return random.choices(active_models, weights=weights, k=1)[0]
    
    def select_platform(self) -> str:
        """Select a platform to generate for (proportional to scraped data)."""
        # Load platform distribution from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT platform, COUNT(*) as count
            FROM posts
            WHERE text IS NOT NULL
              AND TRIM(text) != ''
              AND LENGTH(text) >= 10
              AND LENGTH(text) <= 1000
            GROUP BY platform
        """)
        results = cursor.fetchall()
        conn.close()
        
        platforms = [r[0] for r in results]
        weights = [r[1] for r in results]
        return random.choices(platforms, weights=weights, k=1)[0]
    
    def select_num_examples(self) -> int:
        """Randomly select number of examples to use (8-15) for variety."""
        return random.randint(8, 15)
    
    def load_platform_examples(self, platform: str, count: int = 12) -> List[str]:
        """Load random same-platform examples with variety in length/style."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get mix of short, medium, and long posts for diversity
        examples = []

        # Define length buckets based on platform
        if platform == 'bluesky':
            buckets = [
                (10, 100, max(1, int(count * 0.3))),      # short
                (101, 250, max(1, int(count * 0.4))),     # medium
                (251, 300, count)                         # long (fill remainder)
            ]
        else:
            buckets = [
                (10, 100, max(1, int(count * 0.3))),      # short
                (101, 400, max(1, int(count * 0.4))),     # medium
                (401, 1000, count)                        # long (fill remainder)
            ]

        examples = []
        total_needed = count
        for min_len, max_len, bucket_count in buckets:
            if len(examples) >= count:
                break
            needed = min(bucket_count, count - len(examples))
            cursor.execute("""
                SELECT text FROM posts
                WHERE platform = ?
                  AND text IS NOT NULL
                  AND TRIM(text) != ''
                  AND LENGTH(text) BETWEEN ? AND ?
                  AND (has_media = 0 OR has_media IS NULL)
                ORDER BY RANDOM()
                LIMIT ?
            """, (platform, min_len, max_len, needed))
            rows = [row[0] for row in cursor.fetchall()]
            examples.extend(rows)

        # Fallback: if not enough, fill with any available posts for platform
        if len(examples) < count:
            cursor.execute("""
                SELECT text FROM posts
                WHERE platform = ?
                  AND text IS NOT NULL
                  AND TRIM(text) != ''
                  AND (has_media = 0 OR has_media IS NULL)
                ORDER BY RANDOM()
                LIMIT ?
            """, (platform, count - len(examples)))
            rows = [row[0] for row in cursor.fetchall()]
            examples.extend(rows)

        conn.close()

        # Shuffle to mix lengths
        random.shuffle(examples)
        return examples[:count]
    
    def build_azure_messages(self, platform: str, examples: List[str]) -> dict:
        """Build structured messages for OpenAI/Azure: system prompt separate from examples."""
        template = self.templates[platform]
        system_prompt = template['system_prompt']

        example_block = "Here are some real posts from this platform to use as style inspiration:\n"
        for i, example in enumerate(examples, 1):
            example_block += f"\nExample {i}:\n{example}\n"
        example_block += (
            "\n---\n\n"
            "Write ONE new post that feels authentic to this platform. Match the natural style, tone, and energy of the examples — "
            "how casual or formal they are, how they handle capitalization and punctuation, the kinds of topics and voices used. "
            "Output only the post text, nothing else. No labels, no quotes, no commentary."
        )

        return {"system": system_prompt, "user": example_block}

    def build_prompt(self, platform: str, examples: List[str]) -> str:
        """Build a single prompt string for Gemini/Llama containing system instructions and examples."""
        template = self.templates[platform]
        system_prompt = template['system_prompt']
        
        example_block = "\n\n## Example Posts:\n"
        for i, example in enumerate(examples, 1):
            example_block += f"\nExample {i}:\n{example}\n"
        
        example_block += (
            "\n---\n\n"
            "Write ONE new post that feels authentic to this platform. Match the natural style, tone, and energy of the examples — "
            "how casual or formal they are, how they handle capitalization and punctuation, the kinds of topics and voices used. "
            "Output only the post text, nothing else."
        )
        
        return system_prompt + example_block

    def build_claude_messages(self, platform: str, examples: List[str]) -> dict:
        """Build Anthropic Claude message structure: system prompt, user messages for examples, and a final user message for generation."""
        template = self.templates[platform]
        system_prompt = template['system_prompt']
        messages = []
        # Add each example as a user message
        for example in examples:
            messages.append({"role": "user", "content": example})
        # Add the final user message as the generation instruction
        messages.append({
            "role": "user",
            "content": (
                "Write ONE new post that feels authentic to this platform. Match the natural style, tone, and energy of the examples — "
                "how casual or formal they are, how they handle capitalization and punctuation, the kinds of topics and voices used. "
                "Output only the post text, nothing else."
            )
        })
        return {"system": system_prompt, "messages": messages}
    
    def generate_post(self, platform: str, model: str) -> Optional[Dict]:
        """Generate a single synthetic post."""
        try:
            # Randomly select number of examples for variety (8-15)
            num_examples = self.select_num_examples()
            
            # Load platform-specific examples with mixed lengths
            examples = self.load_platform_examples(platform, num_examples)
            
            if len(examples) < num_examples:
                logger.warning(f"Only found {len(examples)} examples for {platform}, expected {num_examples}")
            
            # Build prompt/messages
            if model == 'claude':
                claude_struct = self.build_claude_messages(platform, examples)
                temp = random.uniform(0.9, 1.0)
                client = self.clients[model]
                result = client.generate_post(
                    system=claude_struct["system"],
                    messages=claude_struct["messages"],
                    temperature=temp,
                    max_tokens=500
                )
            elif model in ('gpt54_nano', 'gpt41_mini'):
                az_msgs = self.build_azure_messages(platform, examples)
                temp = random.uniform(0.9, 1.1)
                client = self.clients[model]
                result = client.generate_post(
                    system=az_msgs["system"],
                    user_message=az_msgs["user"],
                    model=model,
                    temperature=temp,
                    max_tokens=500
                )
            else:
                prompt = self.build_prompt(platform, examples)
                temp = random.uniform(1.0, 1.2)
                client = self.clients[model]
                result = client.generate_post(
                    prompt=prompt,
                    temperature=temp,
                    max_tokens=500
                )
            
            if result and 'text' in result:
                return {
                    'text': result['text'].strip(),
                    'platform': platform,
                    'model': model,
                    'model_family': result.get('model_family', model),
                    'cost_usd': result.get('cost_usd', 0.0),
                    'input_tokens': result.get('input_tokens', 0),
                    'output_tokens': result.get('output_tokens', 0),
                    'generated_at': datetime.now().isoformat(),
                }
            else:
                logger.error(f"Invalid result from {model}: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating post with {model} for {platform}: {e}")
            return None
    
    def save_synthetic_post(self, post_data: Dict) -> bool:
        """Save generated post to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create synthetic_posts table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS synthetic_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    text TEXT NOT NULL,
                    model TEXT NOT NULL,
                    model_family TEXT,
                    cost_usd REAL,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    generated_at TEXT,
                    text_length INTEGER,
                    is_synthetic INTEGER DEFAULT 1
                )
            """)
            
            cursor.execute("""
                INSERT INTO synthetic_posts (
                    platform, text, model, model_family, cost_usd,
                    input_tokens, output_tokens, generated_at, text_length
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_data['platform'],
                post_data['text'],
                post_data['model'],
                post_data['model_family'],
                post_data['cost_usd'],
                post_data['input_tokens'],
                post_data['output_tokens'],
                post_data['generated_at'],
                len(post_data['text'])
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error saving post to database: {e}")
            return False
    
    def generate_batch(self, num_posts: int, delay_seconds: float = 1.0):
        """Generate a batch of synthetic posts."""
        self.generation_start_time = time.time()
        logger.info(f"\n{'='*80}")
        logger.info(f"Starting generation of {num_posts:,} synthetic posts")
        logger.info(f"Model distribution: {self.model_distribution}")
        logger.info(f"{'='*80}\n")
        
        success_count = 0
        failure_count = 0
        
        for i in range(num_posts):
            # Select platform and model
            platform = self.select_platform()
            model = self.select_model()
            
            logger.info(f"[{i+1}/{num_posts}] Generating {platform} post with {model}...")
            
            # Generate post
            post_data = self.generate_post(platform, model)
            
            if post_data:
                # Save to database
                if self.save_synthetic_post(post_data):
                    success_count += 1
                    self.total_cost += post_data['cost_usd']
                    logger.info(f"  ✅ Success! Cost: ${post_data['cost_usd']:.4f} | Length: {len(post_data['text'])} chars")
                else:
                    failure_count += 1
                    logger.error(f"  ❌ Failed to save post")
            else:
                failure_count += 1
                logger.error(f"  ❌ Failed to generate post")
            
            # Progress update every 10 posts
            if (i + 1) % 10 == 0:
                elapsed = time.time() - self.generation_start_time
                rate = (i + 1) / elapsed
                logger.info(f"\n--- Progress: {i+1}/{num_posts} ({(i+1)/num_posts*100:.1f}%) ---")
                logger.info(f"Success: {success_count} | Failures: {failure_count}")
                logger.info(f"Total cost so far: ${self.total_cost:.2f}")
                logger.info(f"Rate: {rate:.2f} posts/second\n")
            
            # Delay between requests
            time.sleep(delay_seconds)
        
        # Final summary
        elapsed_total = time.time() - self.generation_start_time
        logger.info(f"\n{'='*80}")
        logger.info(f"GENERATION COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Total posts generated: {success_count:,}/{num_posts:,}")
        logger.info(f"Failures: {failure_count:,}")
        logger.info(f"Total cost: ${self.total_cost:.2f}")
        logger.info(f"Total time: {elapsed_total/60:.1f} minutes")
        logger.info(f"Average rate: {num_posts/elapsed_total:.2f} posts/second")
        logger.info(f"{'='*80}\n")
        
        # Print cost breakdown by model if available
        logger.info("Cost breakdown by model:")
        for model_name, client in self.clients.items():
            try:
                summary = client.get_cost_summary()
                logger.info(f"  {model_name}: ${summary['estimated_cost']:.2f}")
            except:
                pass


def main():
    """Main entry point for synthetic data generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate synthetic social media posts')
    parser.add_argument('--num-posts', type=int, default=100, help='Number of posts to generate')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests (seconds)')
    args = parser.parse_args()
    
    generator = SyntheticDataGenerator()
    generator.generate_batch(args.num_posts, args.delay)


if __name__ == "__main__":
    main()
