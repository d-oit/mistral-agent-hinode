# Full Markdown Processor

## Overview
The Full Markdown Processor is a Python script designed to process markdown files from a Git repository. It extracts shortcode examples, generates training data, and writes the outputs to specified files.

## Features
- Clones a Git repository and processes markdown files.
- Extracts shortcode examples from markdown content.
- Generates training examples for user queries and assistant responses.
- Writes outputs to JSONL and text files.

## Setup

### Prerequisites
- Python 3.x
- Git

### Installation
1. Clone the repository:
   ```sh
   git clone https://github.com/your-repo/full-markdown-processor.git
   cd full-markdown-processor
   ```
2. Install the required dependencies:
   ```sh
   pip install -r requirements.txt
   ```

### Configuration
Create a `.env` file in the root directory with the following content:
```
REPO_URL=https://github.com/gethinode/docs.git
REPO_BRANCH=main
OUTPUT_DIR=output
CLONE_DIR=temp_clone_dir
LOG_FILE=processing.log
```

## Usage
Run the script using the following command:
```sh
python full-markdown-processor.py
```

## Output
The script will generate two files in the `OUTPUT_DIR`:
- `training_data.jsonl`: Contains the training examples in JSONL format.
- `content.txt`: Contains the raw content of the markdown files.

## License
This project is licensed under the MIT License.
