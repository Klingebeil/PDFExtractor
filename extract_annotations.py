#!/usr/bin/env python3

import fitz  # PyMuPDF
import sys
import os
import openai
import re
import asyncio
import argparse
from concurrent.futures import ThreadPoolExecutor
import yaml
import logging

# Set your OpenAI API key here
openai.api_key = 'YOUR OPENAI KEY'
colors_for_summaries = ["#92e1fb", "#69aff0"]  # Add multiple colors as needed

def extract_annotations(pdf_path, start_page):
    print(f"\n[INFO] Starting annotation extraction from: {pdf_path}")
    print(f"[INFO] Using start page number: {start_page}")
    try:
        doc = fitz.open(pdf_path) # Changed this line
    except Exception as e:
        print(f"[ERROR] Could not open PDF file {pdf_path}: {e}")
        return []

    annotations = []
    total_pages = len(doc)
    start_page = start_page # -1 # Normalizing start_page to avoid mistakes later in adding the extracted page_num to the start_page
    print(f"[INFO] PDF has {total_pages} pages")

    for page_num in range(total_pages):
        page = doc.load_page(page_num)
        annot = page.first_annot
        page_annotations = 0

        while annot:
            color = annot.colors.get("stroke", (0, 0, 0))
            # Safely extract RGB components, defaulting to 0 if missing
            r = color[0] if len(color) > 0 else 0
            g = color[1] if len(color) > 1 else 0
            b = color[2] if len(color) > 2 else 0
            color_hex = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))

            if annot.type[0] == 8:  # Highlight
                text = ""
                quads = annot.vertices
                for i in range(0, len(quads), 4):
                    rect = fitz.Quad(quads[i:i+4]).rect
                    text += page.get_text("text", clip=rect)
                text = text.strip().replace('\n', ' ')
                text = clean_text(text)
                annotations.append({
                    "page": page_num + start_page,  # Add start_page offset
                    "type": "Highlight",
                    "content": text,
                    "color": color_hex,
                })
                page_annotations += 1
            elif annot.type[0] == 12:  # Text note
                annotations.append({
                    "page": page_num + start_page,  # Add start_page offset
                    "type": "Note",
                    "content": annot.info.get("content", "").strip(),
                    "color": color_hex,
                })
                page_annotations += 1
            annot = annot.next
        
        print(f"[INFO] Page {page_num + start_page}: Found {page_annotations} annotations")

    if doc:
        doc.close()
    print(f"[INFO] Total annotations extracted: {len(annotations)}")
    return annotations

async def summarize_single_text(text, index):
    print(f"[INFO] Starting summarization for text #{index + 1} (length: {len(text)} chars)")
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "user",
                    "content": f"Please, explain the following to me in bullet points. Make sure to keep scientific references if they are present in the text!\n\n{text}",
                }
            ]
        )
        summary = response.choices[0].message.content
        print(f"[SUCCESS] Completed summarization for text #{index + 1}")
        return summary
    except Exception as e:
        print(f"[ERROR] Failed to summarize text #{index + 1}: {str(e)}")
        return "Summary not available"

async def summarize_annotations(texts):
    print(f"\n[INFO] Starting concurrent summarization of {len(texts)} texts")
    # Create tasks for each text
    tasks = []
    for i, text in enumerate(texts):
        tasks.append(asyncio.create_task(summarize_single_text(text, i)))
    
    print("[INFO] Waiting for all summarizations to complete...")
    # Wait for all tasks to complete
    summaries = await asyncio.gather(*tasks)
    print("[INFO] All summarizations completed")
    return summaries

def format_annotations_to_markdown(annotations, summaries):
    print("\n[INFO] Starting markdown formatting")
    md_content = "# Annotations\n\n"
    summary_idx = 0
    formatted_items = 0
    
    for annot in annotations:
        color_info = f" (Color: {annot['color']})" if 'color' in annot else ""
        if annot['color'] in colors_for_summaries:  # Check if color is in the list
            if summary_idx < len(summaries):
                md_content += f"- **Highlight on Page {annot['page']} (Summarized)**\n"
                md_content += f"{summaries[summary_idx]}\n\n"
                summary_idx += 1
            else:
                md_content += f"> {annot['content']} (p. {annot['page']})\n\n"
        else:
            if annot['type'] == "Highlight":
                md_content += f"> {annot['content']} (p. {annot['page']})\n\n"
            elif annot['type'] == "Note":
                md_content += f"- **Note on Page {annot['page']}{color_info}**\n"
                md_content += f"- {annot['content']}\n\n"
        formatted_items += 1
    
    print(f"[INFO] Formatted {formatted_items} annotations with {summary_idx} summaries")
    return md_content

def clean_text(text):
    original_length = len(text)
    
    # 1. Replace multiple newline characters and tabs with a single space
    #    This catches common PDF extraction issues where text wraps or has extra spacing.
    text = re.sub(r'[\n\t\r]+', ' ', text)

    # 2. Combine hyphenated words that were split across lines or by spaces.
    #    e.g., "bio- logical" -> "biological", "bio-\nlogical" -> "biological"
    text = re.sub(r'(\w+)-\s*(\w+)', r'\1\2', text)
    
    # 3. Remove common single-character OCR noise that often appears as isolated letters or punctuation.
    #    This is more targeted than the original pattern. It aims to remove single letters that are not 'a' or 'i' 
    #    and are followed/preceded by spaces, and common single punctuation marks.
    #    Careful consideration for scientific text: This pattern is still a heuristic.
    #    - `\b[b-hj-zB-HJ-Z]\b`: single letters (excluding 'a' and 'i') as whole words.
    #    - `[.,;:\?!]\s*`: isolated punctuation marks and spaces following them.
    #    You might need to customize this based on specific PDF quality.
    text = re.sub(r'\b[b-hj-zB-HJ-Z]\b|[.,;:\?!]\s*', '', text)

    # 4. Remove extra whitespace (multiple spaces to a single space) and strip leading/trailing whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    final_length = len(text)
    
    # Log a warning if a significant portion of the text was removed, suggesting a potential issue.
    # The threshold (0.5) and minimum original length (50) can be adjusted.
    if final_length < original_length * 0.5 and original_length > 50:
        logging.warning(f"Significant text reduction in cleaning ({original_length} -> {final_length} chars). Original start: '{text[:50]}...'")
    
    return text

def extract_and_format_metadata(pdf_path):
    """
    Extracts the title from a PDF file and formats it as "TITLE: {Title of Paper}".
    """
    logging.info(f"\nExtracting title from: {pdf_path}")
    title = ""
    try:
        doc = fitz.open(pdf_path)
        raw_metadata = doc.metadata
        doc.close()

        if raw_metadata and 'title' in raw_metadata and raw_metadata['title']:
            title = raw_metadata['title'].strip()

    except fitz.FileDataError as e:
        logging.error(f"Could not open PDF for title extraction {pdf_path}: {e}")
    except Exception as e:
        logging.error(f"An error occurred during title extraction from {pdf_path}: {e}")
    
    if title:
        logging.info(f"Title extracted: {title}")
        yaml_block = "---\n"
        yaml_block += yaml.dump({"TITLE": title}, allow_unicode=True, default_flow_style=False, sort_keys=False)
        yaml_block += "---\n\n"
        return yaml_block
    else:
        logging.warning(f"No title found or extracted for {pdf_path}.")
        return ""

async def main(pdf_path, start_page):
    print("\n[INFO] Starting PDF annotation extraction and summarization")
    print(f"[INFO] Processing file: {pdf_path}")
    print(f"[INFO] Using start page number: {start_page}")
    
    if not os.path.isfile(pdf_path):
        print(f"[ERROR] File not found: {pdf_path}")
        sys.exit(1)

    # All of the following lines need to be indented to the same level
    # as the if statement's body if they are part of the main function's execution path
    # and not part of an 'else' block.
    try: # The try block also needs to be correctly indented
        # 1. Extract and format metadata
        metadata_yaml = extract_and_format_metadata(pdf_path)

        # 2. Extract annotations
        annotations = extract_annotations(pdf_path, start_page)
        # Assuming colors_for_summaries is defined globally or passed
        highlight_texts = [annot['content'] for annot in annotations if annot['color'] in colors_for_summaries]
        # You have logging.info, but logging module is not imported.
        # For now, I'll replace it with print for demonstration.
        print(f"\nFound {len(highlight_texts)} texts to summarize") 
        
        # 3. Run summarization concurrently
        # custom_prompt and include_colors_in_output are not defined in main's scope.
        # You'll need to define them or remove them from the function calls if not used.
        # For this example, I'll remove them as they are not defined in the provided code snippet.
        summaries = await summarize_annotations(highlight_texts) 
        
        # 4. Format annotations to markdown
        annotations_markdown = format_annotations_to_markdown(annotations, summaries)
        
        # 5. Combine metadata and annotations
        final_markdown_content = metadata_yaml + annotations_markdown
        
        output_file = os.path.splitext(pdf_path)[0] + " (annotations).md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_markdown_content)
        
        print(f"\nAnnotations exported to: {output_file}")
        
    except ValueError as ve:
        print(f"Configuration Error: {str(ve)}") # Using print instead of logging
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred during processing: {str(e)}") # Using print instead of logging
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract and summarize PDF annotations')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--start-page', type=int, default=1, 
                      help='Starting page number (default: 1)')
    
    args = parser.parse_args()
    
    print("[INFO] Starting annotation extraction script")
    asyncio.run(main(args.pdf_path, args.start_page))
    print("[INFO] Script execution completed")
    
    print("[INFO] Starting annotation extraction script")
    asyncio.run(main(args.pdf_path, args.start_page))
    print("[INFO] Script execution completed")
