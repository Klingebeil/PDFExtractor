# PDF Annotation Extractor

PDF Annotation Extractor is a Python script that extracts annotations from a PDF file, summarizes highlighted text using OpenAI's GPT-4 model, and formats the extracted annotations into a Markdown file.

## Features

- Extracts highlights and notes from PDF files.
- Summarizes highlighted text using OpenAI's GPT-4 model.
- Outputs the annotations and summaries in a Markdown file into the directory of the PDF.

## Requirements

- `Python 3.6` or higher
- `fitz` (PyMuPDF)
- `openai`

## Installation
1. Clone this repository or download the script file.
2. Setup a python environment in the file directory
3. Install the required Python packages:

```
pip install pymupdf
```

```
pip install pymupdf
```

## Usage Python Script

1. Set your OpenAI API key in the script:

```python
openai.api_key = 'your_openai_api_key'
```

2. The color of the highlights that should be send for OpenAI for automatic summaries. If unsure which color to choose I recommend running the script once without setting the color first. The output will include the color of each highlight, making it easy to identify the hex code.

```python
colorforsummaries = "#00000"
```

3. Run the script with the path to the PDF file as an argument:

```
python extract_annotations.py <path_to_pdf>
```

## OpenAI summaries

The script will send highlights that are in a certain color to OpenAI with the following prompt:

```
Summarize the following text in bullet points:
```

### Example

```
python extract_annotations.py example.pdf
```

This will generate a Markdown file named `example_annotations.md` with the extracted annotations and summaries.

## Using the Shell Script for Apple Automator

A shell script (`extract_annotations.sh`) is also provided to automate the environment setup and script execution. It can be run in the automator by setting up a new file that 1. takes the provded files and 2. runs the following shell script:

```
for f in "$@"
do
  /Users/johannesklingebieljohannesklingebiel/Library/Scripts/PDFExtractor/run_python_script.sh "$f"
done
```

Make sure to use the correct shell and to use the input as arguments in the configuration of the Automator shell script.

### Shell Script Details

The `extract_annotations.sh` script does the following:

1. Creates an output directory if it doesn't exist.*
2. Logs the start of the script and the current working directory for debugging.*
3. Activates a virtual environment.
4. Runs the Python script with the provided PDF file path as an argument.
5. Logs the script completion.*

\* these steps can be deleted without impairing the function and are only provided for easier debugging.

### Usage

1. Edit the `extract_annotations.sh` file to update the paths to your virtual environment (bash/zsh) and Python script paths:

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

2. Make the shell script executable via the terminal:

```
chmod +x extract_annotations.sh
```

3. Run the shell script with the path to the PDF file as an argument:

```
extract_annotations.sh <path_to_pdf>
```

### Example

```
extract_annotations.sh example.pdf
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

MIT License

Copyright (c) [2024] [Johannes Klingebiel]

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