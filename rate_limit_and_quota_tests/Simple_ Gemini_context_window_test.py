import os
from dotenv import load_dotenv
import time
from google.api_core import exceptions
import backoff
import google.generativeai as genai
from datetime import datetime

load_dotenv()
google_api_key = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=google_api_key)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate

class LimitTest:
    def __init__(self):
        self.requests_made = 0
        self.tokens_processed = 0
        self.start_time = datetime.now()
        self.successful_tests = []
        self.failed_tests = []

    def count_tokens(self, text: str) -> int:
        """Count tokens using Gemini's token counter"""
        try:
            model = genai.GenerativeModel('gemini-1.5-pro')
            tokens = model.count_tokens(text)
            return tokens.total_tokens
        except Exception as e:
            print(f"Error counting tokens: {e}")
            return 0

    def create_large_text(self, repetitions=1000):
        """Create a large text by repeating a pattern"""
        base_text = "The quick brown fox jumps over the lazy dog. " * repetitions
        return base_text

    def analyze_error(self, error):
        """Analyze the error to determine its type"""
        error_str = str(error)
        if "429" in error_str and "Resource has been exhausted" in error_str:
            return "API_QUOTA"
        elif "context length" in error_str.lower() or "too long" in error_str.lower():
            return "TOKEN_LIMIT"
        return "OTHER"

    def test_context_window(self, repetitions):
        try:
            model = ChatGoogleGenerativeAI(
                model="gemini-1.5-pro",
                temperature=0.7,
                convert_messages_to_prompt=True,
                streaming=True,
                google_api_key=google_api_key
            )
            
            large_context = self.create_large_text(repetitions)
            token_count = self.count_tokens(large_context)
            
            prompt_messages = ChatPromptTemplate.from_messages([
                ("human", f"Here's a long text: {large_context}\n\nPlease answer:\n"
                         "1. How many times does the word 'fox' appear?")
            ]).format_messages()
            
            full_prompt = prompt_messages[0].content
            total_tokens = self.count_tokens(full_prompt)
            
            print(f"\nTest #{self.requests_made + 1} with {repetitions} repetitions:")
            print(f"Text-only token count: {token_count}")
            print(f"Full prompt token count: {total_tokens}")
            
            start_time = time.time()
            response = model.invoke(prompt_messages)
            end_time = time.time()
            
            self.requests_made += 1
            self.tokens_processed += total_tokens
            
            response_time = end_time - start_time
            print(f"Response time: {response_time:.2f} seconds")
            print(f"Response: {str(response.content)[:100]}...")
            
            self.successful_tests.append({
                'repetitions': repetitions,
                'tokens': total_tokens,
                'response_time': response_time
            })
            
            return True
                
        except Exception as e:
            error_type = self.analyze_error(e)
            self.failed_tests.append({
                'repetitions': repetitions,
                'tokens': total_tokens,
                'error_type': error_type,
                'error_message': str(e)
            })
            
            if error_type == "API_QUOTA":
                print(f"\nHit API quota limit:")
                print(f"- At {repetitions} repetitions")
                print(f"- With {total_tokens} tokens")
                print(f"- After {self.requests_made} successful requests")
                print(f"- Total tokens processed: {self.tokens_processed}")
                time_running = (datetime.now() - self.start_time).total_seconds()
                print(f"- Tokens per second: {self.tokens_processed / time_running:.2f}")
            elif error_type == "TOKEN_LIMIT":
                print(f"\nHit model's token limit:")
                print(f"- At {total_tokens} tokens")
                print(f"- This is a hard limit of the model")
            else:
                print(f"\nUnexpected error: {e}")
            
            return False

    def run_graduated_tests(self):
        """Run tests with gradually increasing sizes"""
        repetitions = 1000  # Start with 1000 repetitions
        
        print("Starting graduated token tests...\n")
        print("This test will help distinguish between:")
        print("1. API Quota Limits (can be increased with higher quota/better rate limiting)")
        print("2. Token Limits (hard limit of the model's capacity)")
        
        while repetitions <= 50000:  # Cap at 50000 repetitions
            time.sleep(2)  # Wait between tests
            success = self.test_context_window(repetitions)
            
            if not success:
                break
                
            repetitions = int(repetitions * 1.5)  # Increase by 50%
        
        self.print_summary()

    def print_summary(self):
        """Print a summary of all tests"""
        print("\n=== Test Summary ===")
        print(f"Total requests made: {self.requests_made}")
        print(f"Total tokens processed: {self.tokens_processed}")
        
        if self.successful_tests:
            print("\nSuccessful Tests:")
            for test in self.successful_tests:
                print(f"- {test['repetitions']} repetitions ({test['tokens']} tokens) "
                      f"in {test['response_time']:.2f}s")
        
        if self.failed_tests:
            print("\nFailed Test:")
            failed = self.failed_tests[-1]
            print(f"- Type: {failed['error_type']}")
            print(f"- At {failed['repetitions']} repetitions")
            print(f"- With {failed['tokens']} tokens")
        
        if self.successful_tests:
            max_successful = max(test['tokens'] for test in self.successful_tests)
            print(f"\nMaximum successful token count: {max_successful}")

if __name__ == "__main__":
    tester = LimitTest()
    tester.run_graduated_tests()