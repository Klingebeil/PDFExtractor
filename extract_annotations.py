import fitz  # PyMuPDF
import sys
import os
import openai
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Set your OpenAI API key here
openai.api_key = 'YOUR OPENAI KEY'
colors_for_summaries = ["#92e1fb", "#69aff0"]  # Add multiple colors as needed

def extract_annotations(pdf_path):
    print(f"\n[INFO] Starting annotation extraction from: {pdf_path}")
    doc = fitz.open(pdf_path)
    annotations = []
    total_pages = len(doc)
    print(f"[INFO] PDF has {total_pages} pages")

    for page_num in range(total_pages):
        page = doc.load_page(page_num)
        annot = page.first_annot
        page_annotations = 0

        while annot:
            color = annot.colors.get("stroke", (0, 0, 0))  # Default to black if no color info is available
            color_hex = "#%02x%02x%02x" % (int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))

            if annot.type[0] == 8:  # Highlight
                text = ""
                quads = annot.vertices
                for i in range(0, len(quads), 4):
                    rect = fitz.Quad(quads[i:i+4]).rect
                    text += page.get_text("text", clip=rect)
                text = text.strip().replace('\n', ' ')
                text = clean_text(text)
                annotations.append({
                    "page": page_num + 1,
                    "type": "Highlight",
                    "content": text,
                    "color": color_hex,
                })
                page_annotations += 1
            elif annot.type[0] == 12:  # Text note
                annotations.append({
                    "page": page_num + 1,
                    "type": "Note",
                    "content": annot.info.get("content", "").strip(),
                    "color": color_hex,
                })
                page_annotations += 1
            annot = annot.next
        
        print(f"[INFO] Page {page_num + 1}: Found {page_annotations} annotations")

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
                    "content": f"Please, explain the following to me in bullet points. Make sure to keep scientific references!\n\n{text}",
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
                md_content += f"- **Highlight on Page {annot['page']} (Summarized){color_info}**\n"
                md_content += f"{summaries[summary_idx]}\n\n"
                summary_idx += 1
            else:
                md_content += f"- **Highlight Color: {annot['color']}**\n"
                md_content += f"> {annot['content']} (p. {annot['page']})\n\n"
        else:
            if annot['type'] == "Highlight":
                md_content += f"- **Highlight Color: {annot['color']}**\n"
                md_content += f"> {annot['content']} (p. {annot['page']})\n\n"
            elif annot['type'] == "Note":
                md_content += f"- **Note on Page {annot['page']}{color_info}**\n"
                md_content += f"- {annot['content']}\n\n"
        formatted_items += 1
    
    print(f"[INFO] Formatted {formatted_items} annotations with {summary_idx} summaries")
    return md_content

def clean_text(text):
    original_length = len(text)
    
    # Remove multiple letter-space-letter extraction patterns
    text = re.sub(r'\b(?<![\'\'])(?!a\b)(?!i\b)([a-z])(?![.])\b|\b(pp|gy|yp|gg)\b', '', text, flags=re.IGNORECASE)

    # Remove single punctuation marks and brackets (also extraction patterns)
    text = re.sub(r'( ,| ;| \? | \( | \) | ` | \), |,,),', '', text)
    
    # Combine hyphenated words
    text = re.sub(r'([a-zA-Z])-\s+([a-zA-Z])', r'\1\2', text)

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Remove extra whitespace a second time
    text = re.sub(r'\s+', ' ', text).strip()
    
    final_length = len(text)
    if final_length < original_length * 0.5:  # If more than 50% of text was removed
        print(f"[WARNING] Significant text reduction in cleaning: {original_length} -> {final_length} chars")
    
    return text

async def main(pdf_path):
    print("\n[INFO] Starting PDF annotation extraction and summarization")
    print(f"[INFO] Processing file: {pdf_path}")
    
    if not os.path.isfile(pdf_path):
        print(f"[ERROR] File not found: {pdf_path}")
        sys.exit(1)

    try:
        annotations = extract_annotations(pdf_path)
        highlight_texts = [annot['content'] for annot in annotations if annot['color'] in colors_for_summaries]
        print(f"\n[INFO] Found {len(highlight_texts)} texts to summarize")
        
        # Run summarization concurrently
        summaries = await summarize_annotations(highlight_texts)
        
        markdown_content = format_annotations_to_markdown(annotations, summaries)
        
        output_file = os.path.splitext(pdf_path)[0] + " (annotations).md"
        with open(output_file, "w") as f:
            f.write(markdown_content)
        
        print(f"\n[SUCCESS] Annotations exported to: {output_file}")
        
    except Exception as e:
        print(f"[ERROR] An error occurred during processing: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("[ERROR] Invalid number of arguments")
        print("Usage: python extract_annotations.py <path_to_pdf>")
        sys.exit(1)

    print("[INFO] Starting annotation extraction script")
    pdf_path = sys.argv[1]
    asyncio.run(main(pdf_path))
    print("[INFO] Script execution completed")
