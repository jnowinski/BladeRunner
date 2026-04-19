"""
Test script to validate all model API credentials and connections.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from Generator.azure_client import AzureOpenAIClient
from Generator.claude_client import ClaudeClient
from Generator.gemini_client import GeminiClient
from Generator.llama_client import LlamaClient
from Generator.deepseek_client import DeepSeekClient

def test_model(name, client, test_prompt):
    """Test a single model client."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print('='*60)
    
    try:
        response = client.generate_post(
            prompt=test_prompt,
            temperature=0.7,
            max_tokens=100
        )
        
        if response and isinstance(response, dict) and 'text' in response:
            print(f"✅ SUCCESS!")
            response_text = response['text']
            preview = response_text[:150] if len(response_text) > 150 else response_text
            print(f"Response preview: {preview}...")
            
            # Show cost info if available
            try:
                cost_summary = client.get_cost_summary()
                if cost_summary['estimated_cost'] > 0:
                    print(f"Cost: ${cost_summary['estimated_cost']:.6f}")
            except:
                pass
            
            return True
        else:
            print(f"❌ FAILED: Received empty or invalid response")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}")
        print(f"Error: {str(e)}")
        return False

def main():
    """Run tests for all model clients."""
    
    test_prompt = """System: You are a helpful assistant that generates short social media posts.

User: Write a single short Reddit post about enjoying coffee in the morning. Keep it casual and under 50 words."""
    
    results = {}
    
    # Test Azure OpenAI (GPT-5.4-nano and GPT-4.1-mini)
    try:
        azure_client = AzureOpenAIClient()
        
        # Test GPT-5.4-nano
        print(f"\n{'='*60}")
        print(f"Testing: Azure OpenAI - GPT-5.4-nano")
        print('='*60)
        try:
            response = azure_client.generate_post(prompt=test_prompt, model='gpt54_nano', temperature=0.7, max_tokens=100)
            if response and 'text' in response:
                print(f"✅ SUCCESS!")
                print(f"Response preview: {response['text'][:150]}...")
                results['Azure GPT-5.4-nano'] = True
            else:
                print(f"❌ FAILED: Empty response")
                results['Azure GPT-5.4-nano'] = False
        except Exception as e:
            print(f"❌ FAILED: {type(e).__name__}: {e}")
            results['Azure GPT-5.4-nano'] = False
        
        # Test GPT-4.1-mini
        print(f"\n{'='*60}")
        print(f"Testing: Azure OpenAI - GPT-4.1-mini")
        print('='*60)
        try:
            response = azure_client.generate_post(prompt=test_prompt, model='gpt41_mini', temperature=0.7, max_tokens=100)
            if response and 'text' in response:
                print(f"✅ SUCCESS!")
                print(f"Response preview: {response['text'][:150]}...")
                results['Azure GPT-4.1-mini'] = True
            else:
                print(f"❌ FAILED: Empty response")
                results['Azure GPT-4.1-mini'] = False
        except Exception as e:
            print(f"❌ FAILED: {type(e).__name__}: {e}")
            results['Azure GPT-4.1-mini'] = False

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"Testing: Azure OpenAI")
        print('='*60)
        print(f"❌ FAILED TO INITIALIZE: {type(e).__name__}")
        print(f"Error: {str(e)}")
        results['Azure GPT-5.4-nano'] = False
        results['Azure GPT-4.1-mini'] = False
    
    # Test Claude
    try:
        claude_client = ClaudeClient()
        results['Claude 3.5 Sonnet'] = test_model(
            'Anthropic Claude 3.5 Sonnet',
            claude_client,
            test_prompt
        )
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"Testing: Anthropic Claude 3.5 Sonnet")
        print('='*60)
        print(f"❌ FAILED TO INITIALIZE: {type(e).__name__}")
        print(f"Error: {str(e)}")
        results['Claude 3.5 Sonnet'] = False
    
    # Test Gemini
    try:
        gemini_client = GeminiClient()
        results['Gemini 1.5 Flash'] = test_model(
            'Google Gemini 1.5 Flash',
            gemini_client,
            test_prompt
        )
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"Testing: Google Gemini 1.5 Flash")
        print('='*60)
        print(f"❌ FAILED TO INITIALIZE: {type(e).__name__}")
        print(f"Error: {str(e)}")
        results['Gemini 1.5 Flash'] = False
    
    # Test Llama (Groq)
    try:
        llama_client = LlamaClient()
        results['Llama 4 Scout'] = test_model(
            'Llama 4 Scout (via Groq)',
            llama_client,
            test_prompt
        )
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"Testing: Llama 4 Scout (via Groq)")
        print('='*60)
        print(f"❌ FAILED TO INITIALIZE: {type(e).__name__}")
        print(f"Error: {str(e)}")
        results['Llama 4 Scout'] = False
    
    # Test DeepSeek
    try:
        deepseek_client = DeepSeekClient()
        results['DeepSeek-V3'] = test_model(
            'DeepSeek-V3',
            deepseek_client,
            test_prompt
        )
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"Testing: DeepSeek-V3")
        print('='*60)
        print(f"❌ FAILED TO INITIALIZE: {type(e).__name__}")
        print(f"Error: {str(e)}")
        results['DeepSeek-V3'] = False
    
    # Summary
    print(f"\n\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for model, success in results.items():
        status = "✅ WORKING" if success else "❌ FAILED"
        print(f"{model:25} {status}")
    
    print(f"\nResults: {passed}/{total} models working")
    
    if passed == total:
        print("\n🎉 All models are configured correctly!")
    else:
        print("\n⚠️  Some models need configuration. Check the .env file.")

if __name__ == "__main__":
    main()
