import os
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions

load_dotenv()
google_api_key = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=google_api_key)

def check_api_status():
    """Check API key and quota status"""
    try:
        print("Checking API configuration...")
        
        # Get and display available models
        print("\nAvailable Models:")
        for m in genai.list_models():
            print(f"- {m.name}")
            print(f"  Rate Limits:")
            if hasattr(m, 'rate_limits'):
                print(f"  {m.rate_limits}")
            print(f"  Input token limit: {m.input_token_limit if hasattr(m, 'input_token_limit') else 'Unknown'}")
            print(f"  Output token limit: {m.output_token_limit if hasattr(m, 'output_token_limit') else 'Unknown'}")
            
        # Make a test request
        print("\nMaking test request...")
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content("What's my current API tier and rate limits?")
        
        print("\nAPI Response:")
        print(response.text)
        
        if hasattr(response, 'candidates') and response.candidates:
            print("\nResponse Metadata:")
            for candidate in response.candidates:
                if hasattr(candidate, 'citation_metadata'):
                    print(f"Citation Metadata: {candidate.citation_metadata}")
                    
        print("\nTest request successful - API key is valid and working")
        
    except exceptions.PermissionDenied as e:
        print(f"\nAPI Key Permission Error: {e}")
        print("This might indicate you're not on the intended billing tier")
    except exceptions.ResourceExhausted as e:
        print(f"\nQuota Exceeded: {e}")
        print("This suggests you're still on the free tier or have hit your limits")
    except Exception as e:
        print(f"\nUnexpected Error: {e}")

if __name__ == "__main__":
    print("Starting Gemini API status check...")
    check_api_status()