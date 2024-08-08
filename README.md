# PDF Annotation Extractor

PDF Annotation Extractor is a Python script that extracts annotations from a PDF file, summarizes highlighted text using OpenAI's GPT-4 model, and formats the extracted annotations into a Markdown file.

## Features

- Extracts highlights and notes from PDF files.
- Summarizes highlighted text using OpenAI's GPT-4 model.
- Outputs the annotations and summaries in a Markdown file.

## Requirements

- Python 3.6 or higher
- `fitz` (PyMuPDF)
- `openai`

## Installation

1. Install the required Python packages:

```bash
pip install pymupdf openai
```

2. Clone this repository or download the script file.

## Usage

1. Set your OpenAI API key in the script:

```python
openai.api_key = 'your_openai_api_key'
```

2. Run the script with the path to the PDF file as an argument:

```bash
python extract_annotations.py <path_to_pdf>
```

### Example

```bash
python extract_annotations.py example.pdf
```

This will generate a Markdown file named `example_annotations.md` with the extracted annotations and summaries.

## Using the Shell Script

A shell script (`extract_annotations.sh`) is also provided to automate the environment setup and script execution.

### Shell Script Details

The `extract_annotations.sh` script does the following:

1. Creates an output directory if it doesn't exist.
2. Logs the start of the script and the current working directory.
3. Activates a virtual environment.
4. Runs the Python script with the provided PDF file path as an argument.
5. Logs the script completion.

### Usage

1. Edit the `extract_annotations.sh` file to update the paths to your virtual environment and Python script:

```sh
#!/bin/zsh

output_dir=~/PDFExtractor

# Create output directory if it doesn't exist
mkdir -p "$output_dir"

# Log the start of the script and current working directory
echo "Starting script..." > "$output_dir/quick_action_log.txt"
echo "Current directory: $(pwd)" >> "$output_dir/quick_action_log.txt"
echo "Script path: $0" >> "$output_dir/quick_action_log.txt"
echo "Arguments: $@" >> "$output_dir/quick_action_log.txt"

# Define paths
VENV_PATH="/path/to/your/venv"
SCRIPT_PATH="/path/to/your/extract_annotations.py"

# Check paths
echo "VENV Path: $VENV_PATH" >> "$output_dir/quick_action_log.txt"
echo "Script Path: $SCRIPT_PATH" >> "$output_dir/quick_action_log.txt"

# Activate the virtual environment
source "$VENV_PATH/bin/activate" || { echo "Failed to activate virtual environment" >> "$output_dir/quick_action_log.txt"; exit 1; }

# Run the Python script with the provided argument
"$VENV_PATH/bin/python3" "$SCRIPT_PATH" "$1" >> "$output_dir/quick_action_log.txt" 2>&1

# Log the script completion
echo "Script finished." >> "$output_dir/quick_action_log.txt"
```

2. Make the shell script executable:

```bash
chmod +x extract_annotations.sh
```

3. Run the shell script with the path to the PDF file as an argument:

```bash
./extract_annotations.sh <path_to_pdf>
```

### Example

```bash
./extract_annotations.sh example.pdf
```

This will execute the Python script and generate the Markdown file with annotations and summaries, logging the process in the specified output directory.

## Script Details

### `extract_annotations(pdf_path)`

Extracts highlights and notes from the specified PDF file.

- `pdf_path`: Path to the PDF file.
- Returns a list of annotations with details such as page number, type (highlight or note), content, and color.

### `summarize_annotations(texts)`

Summarizes the provided texts using OpenAI's GPT-4 model.

- `texts`: List of texts to summarize.
- Returns a list of summaries.

### `format_annotations_to_markdown(annotations, summaries)`

Formats the annotations and summaries into Markdown content.

- `annotations`: List of annotations.
- `summaries`: List of summaries corresponding to the annotations.
- Returns a string containing the Markdown content.

## Example Output

An example of the generated Markdown content:

```markdown
# Annotations

- **Highlight on Page 1 (Summarized) (Color: #92e1fb)**
  - Summary of the highlighted text.

- **Highlight on Page 2 (Color: #ff0000)**
  > Original highlighted text.

- **Note on Page 3 (Color: #00ff00)**
  - Content of the note.
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments

- [PyMuPDF](https://github.com/pymupdf/PyMuPDF)
- [OpenAI](https://www.openai.com)

---

Feel free to modify the script and README file to suit your needs. If you encounter any issues or have suggestions for improvements, please open an issue or submit a pull request.