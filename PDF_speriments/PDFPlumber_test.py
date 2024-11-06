import pdfplumber
import argparse
import os
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n\n"
    return text

def write_text_to_file(text, output_path):
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(text)

def read_text_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def summarize_with_gpt4o(text):
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes text."},
            {"role": "user", "content": f"Please provide a concise summary of the following text:\n\n{text}"}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

def main():
    parser = argparse.ArgumentParser(description="Extract text from a PDF file, save it, and then summarize it using GPT-4.")
    parser.add_argument("pdf_path", help="Path to the input PDF file")
    parser.add_argument("-e", "--extracted", help="Path to save the extracted text (optional)")
    parser.add_argument("-s", "--summary", help="Path to save the summary (optional)")
    args = parser.parse_args()

    # If no extracted text path is provided, create one based on the input filename
    if not args.extracted:
        base_name = os.path.splitext(os.path.basename(args.pdf_path))[0]
        args.extracted = f"{base_name}_extracted.txt"

    # If no summary path is provided, create one based on the input filename
    if not args.summary:
        base_name = os.path.splitext(os.path.basename(args.pdf_path))[0]
        args.summary = f"{base_name}_summary.txt"

    try:
        # Extract text from PDF
        print("Extracting text from PDF...")
        extracted_text = extract_text_from_pdf(args.pdf_path)
        
        # Write extracted text to file
        print(f"Writing extracted text to {args.extracted}...")
        write_text_to_file(extracted_text, args.extracted)
        
        # Read extracted text from file
        print("Reading extracted text from file...")
        file_text = read_text_from_file(args.extracted)
        
        # Summarize text using GPT-4o
        print("Summarizing text with GPT-4o...")
        summary = summarize_with_gpt4o(file_text)
        
        # Write summary to file
        print(f"Writing summary to {args.summary}...")
        write_text_to_file(summary, args.summary)
        
        print(f"Process completed. Extracted text saved to {args.extracted} and summary saved to {args.summary}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()