# PDF Annotation Extractor

PDF Annotation Extractor is a Python script that extracts annotations from a PDF file, summarizes highlighted text using OpenAI's GPT-4 model, and formats the extracted annotations into a Markdown file.

## Features

- Extracts highlights and notes from PDF files
- Summarizes highlighted text using OpenAI's GPT-4 model
- Supports custom starting page numbers for PDFs that are part of larger documents
- Outputs the annotations and summaries in a Markdown file into the directory of the PDF

## Requirements

- `Python 3.6` or higher
- `fitz` (PyMuPDF)
- `openai`

## Installation
1. Clone this repository or download the script file
2. Setup a python environment in the file directory
3. Install the required Python packages:

```bash
pip install pymupdf openai
```

## Usage Python Script

1. Set your OpenAI API key in the script:

```python
openai.api_key = 'your_openai_api_key'
```

2. The colors of the highlights that should be sent to OpenAI for automatic summaries can be configured in the script:

```python
colors_for_summaries = ["#92e1fb", "#69aff0"]  # Add multiple colors as needed
```

If unsure which color to choose, run the script once without setting the color first. The output will include the color of each highlight, making it easy to identify the hex codes.

3. Run the script with the path to the PDF file as an argument:

Basic usage (starts counting from page 1):
```bash
python extract_annotations.py <path_to_pdf>
```

Usage with custom starting page number:
```bash
python extract_annotations.py <path_to_pdf> --start-page <number>
```

### Examples

Standard usage, starting from page 1:
```bash
python extract_annotations.py example.pdf
```

Starting from page 42 (useful for PDFs that are part of larger documents):
```bash
python extract_annotations.py example.pdf --start-page 42
```

This will generate a Markdown file named `example (annotations).md` with the extracted annotations and summaries.

## OpenAI summaries

The script will send highlights that match the specified colors to OpenAI with the following prompt:

```
Please, explain the following to me in bullet points. Make sure to keep scientific references if they are present in the text!
```

## Using the Shell Script in MacOS Automator

A shell script (`extract_annotations.sh`) is also provided to automate the environment setup and script execution. It can be run in the MacOS Automator by setting up a new workflow that 1. inputs the provided files and 2. runs the following shell script:

```bash
for f in "$@"
do
  /<YOURPATH>/PDFExtractor/run_python_script.sh "$f"
done
```

Make sure to use the correct shell and to use the input as arguments in the configuration of the shell script.

### Shell Script Details

The `extract_annotations.sh` script does the following:

1. Creates an output directory if it doesn't exist.*
2. Logs the start of the script and the current working directory for debugging.*
3. Activates a virtual environment.
4. Runs the Python script with the provided PDF file path as an argument.
5. Logs the script completion.*

\* these steps can be deleted without impairing the function and are only provided for easier debugging.

### Usage

1. Edit the `extract_annotations.sh` file to update the paths to your virtual environment and Python script paths:

```sh
#!/bin/zsh
# Make sure to edit this line above to your virtual environment

# Path to output directory for debugging (can be deleted if not necessary)
output_dir=~/PDFExtractor

# Create output directory if it doesn't exist (can be deleted if not necessary)
mkdir -p "$output_dir"

# Log the start of the script and current working directory (can be deleted if not necessary)
echo "Starting script..." > "$output_dir/quick_action_log.txt"
echo "Current directory: $(pwd)" >> "$output_dir/quick_action_log.txt"
echo "Script path: $0" >> "$output_dir/quick_action_log.txt"
echo "Arguments: $@" >> "$output_dir/quick_action_log.txt"

# Define paths
VENV_PATH="<YOURPATH>/PDFExtractor/venv"
SCRIPT_PATH="<YOURPATH>/PDFExtractor/extract_annotations.py"

# Check paths
echo "VENV Path: $VENV_PATH" >> "$output_dir/quick_action_log.txt"
echo "Script Path: $SCRIPT_PATH" >> "$output_dir/quick_action_log.txt"

# Activate the virtual environment
source "$VENV_PATH/bin/activate" || { echo "Failed to activate virtual environment" >> "$output_dir/quick_action_log.txt"; exit 1; }

# Run the Python script with the provided argument
"$VENV_PATH/bin/python3" "$SCRIPT_PATH" "$1" >> "$output_dir/quick_action_log.txt" 2>&1

# Log the script completion (can be deleted if not necessary)
echo "Script finished." >> "$output_dir/quick_action_log.txt"
```

2. Make the shell script executable via the terminal:

```bash
chmod +x extract_annotations.sh
```

3. Run the shell script with the path to the PDF file as an argument:

```bash
./extract_annotations.sh <path_to_pdf>
```

Note: To use the custom start page with the shell script, you'll need to modify the script to pass the `--start-page` argument to the Python script.

## Script Details

### `extract_annotations(pdf_path, start_page)`

Extracts highlights and notes from the specified PDF file.

- `pdf_path`: Path to the PDF file
- `start_page`: Starting page number for the PDF (default: 1)
- Returns a list of annotations with details such as page number, type (highlight or note), content, and color

### `summarize_annotations(texts)`

Summarizes the provided texts using OpenAI's GPT-4 model.

- `texts`: List of texts to summarize
- Returns a list of summaries

### `format_annotations_to_markdown(annotations, summaries)`

Formats the annotations and summaries into Markdown content.

- `annotations`: List of annotations
- `summaries`: List of summaries corresponding to the annotations
- Returns a string containing the Markdown content

## Example Output

An example of the generated Markdown content:

```markdown
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

MIT License

Copyright (c) [2025] [Johannes Klingebiel]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Acknowledgments

- [PyMuPDF](https://github.com/pymupdf/PyMuPDF)
- [OpenAI](https://www.openai.com)

---

Feel free to modify the script and README file to suit your needs.
