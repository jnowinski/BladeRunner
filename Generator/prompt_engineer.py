"""
Automated prompt engineering for platform-specific synthetic post generation.
Creates optimized prompts for Reddit and Bluesky separately.
"""
import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from Scraper.config import DATABASE_CONFIG, GENERATION_CONFIG

def load_platform_samples(db_path, platform, min_length=10, max_length=1000, limit=None):
    """Load valid samples for a specific platform from database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = """
        SELECT id, text, LENGTH(text) as text_length
        FROM posts
        WHERE platform = ?
          AND text IS NOT NULL
          AND TRIM(text) != ''
          AND LENGTH(text) >= ?
          AND LENGTH(text) <= ?
        ORDER BY RANDOM()
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query, (platform, min_length, max_length))
    samples = cursor.fetchall()
    conn.close()
    
    return [{'id': s[0], 'text': s[1], 'length': s[2]} for s in samples]

def create_platform_prompt_template(platform, sample_examples):
    """Create a platform-specific prompt template with examples."""
    
    if platform == 'reddit':
        system_prompt = """You are an AI assistant that generates authentic Reddit posts. Your task is to create realistic Reddit posts that match the style, tone, and content patterns of real users.

Key characteristics of Reddit posts:
- Can range from very short (one-liners, questions) to long-form discussions
- Often conversational and casual in tone
- May include personal anecdotes, opinions, questions, or discussions
- Can contain slang, internet terminology, or subreddit-specific language
- Sometimes include formatting like bullet points or paragraphs
- Vary widely in topic and depth

Generate ONE Reddit post that feels authentic and natural, similar to the examples below."""

    else:  # bluesky
        system_prompt = """You are an AI assistant that generates authentic Bluesky posts. Your task is to create realistic Bluesky posts that match the style, tone, and content patterns of real users.

Key characteristics of Bluesky posts:
- Usually concise (similar to Twitter/X, typically under 300 characters)
- Casual, conversational tone
- May include personal thoughts, observations, jokes, or commentary
- Often timely and topical
- Can be witty, thoughtful, or mundane
- May use hashtags, mentions, or emojis
- More intimate and community-focused than formal

Generate ONE Bluesky post that feels authentic and natural, similar to the examples below."""

    # Format example posts
    examples_text = "\n\n## Example Posts:\n\n"
    for i, example in enumerate(sample_examples[:12], 1):
        examples_text += f"Example {i}:\n{example['text']}\n\n"
    
    examples_text += "---\n\nNow generate ONE new post in a similar style. Output only the post text, nothing else."
    
    user_prompt = examples_text
    
    return {
        'platform': platform,
        'system_prompt': system_prompt,
        'user_prompt_template': user_prompt,
        'num_examples': len(sample_examples[:12]),
    }

def main():
    print("="*80)
    print("=== PROMPT ENGINEERING FOR SYNTHETIC POST GENERATION ===")
    print("="*80)
    
    db_path = DATABASE_CONFIG['db_path']
    samples_per_prompt = GENERATION_CONFIG.get('samples_per_prompt', 12)
    
    print(f"\nDatabase: {db_path}")
    print(f"Samples per prompt: {samples_per_prompt}")
    
    # Load samples for each platform
    platforms = ['reddit', 'bluesky']
    prompt_templates = {}
    
    for platform in platforms:
        print(f"\n--- Processing {platform.upper()} ---")
        
        # Load sample pool for this platform
        samples = load_platform_samples(db_path, platform, limit=1000)
        print(f"Loaded {len(samples):,} valid {platform} samples")
        
        # Create prompt template with example posts
        template = create_platform_prompt_template(platform, samples[:samples_per_prompt])
        prompt_templates[platform] = template
        
        print(f"✅ Created prompt template with {template['num_examples']} examples")
    
    # Save prompt templates
    output_file = Path(__file__).parent / 'prompt_templates.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'samples_per_prompt': samples_per_prompt,
                'platforms': list(platforms),
            },
            'templates': prompt_templates
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Prompt templates saved to: {output_file}")
    
    # Print template preview
    print("\n" + "="*80)
    print("=== TEMPLATE PREVIEW ===")
    print("="*80)
    for platform, template in prompt_templates.items():
        print(f"\n--- {platform.upper()} System Prompt (first 200 chars) ---")
        print(template['system_prompt'][:200] + "...")
        print(f"\nExamples included: {template['num_examples']}")
    
    print("\n" + "="*80)
    print("=== SUMMARY ===")
    print("="*80)
    print(f"Platform-specific templates created: {len(prompt_templates)}")
    print(f"Each template uses {samples_per_prompt} same-platform examples")
    print("Ready for generation: ✅")
    print("="*80)

if __name__ == "__main__":
    main()
