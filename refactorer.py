import argparse
import os
import datetime
import json
import sys
from src.modules.promptcreator import PromptCreator
from src.modules.responseStrategies import *
from src.modules.responseFactory import ResponseFactory


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "refactor_config.json")

with open(CONFIG_PATH, "r") as f:
    _config_data = json.load(f)

PROMPT_TEMPLATE_PATH = _config_data["PROMPT_TEMPLATE_PATH"]
PATTERNDESCRIPTIONPATH = _config_data["PATTERNDESCRIPTIONPATH"]





class RefactorFrontEnd:
    def __init__(self, code_path, refactored_tests_path, pattern_name,
                 temperature, model_name, max_length, strategy, save_folder_path, language):
        self.code_path = code_path
        self.refactored_tests_path = refactored_tests_path
        self.pattern_name = pattern_name
        self.prompt_file_path = PROMPT_TEMPLATE_PATH
        self.temperature = temperature
        self.model_name = model_name
        self.max_length = max_length
        self.strategy = strategy.lower()
        self.save_folder_path = save_folder_path
        self.full_save_path = ""
        self.refactored_code = ""
        self.prompt = ""
        self.prompt_length = 0
        self.response_length = 0
        self.language = language
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


    def generate_prompt(self, ignore_keys=None):
        print("[INFO] Generating prompt...", file=sys.stderr)
        prompt_creator = PromptCreator(
            prompt_template_path=self.prompt_file_path,
            code_path=self.code_path,
            tests_path=self.refactored_tests_path,
            design_pattern_name=self.pattern_name,
            design_pattern_description_folder=PATTERNDESCRIPTIONPATH,
            ignore_keys=ignore_keys,
            language= self.language
        )
        self.prompt = prompt_creator.generate_prompt()
        self.prompt_length = len(self.prompt.split())
        print(f"[INFO] Prompt length: {self.prompt_length} words", file=sys.stderr)

    def prepare_save_directory(self):
        base_name = os.path.splitext(os.path.basename(self.code_path))[0]
        folder_name = f"{base_name}_{self.pattern_name}_{self.model_name}_{self.timestamp}"
        self.full_save_path = os.path.join(self.save_folder_path, folder_name)
        os.makedirs(os.path.join(self.full_save_path, "refactored"), exist_ok=True)

    def get_response_strategy(self):
        params = {
            "model_name": self.model_name,
             "temperature": self.temperature,
            "max_length": self.max_length
        }
        return ResponseFactory.get_strategy(self.strategy, **params)


    def generate_refactored_code(self):
        print(f"[INFO] Using strategy: {self.strategy}", file=sys.stderr)
        response = self.get_response_strategy()
        print("response", response) 
        self.refactored_code = response.process(self.prompt)
        print("processed", self.refactored_code)
        self.response_length = response.length(self.refactored_code)
        print(f"[INFO] Response length: {self.response_length} words", file=sys.stderr)
        print(f"[INFO] Total token length: {self.prompt_length + self.response_length}", file=sys.stderr)

    def save_outputs(self, ignore_keys=None):
        ignore_keys = set(ignore_keys or [])

        with open(os.path.join(self.full_save_path, "prompt.txt"), "w") as f:
            f.write(self.prompt)

        original_file_name = os.path.basename(self.code_path)
        refactored_file = os.path.join(self.full_save_path, "refactored", original_file_name)
        with open(refactored_file, "w") as f:
            f.write(self.refactored_code)

        with open(os.path.join(self.full_save_path, "refactored", "__init__.py"), 'w') as f:
            pass

        

        metadata = {
            "code_path": self.code_path,
            "refactored_tests_path": self.refactored_tests_path,
            "pattern_name": self.pattern_name,
            "prompt_file_path": self.prompt_file_path,
            "temperature": self.temperature,
            "model_name": self.model_name,
            "max_length": self.max_length,
            "strategy": self.strategy,
            "timestamp": self.timestamp,
            "prompt_length": self.prompt_length,
            "response_length": self.response_length,
            "lines_of_code": len(self.refactored_code.splitlines()),
        }

        '''
        #I don't think this should be required to run the refactorer
        #info.json is in parent of code_path folder
        parent_folder = os.path.dirname(os.path.dirname(self.code_path))
        info_path = os.path.join(parent_folder, "info.json")
        info = {}
        try: 
            if os.path.exists(info_path):
                with open(info_path, "r") as f:
                    info = json.load(f)
        except:
            print(f"[WARNING] Could not read info.json from {info_path}. It may be malformed or missing.", file=sys.stderr)

        if info is not None:
            for key in info:
                metadata[key] = info[key]
        '''
        with open(os.path.join(self.full_save_path, "parameters.json"), "w") as f:
            json.dump(metadata, f, indent=4)

        print(f"[INFO] Files saved to: {self.full_save_path}", file=sys.stderr)

        return refactored_file

    def run(self, ignore_keys=None):
        self.generate_prompt(ignore_keys=ignore_keys)
        self.prepare_save_directory()
        self.generate_refactored_code()
        refactored_file = self.save_outputs(ignore_keys=ignore_keys)
        print(refactored_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate refactoring prompt and process response.")
    parser.add_argument("code_path", help="Path to the original code file")
    parser.add_argument("refactored_tests_path", help="Path to the test file")
    parser.add_argument("pattern_name", help="Design pattern name")
    parser.add_argument("save_folder_path", help="Folder where the output will be saved")
    parser.add_argument("--language", type=str, default="python", help="Programming language of the code")
    parser.add_argument("--temperature", type=float, default=1.0, help="Temperature for LLM")
    parser.add_argument("--model_name", type=str, help="Model name")
    parser.add_argument("--max_length", type=int, default=2048, help="Max token length")
    parser.add_argument("--strategy", type=str, default="openai", choices=["openai", "gemini"],
                        help="Strategy to use for LLM response, options: openai, gemini")
    parser.add_argument("--ignore_keys", type=str, default="",
                        help="Comma-separated keys to ignore in metadata and prompt generation")

    args = parser.parse_args()
    ignore_keys = [key.strip() for key in args.ignore_keys.split(",")] if args.ignore_keys else []

    frontend = RefactorFrontEnd(
        code_path=args.code_path,
        refactored_tests_path=args.refactored_tests_path,
        pattern_name=args.pattern_name,
        temperature=args.temperature,
        model_name=args.model_name,
        max_length=args.max_length,
        strategy=args.strategy,
        save_folder_path=args.save_folder_path,
        language=args.language
    )
    frontend.run(ignore_keys=ignore_keys)


