import os
from dotenv import load_dotenv
import google.generativeai as genai
import time
from datetime import datetime

load_dotenv()
google_api_key = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=google_api_key)

def test_billing_status():
    """Test whether we're on free or paid tier by checking TPM limits"""
    print("Testing API billing status by checking TPM limits...")
    print("Will attempt to process just over 32K tokens (free tier limit)\n")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Create a text that will be about 33K tokens
        base_text = "The quick brown fox jumps over the lazy dog. " * 3300  # ~33K tokens
        
        print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
        print("Counting tokens...")
        token_count = model.count_tokens(base_text).total_tokens
        print(f"Test text contains {token_count} tokens")
        
        print("\nAttempting single request above free tier TPM limit...")
        response = model.generate_content(
            f"Here is a text: {base_text}\nQuestion: How many times does 'fox' appear?"
        )
        
        print("\nRequest succeeded! This suggests you're on the paid tier.")
        print("Response preview:", response.text[:100], "...")
        
    except Exception as e:
        error_msg = str(e)
        print("\nRequest failed with error:", error_msg)
        
        if "429" in error_msg and "quota" in error_msg.lower():
            print("\nDiagnosis: You appear to be on the free tier because:")
            print("- Error 429 (quota exceeded) at around 32K tokens")
            print("- This is the characteristic free tier TPM limit")
            print("\nTo fix this:")
            print("1. Check if billing is enabled in Google Cloud Console")
            print("2. Verify the project has billing enabled")
            print("3. Ensure the API key is associated with the paid project")
        else:
            print("\nUnexpected error type. Please check Google Cloud Console.")

if __name__ == "__main__":
    test_billing_status()
    test_billing_status()
