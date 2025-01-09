import fitz  # PyMuPDF
import sys
import os
import openai
import re

# Set your OpenAI API ky and color of the annotations that are to be summarized here
openai.api_key = 'YOUR OPEN AI KEY'
colors_for_summaries = ["#92e1fb", "#69aff0"]  # Add multiple colors as needed

def extract_annotations(pdf_path):
    doc = fitz.open(pdf_path)
    annotations = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        annot = page.first_annot

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
            elif annot.type[0] == 12:  # Text note
                annotations.append({
                    "page": page_num + 1,
                    "type": "Note",
                    "content": annot.info.get("content", "").strip(),
                    "color": color_hex,
                })
            annot = annot.next

    return annotations

def summarize_annotations(texts):
    summaries = []
    for text in texts:
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "user",
                        "content": f"Can you explain the following to me in bullet points? Make sure to keep any scientific references!\n\n{text}",
                    }
                ]
            )
            summary = response.choices[0].message.content
            summaries.append(summary)
        except Exception as e:
            print(f"Error summarizing text: {e}")
            summaries.append("Summary not available")
    return summaries

def format_annotations_to_markdown(annotations, summaries):
    md_content = "# Annotations\n\n"
    summary_idx = 0
    
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
    
    return md_content

def clean_text(text):
    # The function strips out weird PDF encoding patterns such as " p y p " or " gy ". 
    # If pieces of the annotations should get lost. It is most likely this one that's at fault.
    
    # Remove multiple letter-space-letter extraction patterns
    text = re.sub(r'\b(?<![\'\’])(?!a\b)(?!i\b)([a-z])(?![.])\b|\b(pp|gy|yp|gg)\b', '', text, flags=re.IGNORECASE)

    # Remove single punctuation marks and brackets (also extraction patterns)
    text = re.sub(r'( ,| ;| \? | \( | \) | ` | \), |,,),', '', text)
    
    # Combine hyphenated words
    text = re.sub(r'([a-zA-Z])-\s+([a-zA-Z])', r'\1\2', text)

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Remove extra whitespace a second time
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_annotations.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    
    if not os.path.isfile(pdf_path):
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    annotations = extract_annotations(pdf_path)
    highlight_texts = [annot['content'] for annot in annotations if annot['color'] in colors_for_summaries]
    summaries = summarize_annotations(highlight_texts)
    
    markdown_content = format_annotations_to_markdown(annotations, summaries)
    
    output_file = os.path.splitext(pdf_path)[0] + " (annotations).md"
    with open(output_file, "w") as f:
        f.write(markdown_content)
    
    print(f"Annotations exported to {output_file}")
    
    print(f"Annotations exported to {output_file}")
