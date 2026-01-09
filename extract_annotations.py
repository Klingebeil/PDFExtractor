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
import hashlib
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Configuration and globals
config = {}
colors_for_summaries = []

# API response cache
api_cache = {}
api_call_times = []

# Pre-compiled regex patterns for text cleaning (performance optimization)
WHITESPACE_PATTERN = re.compile(r'[\n\t\r]+')
# Improved pattern for line-break hyphens (hyphen + whitespace + continuation)
LINE_BREAK_HYPHEN_PATTERN = re.compile(r'(\w+)-\s+(\w+)')
# More selective OCR noise removal - only remove 4+ consecutive consonants
OCR_NOISE_PATTERN = re.compile(r'\b(?:[b-df-hj-np-tv-zB-DF-HJ-NP-TV-Z]\s+){4,}\b')
# Smart punctuation spacing - only after letters, preserve emails/versions
SMART_PUNCT_PATTERN = re.compile(r'([.,;?!])([a-zA-Z])')
ISOLATED_SPECIAL_PATTERN = re.compile(r'\s[^\w\s]\s')
# More conservative single character removal - only remove obvious noise
SINGLE_CHAR_NOISE_PATTERN = re.compile(r'\s+[b-df-hj-np-tv-zB-DF-HJ-NP-TV-Z]\s+(?=\s*[b-df-hj-np-tv-zB-DF-HJ-NP-TV-Z]\s+)')
EXTRA_SPACES_PATTERN = re.compile(r'\s+')

# Patterns to preserve important content
EMAIL_PATTERN = re.compile(r'\b[\w.-]+@[\w.-]+\.\w+\b')
VERSION_PATTERN = re.compile(r'\b\d+\.\d+(?:\.\d+)*\b')
FILE_EXTENSION_PATTERN = re.compile(r'\b\w+\.\w{2,4}\b')

# Common abbreviations to preserve (case insensitive)
COMMON_ABBREVIATIONS = {
    'pdf', 'usa', 'ceo', 'dna', 'rna', 'cpu', 'gpu', 'api', 'url', 'http', 'https',
    'ftp', 'ssh', 'tcp', 'udp', 'ip', 'ui', 'ux', 'ai', 'ml', 'nlp', 'ocr',
    'eu', 'uk', 'us', 'ca', 'au', 'de', 'fr', 'it', 'es', 'jp', 'cn'
}

class AnnotationType(Enum):
    HIGHLIGHT = 8
    TEXT_NOTE = 12
    FREETEXT = 2

def load_config():
    """Load configuration from config.yaml and environment variables"""
    global config, colors_for_summaries
    
    # Load YAML configuration
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.yaml')
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        colors_for_summaries = config['colors']['summary_colors']
        print(f"[INFO] Configuration loaded from {config_path}")
    except FileNotFoundError:
        print(f"[WARNING] Config file not found at {config_path}, using defaults")
        config = {
            'api': {'model': 'gpt-4', 'max_retries': 3, 'retry_delay': 1.0, 'rate_limit_per_minute': 50},
            'colors': {'summary_colors': ["#92e1fb", "#69aff0", "#2ea8e5"]},
            'prompts': {'summarization': 'Please, explain the following to me in bullet points. Make sure to keep scientific references if they are present in the text!'},
            'processing': {'max_workers': 4, 'chunk_size': 100}
        }
        colors_for_summaries = config['colors']['summary_colors']
    except Exception as e:
        print(f"[ERROR] Failed to load configuration: {e}")
        sys.exit(1)
    
    # Setup OpenAI API key from environment or config
    api_key = os.getenv('OPENAI_API_KEY')
    
    # If not in environment, try to load from config
    if not api_key and 'api' in config and 'openai_api_key' in config['api']:
        api_key = config['api']['openai_api_key']
        print("[INFO] OpenAI API key loaded from config file")
    elif api_key:
        print("[INFO] OpenAI API key loaded from environment")
    
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not found in environment or config file")
        print("[INFO] Please either:")
        print("  1. Set environment variable: export OPENAI_API_KEY='your-key-here'")
        print("  2. Add to config.yaml: api.openai_api_key: 'your-key-here'")
        sys.exit(1)
    
    openai.api_key = api_key

def rate_limit_check():
    """Simple rate limiting for API calls"""
    global api_call_times
    now = time.time()
    
    # Remove calls older than 1 minute
    api_call_times = [t for t in api_call_times if now - t < 60]
    
    # Check if we're at the rate limit
    if len(api_call_times) >= config['api']['rate_limit_per_minute']:
        wait_time = 60 - (now - api_call_times[0])
        if wait_time > 0:
            print(f"[INFO] Rate limit reached, waiting {wait_time:.1f} seconds")
            time.sleep(wait_time)
    
    api_call_times.append(now)

def get_text_hash(text: str) -> str:
    """Generate a hash for text to use as cache key"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def process_single_page(page_data: Tuple[int, fitz.Page, int]) -> Tuple[List[Dict], set]:
    """Process annotations from a single page (for concurrent processing)"""
    page_num, page, start_page = page_data
    annotations = []
    highlight_colors = set()
    
    try:
        annot = page.first_annot
        page_annotations = 0

        while annot:
            color = annot.colors.get("stroke", (0, 0, 0))
            r = color[0] if len(color) > 0 else 0
            g = color[1] if len(color) > 1 else 0
            b = color[2] if len(color) > 2 else 0
            color_hex = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))

            if annot.type[0] == AnnotationType.HIGHLIGHT.value:
                highlight_colors.add(color_hex)
                
                highlighted_text = ""
                quads = annot.vertices
                for i in range(0, len(quads), 4):
                    rect = fitz.Quad(quads[i:i+4]).rect
                    highlighted_text += page.get_text("text", clip=rect)
                highlighted_text = clean_text(highlighted_text.strip().replace('\n', ' '))
                
                text_content_from_info = annot.info.get("content", "").strip()
                
                if text_content_from_info:
                    annotations.append({
                        "page": page_num + start_page,
                        "type": "Highlight Comment",
                        "content": f"Highlighted Text: {highlighted_text}\nComment: {text_content_from_info}",
                        "color": color_hex,
                    })
                else:
                    annotations.append({
                        "page": page_num + start_page,
                        "type": "Highlight",
                        "content": highlighted_text,
                        "color": color_hex,
                    })
                page_annotations += 1
            elif annot.type[0] == AnnotationType.TEXT_NOTE.value:
                annotations.append({
                    "page": page_num + start_page,
                    "type": "Note",
                    "content": annot.info.get("content", "").strip(),
                    "color": color_hex,
                })
                page_annotations += 1
            elif annot.type[0] == AnnotationType.FREETEXT.value:
                annotations.append({
                    "page": page_num + start_page,
                    "type": "FreeText Comment",
                    "content": annot.info.get("content", "").strip(),
                    "color": color_hex,
                })
                page_annotations += 1
            annot = annot.next

        if page_annotations > 0:
            print(f"[INFO] Page {page_num + start_page}: Found {page_annotations} annotations")
            
    except Exception as e:
        print(f"[ERROR] Failed to process page {page_num + start_page}: {e}")
    
    return annotations, highlight_colors

def extract_annotations(pdf_path, start_page):
    print(f"\n[INFO] Starting annotation extraction from: {pdf_path}")
    print(f"[INFO] Using start page number: {start_page}")
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"[ERROR] Could not open PDF file {pdf_path}: {e}")
        return [], set()

    total_pages = len(doc)
    print(f"[INFO] PDF has {total_pages} pages")
    
    # Prepare data for concurrent processing
    page_data = []
    for page_num in range(total_pages):
        try:
            page = doc.load_page(page_num)
            page_data.append((page_num, page, start_page))
        except Exception as e:
            print(f"[ERROR] Could not load page {page_num}: {e}")
    
    # Process pages concurrently
    all_annotations = []
    all_highlight_colors = set()
    
    max_workers = config.get('processing', {}).get('max_workers', 4)
    
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            print(f"[INFO] Processing pages with {max_workers} workers")
            results = list(executor.map(process_single_page, page_data))
            
            # Combine results
            for annotations, highlight_colors in results:
                all_annotations.extend(annotations)
                all_highlight_colors.update(highlight_colors)
                
    except Exception as e:
        print(f"[ERROR] Concurrent processing failed: {e}")
        # Fallback to sequential processing
        print("[INFO] Falling back to sequential processing")
        for page_data_item in page_data:
            try:
                annotations, highlight_colors = process_single_page(page_data_item)
                all_annotations.extend(annotations)
                all_highlight_colors.update(highlight_colors)
            except Exception as e:
                print(f"[ERROR] Failed to process page {page_data_item[0]}: {e}")
    
    if doc:
        doc.close()
    
    print(f"[INFO] Total annotations extracted: {len(all_annotations)}")
    return all_annotations, all_highlight_colors

async def summarize_single_text(text, index):
    global api_cache
    
    print(f"[INFO] Starting summarization for text #{index + 1} (length: {len(text)} chars)")
    
    # Check cache first
    text_hash = get_text_hash(text)
    if text_hash in api_cache:
        print(f"[INFO] Using cached summary for text #{index + 1}")
        return api_cache[text_hash]
    
    max_retries = config.get('api', {}).get('max_retries', 3)
    retry_delay = config.get('api', {}).get('retry_delay', 1.0)
    model = config.get('api', {}).get('model', 'gpt-4')
    prompt_template = config.get('prompts', {}).get('summarization', 
        'Please, explain the following to me in bullet points. Make sure to keep scientific references if they are present in the text!')
    
    for attempt in range(max_retries):
        try:
            # Rate limiting
            rate_limit_check()
            
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt_template}\n\n{text}",
                    }
                ]
            )
            summary = response.choices[0].message.content
            
            # Cache the result
            api_cache[text_hash] = summary
            
            print(f"[SUCCESS] Completed summarization for text #{index + 1}")
            return summary
            
        except openai.RateLimitError as e:
            wait_time = retry_delay * (2 ** attempt)
            print(f"[WARNING] Rate limit hit for text #{index + 1}, attempt {attempt + 1}/{max_retries}, waiting {wait_time}s: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(wait_time)
            else:
                print(f"[ERROR] Max retries exceeded for text #{index + 1} due to rate limiting")
                return "Summary not available due to rate limiting"
                
        except openai.APIError as e:
            wait_time = retry_delay * (2 ** attempt)
            print(f"[WARNING] API error for text #{index + 1}, attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(wait_time)
            else:
                print(f"[ERROR] Max retries exceeded for text #{index + 1} due to API errors")
                return f"Summary not available due to API error: {str(e)}"
                
        except Exception as e:
            print(f"[ERROR] Unexpected error for text #{index + 1}, attempt {attempt + 1}/{max_retries}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                return f"Summary not available due to unexpected error: {str(e)}"
    
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
                # If for some reason a summary wasn't generated but the color is for summary
                md_content += f"> {annot['content']} (p. {annot['page']})\n\n"
        else:
            if annot['type'] == "Highlight":
                md_content += f"> {annot['content']} (p. {annot['page']})\n\n"
            elif annot['type'] == "Highlight Comment":
                # Assume the format is "Highlighted Text: ...\nComment: ..."
                lines = annot['content'].splitlines()
                highlighted = comment = ""
                for line in lines:
                    if line.startswith("Highlighted Text:"):
                        highlighted = line.replace("Highlighted Text:", "").strip()
                    elif line.startswith("Comment:"):
                        comment = line.replace("Comment:", "").strip()
                
                md_content += f"- {comment}\n\n"
                md_content += f"> {highlighted} (p. {annot['page']})\n\n"
            elif annot['type'] == "Note":
                md_content += f"- **Note on Page {annot['page']}**\n"
                md_content += f"- {annot['content']}\n\n"
            elif annot['type'] == "FreeText Comment": # FreeText comments
                md_content += f"- **Comment on Page {annot['page']}**\n"
                md_content += f"- {annot['content']}\n\n"
        formatted_items += 1
    
    print(f"[INFO] Formatted {formatted_items} annotations with {summary_idx} summaries")
    return md_content 

def _preserve_important_patterns(text):
    """Extract and temporarily replace important patterns to preserve them"""
    preservations = {}
    placeholder_counter = 0
    
    # Preserve emails
    for match in EMAIL_PATTERN.finditer(text):
        placeholder = f"__PRESERVE_EMAIL_{placeholder_counter}__"
        preservations[placeholder] = match.group()
        text = text.replace(match.group(), placeholder)
        placeholder_counter += 1
    
    # Preserve version numbers
    for match in VERSION_PATTERN.finditer(text):
        placeholder = f"__PRESERVE_VERSION_{placeholder_counter}__"
        preservations[placeholder] = match.group()
        text = text.replace(match.group(), placeholder)
        placeholder_counter += 1
    
    # Preserve file extensions
    for match in FILE_EXTENSION_PATTERN.finditer(text):
        placeholder = f"__PRESERVE_FILE_{placeholder_counter}__"
        preservations[placeholder] = match.group()
        text = text.replace(match.group(), placeholder)
        placeholder_counter += 1
    
    return text, preservations

def _restore_important_patterns(text, preservations):
    """Restore the preserved patterns"""
    for placeholder, original in preservations.items():
        text = text.replace(placeholder, original)
    return text

def _is_common_abbreviation(text_part):
    """Check if a spaced text could be a common abbreviation"""
    # Remove spaces and check if it's in our abbreviation list
    cleaned = text_part.replace(' ', '').lower()
    return cleaned in COMMON_ABBREVIATIONS

def clean_text(text):
    """Optimized text cleaning with better preservation of legitimate content"""
    if not text:
        return ""
    
    original_text = text
    original_length = len(text)
    
    try:
        # Step 1: Preserve important patterns (emails, versions, files)
        text, preservations = _preserve_important_patterns(text)
        
        # Step 2: Normalize whitespace (tabs, newlines -> single space)
        text = WHITESPACE_PATTERN.sub(' ', text)
        
        # Step 3: Smart line-break hyphen handling
        # Conservative approach: only join obvious line breaks
        def smart_line_break_hyphen_join(match):
            word1, word2 = match.groups()
            
            # Always keep very short words (x-ray, a-b, etc.)
            if len(word1) <= 2 or len(word2) <= 2:
                return f"{word1}-{word2}"
            
            # Join if second part starts with lowercase (clear continuation)
            if word2[0].islower():
                return word1 + word2
            
            # Join only very obvious prefix patterns that rarely occur as compounds
            obvious_prefixes = {'pre', 'anti', 'auto', 'semi', 'inter', 'intra', 'super', 'sub'}
            if word1.lower() in obvious_prefixes:
                return word1 + word2
                
            # Join clear suffix patterns (broken word endings)
            clear_suffixes = {'ing', 'ed', 'tion', 'sion', 'ment', 'ness', 'able', 'ible'}
            if any(word2.lower().startswith(suffix) for suffix in clear_suffixes):
                return word1 + word2
            
            # Join very long combinations (definitely broken words)
            if len(word1) + len(word2) > 15:  # Raised threshold
                return word1 + word2
            
            # Default: preserve hyphen (safer for compound words)
            return f"{word1}-{word2}"
        
        text = LINE_BREAK_HYPHEN_PATTERN.sub(smart_line_break_hyphen_join, text)
        
        # Step 4: Smart OCR noise removal with abbreviation preservation
        # First, preserve known abbreviations before applying OCR removal
        spaced_abbrevs = {}
        abbrev_counter = 0
        
        # Look for spaced patterns that might be abbreviations
        spaced_pattern = re.compile(r'\b([A-Z])\s+([A-Z])\s+([A-Z])(?:\s+[A-Z])*\b')
        for match in spaced_pattern.finditer(text):
            candidate = match.group(0)
            if _is_common_abbreviation(candidate):
                placeholder = f"__ABBREV_{abbrev_counter}__"
                spaced_abbrevs[placeholder] = candidate.replace(' ', '')  # Remove spaces
                text = text.replace(candidate, placeholder)
                abbrev_counter += 1
        
        # Now apply OCR noise removal
        text = OCR_NOISE_PATTERN.sub(' ', text)
        
        # Restore abbreviations
        for placeholder, abbrev in spaced_abbrevs.items():
            text = text.replace(placeholder, abbrev)
        
        # Step 5: Remove obvious single character noise more conservatively
        # Only remove when there are multiple consecutive single chars
        text = SINGLE_CHAR_NOISE_PATTERN.sub(' ', text)
        
        # Step 6: Smart punctuation spacing - only where needed
        text = SMART_PUNCT_PATTERN.sub(r'\1 \2', text)
        
        # Step 7: Remove isolated special characters (but not in preserved patterns)
        text = ISOLATED_SPECIAL_PATTERN.sub(' ', text)
        
        # Step 8: Final whitespace cleanup
        text = EXTRA_SPACES_PATTERN.sub(' ', text).strip()
        
        # Step 9: Restore preserved patterns
        text = _restore_important_patterns(text, preservations)
        
        final_length = len(text)
        
        # Enhanced validation and logging
        reduction_ratio = final_length / original_length if original_length > 0 else 1
        
        if reduction_ratio < 0.3 and original_length > 50:
            print(f"[WARNING] Aggressive text reduction: {original_length} -> {final_length} chars (ratio: {reduction_ratio:.2f})")
            print(f"[WARNING] Original excerpt: '{original_text[:100]}...'")
            print(f"[WARNING] Cleaned excerpt: '{text[:100]}...'")
            # Could optionally return original text or apply gentler cleaning
        elif original_length > 20:
            print(f"[DEBUG] Text cleaned: {original_length} -> {final_length} chars (ratio: {reduction_ratio:.2f})")
        
        return text
        
    except Exception as e:
        print(f"[ERROR] Text cleaning failed: {e}")
        print(f"[ERROR] Problematic text: '{original_text[:100]}...'")
        return original_text  # Return original text if cleaning fails

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
    
    # Load configuration and setup
    try:
        load_config()
    except Exception as e:
        print(f"[ERROR] Configuration failed: {e}")
        sys.exit(1)
    
    if not os.path.isfile(pdf_path):
        print(f"[ERROR] File not found: {pdf_path}")
        sys.exit(1)

    used_highlight_colors = set()
    try:
        metadata_yaml = extract_and_format_metadata(pdf_path)
        annotations, used_highlight_colors = extract_annotations(pdf_path, start_page)
        highlight_texts = [annot['content'] for annot in annotations if annot['color'] in colors_for_summaries and annot['type'] == "Highlight"]
        print(f"\nFound {len(highlight_texts)} texts to summarize") 
        
        summaries = await summarize_annotations(highlight_texts) 
        
        annotations_markdown = format_annotations_to_markdown(annotations, summaries)
        
        final_markdown_content = metadata_yaml + annotations_markdown
        
        output_file = os.path.splitext(pdf_path)[0] + " (annotations).md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_markdown_content)
        
        print(f"\nAnnotations exported to: {output_file}")
        print(f"[INFO] API cache hits: {len([k for k in api_cache.keys()])} cached responses")
        
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