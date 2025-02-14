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

A shell script (`extract_annotations.sh`) can automate the environment setup and script execution. It can be run in the MacOS Automator by setting up a new workflow that:
1. Inputs the provided files
2. Runs the following shell script:

```bash
osascript <<EOF > /tmp/page_number.txt
set pageNumber to text returned of (display dialog "Enter starting page number (leave empty for default: 1):" default answer "1" buttons {"Cancel", "OK"} default button "OK")
return pageNumber
EOF

PAGE_NUMBER=$(cat /tmp/page_number.txt)

for f in "$@"
do
  /<YOURPATH>/PDFExtractor/run_python_script.sh "$f" "$PAGE_NUMBER"
done
```

Make sure to use the correct shell and configure input arguments properly.

### Shell Script Details

The `extract_annotations.sh` script does the following:

1. Prompts the user **once** for the starting page number and stores it.
2. Loops through all selected files, passing the same page number.
3. Activates a virtual environment.
4. Runs the Python script with the provided PDF file path and page number.
5. Logs execution details for debugging.

### Usage

1. Edit the `extract_annotations.sh` file to update the paths to your virtual environment and Python script paths:

```sh
#!/bin/zsh
# Make sure to edit this line above to your virtual environment

VENV_PATH="<YOURPATH>/PDFExtractor/venv"
SCRIPT_PATH="<YOURPATH>/PDFExtractor/extract_annotations.py"

# Activate the virtual environment
source "$VENV_PATH/bin/activate" || { echo "Failed to activate virtual environment"; exit 1; }

# Run the Python script with the provided argument
"$VENV_PATH/bin/python3" "$SCRIPT_PATH" "$1" "$2"
```

2. Make the shell script executable via the terminal:

```bash
chmod +x extract_annotations.sh
```

3. Run the shell script with the path to the PDF file as an argument:

```bash
./extract_annotations.sh <path_to_pdf>
```

This ensures that the page number is prompted **only once** and applied to all selected files.

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

---

Feel free to modify the script and README file to suit your needs.
