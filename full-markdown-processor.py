import os
import re
import json
import shutil
import logging
import tempfile
from pathlib import Path
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from git import Repo, GitCommandError
from dotenv import load_dotenv
import frontmatter
import random
import string

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

class Config:
    REPO_URL = os.getenv('REPO_URL', 'https://github.com/gethinode/docs.git')
    REPO_BRANCH = os.getenv('REPO_BRANCH', 'main')
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
    CLONE_DIR = os.getenv('CLONE_DIR', tempfile.mkdtemp())
    LOG_FILE = os.getenv('LOG_FILE', 'processing.log')

@dataclass
class ShortcodeExample:
    name: str
    parameters: Dict[str, str]
    full_text: str

class MarkdownProcessor:
    def __init__(self):
        self.config = Config()
        self.setup_logging()

    def setup_logging(self):
        file_handler = logging.FileHandler(self.config.LOG_FILE)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(file_handler)

    def clone_repository(self) -> str:
        try:
            if Path(self.config.CLONE_DIR).exists():
                try:
                    shutil.rmtree(self.config.CLONE_DIR)
                except PermissionError as e:
                    logging.warning(f"Permission denied when trying to delete {self.config.CLONE_DIR}: {e}")
            logging.info(f"Cloning repository: {self.config.REPO_URL}")
            repo = Repo.clone_from(self.config.REPO_URL, self.config.CLONE_DIR, branch=self.config.REPO_BRANCH)
            return self.config.CLONE_DIR
        except GitCommandError as e:
            logging.error(f"Failed to clone repository: {e}")
            raise

    def get_markdown_files(self, repo_dir: str) -> List[str]:
        markdown_files = []
        for root, _, files in os.walk(repo_dir):
            if '.git' in root:
                continue
            for file in files:
                if file.endswith('.md'):
                    markdown_files.append(os.path.join(root, file))
        return markdown_files

    def extract_shortcode_examples(self, content: str) -> List[ShortcodeExample]:
        shortcode_pattern = r'{{<\s*(.+?)\s*>}}'
        matches = re.findall(shortcode_pattern, content)
        examples = []

        for match in matches:
            parts = match.split()
            if not parts:
                continue

            name = parts[0]
            params = {}
            for part in parts[1:]:
                if '=' in part:
                    key, value = part.split('=', 1)
                    params[key] = value.strip('"\'')

            examples.append(ShortcodeExample(
                name=name,
                parameters=params,
                full_text=match
            ))
        return examples

    def generate_training_example(self, user_query: str, assistant_response: str) -> Dict[str, Any]:
        return {
            "messages": [
                {"role": "user", "content": user_query},
                {"role": "assistant", "content": assistant_response}
            ]
        }

    @staticmethod
    def generate_random_id(length=9):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def generate_tool_example(self, shortcode: ShortcodeExample) -> Dict[str, Any]:
        tool_call_id = self.generate_random_id()
        tool_call = {
            "id": tool_call_id,
            "name": "use_hinode_shortcode",
            "parameters": {
                "shortcode_name": shortcode.name,
                "parameters": shortcode.parameters
            }
        }

        return {
            "messages": [
                {"role": "user", "content": f"Create a {shortcode.name} shortcode with these parameters: {json.dumps(shortcode.parameters)}"},
                {"role": "assistant", "content": json.dumps(tool_call)},
                {"role": "assistant", "content": f"I've created the {shortcode.name} shortcode."}
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "use_hinode_shortcode",
                        "description": "Use the hinode shortcode with the given parameters",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "shortcode_name": {
                                    "type": "string",
                                    "description": "The name of the shortcode"
                                },
                                "parameters": {
                                    "type": "object",
                                    "description": "The parameters for the shortcode",
                                    "additionalProperties": {
                                        "type": "string"
                                    }
                                }
                            },
                            "required": ["shortcode_name", "parameters"]
                        }
                    }
                }
            ]
        }

    def process_markdown_file(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)

            examples = []
            metadata = post.metadata
            shortcodes = self.extract_shortcode_examples(post.content)

            # Basic content example
            if metadata.get('title') and metadata.get('description'):
                examples.append(self.generate_training_example(
                    f"What is {metadata['title']} used for?",
                    metadata['description']
                ))

            # Generate tool examples for each shortcode
            for shortcode in shortcodes:
                examples.append(self.generate_tool_example(shortcode))

            return examples

        except Exception as e:
            logging.error(f"Error processing file {file_path}: {e}")
            return []

    def write_outputs(self, examples: List[Dict[str, Any]], content: List[str]):
        try:
            output_dir = Path(self.config.OUTPUT_DIR)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Write JSONL training data
            with (output_dir / 'training_data.jsonl').open('w', encoding='utf-8') as f:
                for example in examples:
                    f.write(json.dumps(example) + '\n')

            # Write raw content
            with (output_dir / 'content.txt').open('w', encoding='utf-8') as f:
                f.write('\n\n---\n\n'.join(content))

            logging.info(f"Outputs written to {self.config.OUTPUT_DIR}/")

        except Exception as e:
            logging.error(f"Error writing outputs: {e}")
            raise

    def process(self):
        try:
            repo_dir = self.clone_repository()
            markdown_files = self.get_markdown_files(repo_dir)

            all_examples = []
            raw_content = []

            for file_path in markdown_files:
                logging.info(f"Processing {file_path}")
                examples = self.process_markdown_file(file_path)
                all_examples.extend(examples)

                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_content.append(f.read())

            self.write_outputs(all_examples, raw_content)

        except Exception as e:
            logging.error(f"Processing failed: {e}")
            raise
        finally:
            if Path(self.config.CLONE_DIR).exists():
                try:
                    shutil.rmtree(self.config.CLONE_DIR)
                except PermissionError as e:
                    logging.warning(f"Permission denied when trying to delete {self.config.CLONE_DIR}: {e}")

def main():
    processor = MarkdownProcessor()
    processor.process()

if __name__ == "__main__":
    main()
