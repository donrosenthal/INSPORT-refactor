import os
from dotenv import load_dotenv
import time
from google.api_core import exceptions
import google.generativeai as genai
from datetime import datetime

load_dotenv()
google_api_key = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=google_api_key)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate

class TPMLimitTest:
    def __init__(self):
        self.test_start_time = datetime.now()
        self.requests_made = 0
        self.input_tokens_total = 0
        self.output_tokens_total = 0
        self.minute_windows = {}  # Track tokens per minute window
        
    def count_tokens(self, text: str) -> int:
        model = genai.GenerativeModel('gemini-1.5-pro')
        tokens = model.count_tokens(text)
        return tokens.total_tokens
        
    def create_large_text(self, repetitions):
        base_text = "The quick brown fox jumps over the lazy dog. " * repetitions
        return base_text
        
    def update_minute_window(self, current_time, input_tokens, output_tokens):
        """Track tokens in the current minute window"""
        minute_key = current_time.strftime('%Y-%m-%d %H:%M')
        if minute_key not in self.minute_windows:
            self.minute_windows[minute_key] = {'input': 0, 'output': 0}
        self.minute_windows[minute_key]['input'] += input_tokens
        self.minute_windows[minute_key]['output'] += output_tokens
        
    def test_with_tpm_limit(self):
        """Test with respect to TPM limit, starting at 3000 repetitions"""
        repetitions = 2250 # Starting point
        
        print("Starting TPM-limited token test...")
        print("Will wait 60 seconds between each request")
        print("Starting with 3000 repetitions\n")
        
        while True:
            try:
                current_time = datetime.now()
                
                # Create and count input text
                input_text = self.create_large_text(repetitions)
                prompt_messages = ChatPromptTemplate.from_messages([
                    ("human", f"Here's a long text: {input_text}\n\nCount the word 'fox'.")
                ]).format_messages()
                
                input_tokens = self.count_tokens(prompt_messages[0].content)
                
                # Log attempt details
                print(f"\nAttempt #{self.requests_made + 1}")
                print(f"Repetitions: {repetitions}")
                print(f"Input tokens: {input_tokens}")
                print(f"Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Make the request
                model = ChatGoogleGenerativeAI(
                    model="gemini-1.5-pro",
                    temperature=0.7,
                    convert_messages_to_prompt=True,
                    streaming=True,
                    google_api_key=google_api_key
                )
                
                start_time = time.time()
                response = model.invoke(prompt_messages)
                end_time = time.time()
                
                # Count output tokens
                output_tokens = self.count_tokens(response.content)
                
                # Update totals
                self.requests_made += 1
                self.input_tokens_total += input_tokens
                self.output_tokens_total += output_tokens
                self.update_minute_window(current_time, input_tokens, output_tokens)
                
                # Log success
                print(f"Success! Response time: {end_time - start_time:.2f}s")
                print(f"Output tokens: {output_tokens}")
                elapsed = (datetime.now() - self.test_start_time).total_seconds()
                print(f"Elapsed time since start: {elapsed:.1f}s")
                print(f"Total input tokens so far: {self.input_tokens_total}")
                print(f"Total output tokens so far: {self.output_tokens_total}")
                
                # Show current minute's token usage
                minute_key = current_time.strftime('%Y-%m-%d %H:%M')
                if minute_key in self.minute_windows:
                    print(f"This minute's token usage:")
                    print(f"- Input: {self.minute_windows[minute_key]['input']}")
                    print(f"- Output: {self.minute_windows[minute_key]['output']}")
                
                # Wait n seconds before next request
                print("\nWaiting 10 seconds before next request...")
                time.sleep(10)
                
                # Increase size for next attempt (smaller increment)
                repetitions = int(repetitions * 1.2)  # 20% increase each time
                
            except Exception as e:
                elapsed_time = (datetime.now() - self.test_start_time).total_seconds()
                
                print("\n=== Test Summary ===")
                print(f"Test duration: {elapsed_time:.1f} seconds")
                print(f"Total requests made: {self.requests_made}")
                print(f"Total input tokens: {self.input_tokens_total}")
                print(f"Total output tokens: {self.output_tokens_total}")
                print(f"Input tokens per second: {self.input_tokens_total / elapsed_time:.1f}")
                print(f"Output tokens per second: {self.output_tokens_total / elapsed_time:.1f}")
                
                print("\nToken usage by minute:")
                for minute, counts in sorted(self.minute_windows.items()):
                    print(f"{minute}: Input={counts['input']}, Output={counts['output']}, "
                          f"Total={counts['input'] + counts['output']}")
                
                print(f"\nFailed at:")
                print(f"- {repetitions} repetitions")
                print(f"- {input_tokens} input tokens in last attempt")
                print(f"\nError: {str(e)}")
                break

if __name__ == "__main__":
    tester = TPMLimitTest()
    tester.test_with_tpm_limit()