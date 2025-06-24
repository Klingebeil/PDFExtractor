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
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"[ERROR] Could not open PDF file {pdf_path}: {e}")
        return []

    annotations = [] # Initialize an array to store annotation content
    highlight_colors = set() # Initialize a set to store unique highlight colors
    total_pages = len(doc)
    print(f"[INFO] PDF has {total_pages} pages")

    for page_num in range(total_pages):
        page = doc.load_page(page_num)
        annot = page.first_annot
        page_annotations = 0

        while annot:
            color = annot.colors.get("stroke", (0, 0, 0))
            r = color[0] if len(color) > 0 else 0
            g = color[1] if len(color) > 1 else 0
            b = color[2] if len(color) > 2 else 0
            color_hex = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))

            if annot.type[0] == 8:  # Highlight
                highlight_colors.add(color_hex) # Add the color to the set

                # Prioritize content from annot.info['content'] if available (user's "comment" in highlight)
                text_content_from_info = annot.info.get("content", "").strip()
                annotation_type = "Highlight"
                
                if text_content_from_info: # If there is content in the 'Contents' field
                    text = text_content_from_info
                    annotation_type = "Highlight Comment" # Differentiate this type
                else: # Otherwise, extract text from the highlighted area
                    text = ""
                    quads = annot.vertices
                    for i in range(0, len(quads), 4):
                        rect = fitz.Quad(quads[i:i+4]).rect
                        text += page.get_text("text", clip=rect)
                    text = text.strip().replace('\n', ' ')
                    text = clean_text(text)
                
                annotations.append({
                    "page": page_num + start_page,
                    "type": annotation_type, # Use the determined type
                    "content": text,
                    "color": color_hex,
                })
                page_annotations += 1
            elif annot.type[0] == 12:  # Text note (Sticky Note)
                annotations.append({
                    "page": page_num + start_page,
                    "type": "Note",
                    "content": annot.info.get("content", "").strip(),
                    "color": color_hex,
                })
                page_annotations += 1
            elif annot.type[0] == 2:  # FreeText (Text Box, Typewriter)
                annotations.append({
                    "page": page_num + start_page,
                    "type": "FreeText Comment",
                    "content": annot.info.get("content", "").strip(),
                    "color": color_hex,
                })
                page_annotations += 1
            annot = annot.next

        print(f"[INFO] Page {page_num + start_page}: Found {page_annotations} annotations")

    if doc:
        doc.close()
    print(f"[INFO] Total annotations extracted: {len(annotations)}")
    return annotations, highlight_colors

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
            elif annot['type'] == "Highlight Comment": # New type for highlights with embedded comments
                md_content += f"- **Highlight Comment on Page {annot['page']}**\n"
                md_content += f"- {annot['content']}\n\n"
            elif annot['type'] == "Note":
                md_content += f"- **Note on Page {annot['page']}**\n"
                md_content += f"- {annot['content']}\n\n"
            elif annot['type'] == "FreeText Comment": # FreeText comments
                md_content += f"- **Comment on Page {annot['page']}**\n"
                md_content += f"- {annot['content']}\n\n"
        formatted_items += 1
    
    print(f"[INFO] Formatted {formatted_items} annotations with {summary_idx} summaries")
    return md_content

def clean_text(text):
    original_length = len(text)

    # 1. Replace multiple newline characters and tabs with a single space.
    #    This is generally safe and helps standardize whitespace from PDFs.
    text = re.sub(r'[\n\t\r]+', ' ', text)

    # 2. Combine hyphenated words that were split across lines or by spaces.
    #    This is crucial for maintaining word integrity (e.g., "bio- logical" -> "biological").
    #    The original regex was good here.
    text = re.sub(r'(\w+)-\s*(\w+)', r'\1\2', text)

    # 3. Handle punctuation more carefully.
    #    Instead of removing all isolated punctuation, we'll focus on
    #    ensuring spaces around them for readability.
    #    This is the main area where the previous script was "aggressive."
    #    We'll ensure punctuation is followed by a space if it's not already.
    #    This prevents "workwe" from becoming "workwe" and keeps "understoodVarious" as "understood. Various".
    text = re.sub(r'([.,;?!])(\S)', r'\1 \2', text) # Add space after punctuation if not present

    # 4. Remove common single-character OCR noise, but with more precision.
    #    The previous regex `\b[b-hj-zB-HJ-Z]\b` was too broad as it removed
    #    single letters like 'b' or 'j' even if they were valid parts of abbreviations or codes.
    #    Instead, let's focus on actual noise like isolated special characters or
    #    single letters that are clearly not part of a word (e.g., often found
    #    due to scanning errors).
    #    For now, let's try removing only truly isolated single non-alphanumeric characters.
    #    You might need to adjust this based on the *specific* types of OCR noise you encounter.
    text = re.sub(r'\s[^a-zA-Z0-9\s]\s', ' ', text) # Removes isolated single non-alphanumeric chars
                                                # e.g., "word % other" -> "word other"

    # 5. Remove extra whitespace (multiple spaces to a single space) and strip leading/trailing whitespace.
    #    This is a standard and generally safe cleaning step.
    text = re.sub(r'\s+', ' ', text).strip()

    final_length = len(text)

    # Log a warning if a significant portion of the text was removed.
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

    used_highlight_colors = set() # Initialize here to ensure it's always defined
    try:
        metadata_yaml = extract_and_format_metadata(pdf_path)
        annotations, used_highlight_colors = extract_annotations(pdf_path, start_page) # Receive both annotations and colors
        highlight_texts = [annot['content'] for annot in annotations if annot['color'] in colors_for_summaries and annot['type'] == "Highlight"]
        print(f"\nFound {len(highlight_texts)} texts to summarize") 
        
        summaries = await summarize_annotations(highlight_texts) 
        
        annotations_markdown = format_annotations_to_markdown(annotations, summaries)
        
        final_markdown_content = metadata_yaml + annotations_markdown
        
        output_file = os.path.splitext(pdf_path)[0] + " (annotations).md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_markdown_content)
        
        print(f"\nAnnotations exported to: {output_file}")
        
        if used_highlight_colors:
            print(f"[INFO] All unique highlight colors used: {', '.join(sorted(list(used_highlight_colors)))}")
        else:
            print("[INFO] No highlight colors were found.")
        
    except ValueError as ve:
        print(f"Configuration Error: {str(ve)}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred during processing: {str(e)}")
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
