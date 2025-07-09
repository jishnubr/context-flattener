# --- START OF FILE code (2) - Copy.txt (Refined for Java Naming) ---

import os
import re
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import sys

def detect_language_and_extension(code_block, lang_hint=None):
    """
    Detects the programming language and returns its common file extension.
    Prioritizes language hint, then uses content-based heuristics.
    """
    # Use a mapping from common language names/aliases to file extensions
    ext_map = {
        'python': 'py', 'py': 'py',
        'java': 'java',
        'html': 'html',
        'css': 'css',
        'js': 'js', 'javascript': 'js',
        'sql': 'sql',
        'csharp': 'cs', 'cs': 'cs',
        'c++': 'cpp', 'cpp': 'cpp',
        'text': 'txt', 'txt': 'txt',
        # Config files & other common types
        'yaml': 'yml', 'yml': 'yml',
        'json': 'json',
        'xml': 'xml',
        'properties': 'properties', # Java Properties
        'ini': 'ini',
        'conf': 'conf', 'cfg': 'cfg',
        'toml': 'toml',
        'sh': 'sh', 'bash': 'sh',
        'powershell': 'ps1', 'ps1': 'ps1',
        'dockerfile': 'Dockerfile', 'Dockerfile': 'Dockerfile', # Note: ext becomes "Dockerfile"
        'makefile': 'Makefile', 'Makefile': 'Makefile', # Note: ext becomes "Makefile"
        'md': 'md', 'markdown': 'md',
        'csv': 'csv',
        'env': 'env', # .env files
        'gradle': 'gradle', # Groovy-based build scripts
        'kt': 'kt', 'kotlin': 'kt'
    }

    if lang_hint:
        lang_hint = lang_hint.strip().lower()
        # For Dockerfile/Makefile, the hint might be lowercase but the desired extension has capitals
        if lang_hint == 'dockerfile': return 'Dockerfile'
        if lang_hint == 'makefile': return 'Makefile'
        # For Java, return 'java' if hint is related to Java
        if 'java' in lang_hint or 'gradle' in lang_hint: # Consider gradle hint as potentially Java-related for detection purposes
             return 'java'
        return ext_map.get(lang_hint, 'txt') # Default to 'txt' if hint is unknown

    # Content-based heuristics - Order matters!
    # Check for Java keywords/structures
    if 'public class' in code_block or 'public interface' in code_block or 'public enum' in code_block or 'public record' in code_block or 'public @interface' in code_block:
         return 'java'
    # More basic Java check if not public
    if ' class ' in code_block or ' interface ' in code_block or ' enum ' in code_block or ' record ' in code_block:
         # Add checks to avoid misclassifying other languages that might use these words
         if not any(kw in code_block for kw in ['def ', 'function ', '#include']):
              return 'java'


    if code_block.strip().startswith('using ') and 'namespace' in code_block and (';' in code_block or '{' in code_block): return 'cs'
    if 'def ' in code_block or 'import ' in code_block: return 'py'
    if code_block.strip().lower().startswith('<!doctype html') or ('<html' in code_block.lower() and '</html' in code_block.lower()): return 'html'
    if '<style>' in code_block.lower() or ('{' in code_block and '}' in code_block and (':' in code_block or ';' in code_block) and not any(kw in code_block for kw in ['<html', 'public class', 'def ', 'function'])): # Basic CSS check
        # More refined CSS: look for common properties or selectors if it's not clearly something else
        if re.search(r'(\w+(-\w+)*\s*:\s*\w+)|(\.\w+\s*\{)|(#\w+\s*\{)', code_block.lower()):
            return 'css'
    if 'function ' in code_block or 'console.log' in code_block or 'var ' in code_block or 'let ' in code_block or 'const ' in code_block: return 'js'
    if 'SELECT ' in code_block.upper() or 'INSERT INTO' in code_block.upper() or 'UPDATE ' in code_block.upper() or 'DELETE FROM' in code_block.upper(): return 'sql'
    if '#include' in code_block or 'int main(' in code_block: return 'cpp'

    # XML detection (before general C-like syntax)
    # Check for <?xml ...?> or a root tag structure, and avoid matching HTML again
    if code_block.strip().lower().startswith('<?xml') or \
       (code_block.strip().startswith('<') and '</' in code_block and '>' in code_block and not code_block.strip().lower().startswith('<!doctype html')):
        return 'xml'

    # JSON detection (more specific than generic C-like)
    # Checks for {..} or [..] and presence of ":" and quotes typical of JSON
    if (code_block.strip().startswith('{') and code_block.strip().endswith('}')) or \
       (code_block.strip().startswith('[') and code_block.strip().endswith(']')):
        # Regex for "key": value pattern (value can be string, number, bool, null, object, array)
        if re.search(r'"\s*:\s*(?:"(?:\\.|[^"\\])*"|true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|{|\[)', code_block):
            return 'json'

    # Generic C-like language fallback (less specific)
    if '{' in code_block and '}' in code_block and ';' in code_block:
        return 'txt' # Default to 'txt' to avoid misclassifying as JS or other specific C-like languages

    return 'txt' # Default fallback

def extract_java_class_name(code_block):
    """
    Extracts the name of the public top-level type (class, interface, enum, record, annotation)
    or the first top-level type if no public one exists, from a Java code block.
    This name is typically used for the file name.
    """
    # Patterns to find top-level type declarations:
    # Look for 'public' types first as they dictate the file name
    public_type_pattern = r'public\s+(class|interface|enum|@?interface|record)\s+(\w+)'
    # Fallback pattern for non-public types (only checked if no public type found)
    any_type_pattern = r'(class|interface|enum|@?interface|record)\s+(\w+)'

    # Search for public types first
    public_match = re.search(public_type_pattern, code_block)
    if public_match:
        # Return the captured name (group 2)
        return public_match.group(2)

    # If no public type is found, search for any top-level type as a fallback heuristic
    any_type_match = re.search(any_type_pattern, code_block)
    if any_type_match:
        # Return the captured name (group 2) of the first type found
        return any_type_match.group(2)

    # If no type declaration is found, return None
    return None

def get_initial_dialog_dir():
    android_downloads = Path("/storage/emulated/0/Download")
    user_home_downloads = Path.home() / "Downloads"
    if sys.platform == "android" and android_downloads.is_dir():
        return str(android_downloads)
    elif user_home_downloads.is_dir():
        return str(user_home_downloads)
    else:
        return str(Path.home())

def extract_code_blocks(filepath, base_output_dir_path_str):
    if not filepath:
        print("No input file selected. Operation cancelled.")
        return
    if not base_output_dir_path_str:
        print("No base output directory selected. Operation cancelled.")
        return

    input_file_path = Path(filepath)
    base_output_dir = Path(base_output_dir_path_str)

    # Create a sub-directory named after the input file (without extension)
    output_subdir_name = f"{input_file_path.stem}_extracted_code"
    final_output_dir = base_output_dir / output_subdir_name

    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ Error: Input file not found at '{input_file_path}'")
        return
    except Exception as e:
        print(f"❌ Error reading input file '{input_file_path}': {e}")
        return

    # Regex to find code blocks: ```[optional_language_hint]\ncode\n```
    # re.DOTALL allows '.' to match newlines, capturing multiline code blocks.
    # The first group captures the language hint (optional).
    # The second group captures the code content.
    pattern = r'```(\w+)?\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)

    try:
        # Create the output subdirectory if it doesn't exist
        final_output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Ensured output subdirectory exists: '{final_output_dir}'")
    except OSError as e:
        print(f"❌ Error creating output directory '{final_output_dir}': {e}")
        print("Please ensure the application has write permissions to the base location.")
        return

    count = 1 # Counter for generic filenames
    processed_filenames_in_batch = set() # Tracks all filenames generated in this run to avoid internal clashes

    if not matches:
        print(f"No code blocks found in the input file: '{input_file_path.name}'")
        return

    print(f"\nProcessing '{input_file_path.name}' ({len(matches)} code blocks found)...")

    # Iterate through each found code block
    for lang_hint, code_block_raw in matches:
        code = code_block_raw.strip() # Remove leading/trailing whitespace from the code block
        if not code:
            print(f"Skipping empty code block (match {count}).")
            count += 1 # Increment generic counter even for skipped blocks
            continue

        # Determine the file extension based on language hint or content
        ext = detect_language_and_extension(code, lang_hint)
        generated_file_name_str = None # Variable to hold the final filename

        # --- Filename Generation Logic ---
        # Prioritize specific naming conventions (like Java class names)
        if ext == 'java':
            # Use the enhanced function to find a suitable Java name
            java_name = extract_java_class_name(code)
            if java_name:
                base_name = java_name # Use the extracted type name as the base
                # Start suffix check from empty string to avoid _1 if original doesn't exist
                suffix = ""
                idx = 1
                temp_name = f"{base_name}{suffix}.java"
                # Check for uniqueness: Does the file exist OR have we already generated a file with this exact name in *this* run?
                while (final_output_dir / temp_name).exists() or temp_name in processed_filenames_in_batch:
                    suffix = f"_{idx}" # Add a numerical suffix
                    idx += 1
                    temp_name = f"{base_name}{suffix}.java"
                generated_file_name_str = temp_name # Found a unique name
            else:
                # Fallback for Java if no suitable type name was found in the block
                base_name = f"java_code_{count}" # Use a generic base name with the counter
                suffix = ""
                idx_generic = 1
                temp_name = f"{base_name}{suffix}.java"
                 # Check for uniqueness against existing files and names already generated in this batch
                while (final_output_dir / temp_name).exists() or temp_name in processed_filenames_in_batch:
                    suffix = f"_{idx_generic}"
                    idx_generic += 1
                    temp_name = f"{base_name}{suffix}.java"
                generated_file_name_str = temp_name # Found a unique name

        # Handle Dockerfile and Makefile which are often named without a traditional extension
        elif ext in ["Dockerfile", "Makefile"]:
             base_name_for_file = ext # Use 'Dockerfile' or 'Makefile' as the base name
             current_ext = "" # These files typically don't have an extension part after the name

             idx = 1
             temp_name_for_unique_check = base_name_for_file # Start check with the base name
             # Check for uniqueness against existing files and names already generated in this batch
             while (final_output_dir / temp_name_for_unique_check).exists() or temp_name_for_unique_check in processed_filenames_in_batch:
                 temp_name_for_unique_check = f"{base_name_for_file}_{idx}" # Add a numerical suffix
                 idx += 1
             generated_file_name_str = temp_name_for_unique_check # Found a unique name


        # Generic naming for all other languages/extensions
        else:
            base_name_for_file = f"extracted_code_{count}" # Use a generic base name with the counter
            current_ext = f".{ext}" # Standard extension format

            idx = 1
            temp_name_for_unique_check = f"{base_name_for_file}{current_ext}" # Start check with the base name + extension
            # Check for uniqueness against existing files and names already generated in this batch
            while (final_output_dir / temp_name_for_unique_check).exists() or temp_name_for_unique_check in processed_filenames_in_batch:
                 temp_name_for_unique_check = f"{base_name_for_file}_{idx}{current_ext}" # Add a numerical suffix before the extension
                 idx += 1
            generated_file_name_str = temp_name_for_unique_check # Found a unique name


        # --- End of Filename Generation Logic ---

        # Add the generated filename to the set of processed names for this batch
        if generated_file_name_str:
            processed_filenames_in_batch.add(generated_file_name_str)
            full_path = final_output_dir / generated_file_name_str

            # --- Save the code block to the generated file ---
            try:
                with open(full_path, 'w', encoding='utf-8') as out_file:
                    out_file.write(code)
                # Report success relative to the base output directory for cleaner path display
                relative_output_path = final_output_dir.relative_to(base_output_dir)
                print(f"✅ Saved: {generated_file_name_str} to '{relative_output_path}'")
            except Exception as e:
                print(f"❌ Error saving '{generated_file_name_str}' to '{full_path}': {e}")
        else:
            # This case should ideally not happen if naming logic covers all `ext` values,
            # but as a safeguard.
            print(f"❌ Error: Could not determine a valid filename for code block {count}.")

        count += 1 # Increment the generic counter for the next block


    print("\nProcessing complete.")
    if not matches:
         print("No code blocks found, so no files were created.")


def select_input_file(initial_dir):
    # Use tkinter for the file dialog (GUI)
    root = tk.Tk()
    root.withdraw() # Hide the main Tkinter window
    file_path = filedialog.askopenfilename(
        initialdir=initial_dir,
        title="Select Input Text File with Code Blocks",
        filetypes=(("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")) # Filter file types
    )
    root.destroy() # Destroy the root window after the dialog is closed
    return file_path

def select_output_directory(initial_dir):
    # Use tkinter for the directory dialog (GUI)
    root = tk.Tk()
    root.withdraw() # Hide the main Tkinter window
    dir_path = filedialog.askdirectory(
        initialdir=initial_dir,
        title="Select Base Output Directory (a subdirectory will be created here)"
    )
    root.destroy() # Destroy the root window after the dialog is closed
    return dir_path

if __name__ == "__main__":
    print("Welcome to the Code Block Extractor!")
    # Determine a sensible starting directory for the file dialogs
    common_initial_dir = get_initial_dialog_dir()

    print(f"\nPlease select the text file containing code blocks (e.g., a .txt or .md file).")
    print(f"(Dialog will start in: '{common_initial_dir}')")
    input_file = select_input_file(common_initial_dir) # Call function to open file dialog

    if input_file: # Proceed only if a file was selected (not cancelled)
        input_file_path_obj = Path(input_file)
        print(f"Selected input file: '{input_file_path_obj.name}'")

        print(f"\nPlease select the base directory where extracted code files will be saved.")
        # Explain that a subdirectory will be created for organization
        print(f"A new subdirectory (e.g., '{input_file_path_obj.stem}_extracted_code') will be created inside your chosen location.")
        print(f"(Dialog will start in: '{common_initial_dir}')")

        output_dir_base = select_output_directory(common_initial_dir) # Call function to open directory dialog

        if output_dir_base: # Proceed only if a directory was selected (not cancelled)
            print(f"Selected base output directory: '{output_dir_base}'")
            # Execute the core logic to extract and save the code blocks
            extract_code_blocks(input_file, output_dir_base)
            print("\nProgram execution finished.")
        else:
            print("Base output directory selection cancelled. Exiting.")
    else:
        print("Input file selection cancelled. Exiting.")

# --- END OF FILE code (2) - Copy.txt (Refined for Java Naming) ---