This project provides a Python script to extract annotations from PDF files, summarize highlighted text using OpenAI's GPT-4, and save the output in a Markdown file.

## Features

  * Extracts highlights and notes from PDF files.
  * Summarizes highlighted text using OpenAI's GPT-4 model.
  * Supports custom starting page numbers for PDFs that are part of larger documents.
  * Outputs annotations and summaries into a Markdown file in the same directory as the PDF.

## Requirements

  * Python 3.6 or higher.
  * `PyMuPDF` (fitz).
  * `openai`.

## Installation

1.  Download the script file.
2.  Open your terminal or command prompt, navigate to the directory where you saved the script, and run the following command to install the required Python packages:
    ```bash
    pip install pymupdf openai
    ```

## Usage

1.  **Get your OpenAI API Key**: If you don't have one, you'll need to create an account and get an API key from [OpenAI's website](https://platform.openai.com/account/api-keys).
2.  **Set your API Key in the script**:
      * Open the `extract_annotations.py` file in a text editor (like Notepad, VS Code, or Sublime Text).
      * Find the line that starts with `openai.api_key = 'YOUR API KEY'` and replace it with your OpenAI API key, keeping the quotation marks around your key.
3.  **Configure Highlight Colors for Summaries (Optional)**:
      * In the same `extract_annotations.py` file, find the line:
        ```python
        colors_for_summaries = ["#92e1fb", "#69aff0", "#2ea8e5"]
        ```
      * These hex codes represent the colors of highlights that will be sent to OpenAI for summarization.
      * You can add or remove color codes from this list. If you're unsure what the hex code for a highlight color is, you can run the script once without setting any colors; the output will include the color of each highlight, making it easy to identify them.
4.  **Run the script**:
      * Open your terminal or command prompt.
      * Navigate to the directory where you saved `extract_annotations.py`.
      * Run the script using one of the following commands:
          * **Basic usage (starts counting from page 1)**:
            ```bash
            python extract_annotations.py <path_to_pdf>
            ```
            Example:
            ```bash
            python extract_annotations.py "C:\Users\YourName\Documents\example.pdf"
            ```
          * **Usage with a custom starting page number**: This is useful if your PDF is part of a larger document and you want the page numbers in the output to match the original document.
            ```bash
            python extract_annotations.py <path_to_pdf> --start-page <number>
            ```
            Example (starting from page 42):
            ```bash
            python extract_annotations.py "C:\Users\YourName\Documents\example.pdf" --start-page 42
            ```

The script will generate a Markdown file (e.g., `example (annotations).md`) in the same directory as your PDF, containing the extracted annotations and summaries.

## OpenAI Summaries

The script sends highlighted text that matches the configured colors to OpenAI with the following prompt:

"Please, explain the following to me in bullet points. Make sure to keep scientific references if they are present in the text\!"

## Example Output

Here's an example of what the generated Markdown content will look like:

```markdown
---
TITLE: Title of Your Document
---

# Annotations

- **Highlight on Page 42 (Summarized)**
  - Summary point 1
  - Summary point 2
  - Summary point 3

- **Highlight on Page 43**
  > Original highlighted text.

- **Note on Page 44 (Color: #00ff00)**
  - Content of the note.
```

## License

This project is released under the MIT License.
