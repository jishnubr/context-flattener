import os
import re
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import sys
import subprocess
import zipfile
import shutil # Added for robust directory removal

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
        if lang_hint == 'dockerfile': return 'Dockerfile'
        if lang_hint == 'makefile': return 'Makefile'
        if 'java' in lang_hint or 'gradle' in lang_hint:
             return 'java'
        return ext_map.get(lang_hint, 'txt')

    if 'public class' in code_block or 'public interface' in code_block or 'public enum' in code_block or 'public record' in code_block or 'public @interface' in code_block:
         return 'java'
    if ' class ' in code_block or ' interface ' in code_block or ' enum ' in code_block or ' record ' in code_block:
         if not any(kw in code_block for kw in ['def ', 'function ', '#include']):
              return 'java'

    if re.search(r'\bdef\s+\w+\s*\(', code_block) or 'import ' in code_block: return 'py'

    if code_block.strip().startswith('using ') and 'namespace' in code_block and (';' in code_block or '{' in code_block): return 'cs'
    if code_block.strip().lower().startswith('<!doctype html') or ('<html' in code_block.lower() and '</html' in code_block.lower()): return 'html'

    # Basic CSS check: look for common properties or selectors if it's not clearly something else
    # Regex breakdown:
    # (\w+(-\w+)*\s*:\s*\w+) : matches 'property-name: value' (e.g., font-size: 12px)
    # (\.\w+\s*\{) : matches a class selector (e.g., .my-class {)
    # (#\w+\s*\{) : matches an ID selector (e.g., #my-id {)
    if '<style>' in code_block.lower() or ('{' in code_block and '}' in code_block and (':' in code_block or ';' in code_block) and not any(kw in code_block for kw in ['<html', 'public class', 'def ', 'function'])):
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
    # Regex breakdown for value pattern:
    # (?:"(?:\\.|[^"\\])*"|true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|{|\[)
    # This matches valid JSON values: a string, true/false/null, a number, or an object/array start.
    if (code_block.strip().startswith('{') and code_block.strip().endswith('}')) or \
       (code_block.strip().startswith('[') and code_block.strip().endswith(']')):
        if re.search(r'"\s*:\s*(?:"(?:\\.|[^"\\])*"|true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|{|\[)', code_block):
            return 'json'

    # Generic C-like language fallback (less specific)
    if '{' in code_block and '}' in code_block and ';' in code_block:
        return 'txt'

    return 'txt'

def extract_java_class_name(code_block):
    """
    Extracts the name of the public top-level type (class, interface, enum, record, annotation)
    or the first top-level type if no public one exists, from a Java code block.
    This name is typically used for the file name.
    """
    public_type_pattern = r'public\s+(class|interface|enum|@?interface|record)\s+(\w+)'
    any_type_pattern = r'(class|interface|enum|@?interface|record)\s+(\w+)'

    public_match = re.search(public_type_pattern, code_block)
    if public_match:
        return public_match.group(2)

    any_type_match = re.search(any_type_pattern, code_block)
    if any_type_match:
        return any_type_match.group(2)

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

def open_folder_in_explorer(path: Path):
    """
    Opens the given folder path in the system's default file explorer.
    Handles different operating systems.
    """
    if not path.is_dir():
        print(f"Warning: Directory not found or is not a directory: '{path}'")
        return

    try:
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin": # macOS
            subprocess.run(["open", str(path)], check=True)
        elif sys.platform.startswith("linux"):
            try:
                subprocess.run(["xdg-open", str(path)], check=True)
            except FileNotFoundError:
                subprocess.run(["gio", "open", str(path)], check=True)
        elif sys.platform == "android":
             print(f"\nOn Android, please navigate to the output folder manually:")
             print(f"  {path}")
             print("You might need a file manager app to open this path (e.g., in Termux, check if 'xdg-open' or 'termux-open' is installed and configured).")
             return
        else:
            print(f"Unsupported operating system '{sys.platform}'. Cannot automatically open folder.")
            print(f"Please navigate to the output folder manually: '{path}'")
    except Exception as e:
        print(f"Error attempting to open folder '{path}': {e}")
        print("Please navigate to the output folder manually.")

def extract_code_blocks(filepath, base_output_dir_path_str) -> Path | None:
    """
    Extracts code blocks from the input file, saves them to a temporary subdirectory,
    then compresses them into a ZIP file.
    Returns the path to the created ZIP file on success, or the temporary directory
    if zipping fails, or None on critical failure/cancellation.
    """
    if not filepath:
        print("No input file selected. Operation cancelled.")
        return None
    if not base_output_dir_path_str:
        print("No base output directory selected. Operation cancelled.")
        return None

    input_file_path = Path(filepath)
    base_output_dir = Path(base_output_dir_path_str)

    temp_output_subdir_name = f"{input_file_path.stem}_extracted_code_temp"
    temp_output_dir = base_output_dir / temp_output_subdir_name
    zip_filename = base_output_dir / f"{input_file_path.stem}_extracted_code.zip"

    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ Error: Input file not found at '{input_file_path}'")
        return None
    except Exception as e:
        print(f"❌ Error reading input file '{input_file_path}': {e}")
        return None

    pattern = r'```(\w+)?\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)

    try:
        temp_output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Ensured temporary output subdirectory exists: '{temp_output_dir}'")
    except OSError as e:
        print(f"❌ Error creating temporary output directory '{temp_output_dir}': {e}")
        print("Please ensure the application has write permissions to the base location.")
        return None

    count = 1
    processed_filenames_in_batch = set()
    files_extracted_count = 0

    if not matches:
        print(f"No code blocks found in the input file: '{input_file_path.name}'.")
        print(f"No files will be extracted, and no ZIP file will be created.")
        # Attempt to clean up the newly created empty temporary directory
        try:
            if temp_output_dir.is_dir() and not any(temp_output_dir.iterdir()):
                temp_output_dir.rmdir()
                print(f"Cleaned up empty temporary directory: '{temp_output_dir}'")
        except Exception as e:
            print(f"Warning: Could not remove empty temporary directory '{temp_output_dir}': {e}")
        return None # Indicate no useful output was generated

    print(f"\nProcessing '{input_file_path.name}' ({len(matches)} code blocks found)...")

    for lang_hint, code_block_raw in matches:
        code = code_block_raw.strip()
        if not code:
            print(f"Skipping empty code block (match {count}).")
            count += 1
            continue

        ext = detect_language_and_extension(code, lang_hint)
        generated_file_name_str = None

        if ext == 'java':
            java_name = extract_java_class_name(code)
            if java_name:
                base_name = java_name
                suffix = ""
                idx = 1
                temp_name = f"{base_name}{suffix}.java"
                while (temp_output_dir / temp_name).exists() or temp_name in processed_filenames_in_batch:
                    suffix = f"_{idx}"
                    idx += 1
                    temp_name = f"{base_name}{suffix}.java"
                generated_file_name_str = temp_name
            else:
                base_name = f"java_code_{count}"
                suffix = ""
                idx_generic = 1
                temp_name = f"{base_name}{suffix}.java"
                while (temp_output_dir / temp_name).exists() or temp_name in processed_filenames_in_batch:
                    suffix = f"_{idx_generic}"
                    idx_generic += 1
                    temp_name = f"{base_name}{suffix}.java"
                generated_file_name_str = temp_name

        elif ext in ["Dockerfile", "Makefile"]:
             base_name_for_file = ext
             current_ext = ""

             idx = 1
             temp_name_for_unique_check = base_name_for_file
             while (temp_output_dir / temp_name_for_unique_check).exists() or temp_name_for_unique_check in processed_filenames_in_batch:
                 temp_name_for_unique_check = f"{base_name_for_file}_{idx}"
                 idx += 1
             generated_file_name_str = temp_name_for_unique_check

        else:
            base_name_for_file = f"extracted_code_{count}"
            current_ext = f".{ext}"

            idx = 1
            temp_name_for_unique_check = f"{base_name_for_file}{current_ext}"
            while (temp_output_dir / temp_name_for_unique_check).exists() or temp_name_for_unique_check in processed_filenames_in_batch:
                 temp_name_for_unique_check = f"{base_name_for_file}_{idx}{current_ext}"
                 idx += 1
            generated_file_name_str = temp_name_for_unique_check

        if generated_file_name_str:
            processed_filenames_in_batch.add(generated_file_name_str)
            full_path = temp_output_dir / generated_file_name_str

            try:
                with open(full_path, 'w', encoding='utf-8') as out_file:
                    out_file.write(code)
                relative_output_path = full_path.relative_to(base_output_dir) # Changed to be relative to base_output_dir for clarity
                print(f"✅ Saved: {generated_file_name_str} to '{relative_output_path}'")
                files_extracted_count += 1
            except Exception as e:
                print(f"❌ Error saving '{generated_file_name_str}' to '{full_path}': {e}")
        else:
            print(f"❌ Error: Could not determine a valid filename for code block {count}.")

        count += 1

    print(f"\n--- Extraction Summary ---")
    print(f"Total code blocks found: {len(matches)}")
    print(f"Successfully extracted {files_extracted_count} files to temporary location: '{temp_output_dir}'")

    if files_extracted_count == 0:
        print("\nNo files were successfully extracted. No ZIP archive will be created.")
        # Attempt to clean up the empty temporary directory
        try:
            if temp_output_dir.is_dir():
                shutil.rmtree(temp_output_dir)
                print(f"Cleaned up empty temporary directory: '{temp_output_dir}'")
        except Exception as e:
            print(f"Warning: Could not remove empty temporary directory '{temp_output_dir}': {e}")
        return None

    # --- Zipping Logic ---
    print(f"\n--- Zipping Process ---")
    print(f"Target ZIP file: '{zip_filename}'")
    try:
        # Check if the zip file already exists and remove it to avoid issues with stale content
        if zip_filename.exists():
            print(f"Existing ZIP file found: '{zip_filename}'. Deleting before recreation...")
            zip_filename.unlink()

        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_output_dir):
                for file in files:
                    file_path = Path(root) / file
                    # arcname is the path inside the zip. This makes the zip contain a folder
                    # named like the temp_output_subdir_name (e.g., 'my_file_extracted_code_temp/MyClass.java')
                    arcname = file_path.relative_to(temp_output_dir.parent)
                    print(f"  Adding '{file_path.name}' to ZIP as '{arcname}'")
                    zipf.write(file_path, arcname)
        print(f"✅ Successfully compressed {files_extracted_count} files to: '{zip_filename}'")
        return zip_filename
    except Exception as e:
        print(f"❌ Error compressing files to '{zip_filename}': {e}")
        print(f"The extracted files could not be zipped. They are still available in the temporary directory: '{temp_output_dir}'")
        return temp_output_dir # Return the path to the temporary directory if zipping fails
    finally:
        # Clean up the temporary directory regardless of zipping success or failure,
        # UNLESS the temporary directory itself became the output (if zipping failed).
        # This prevents accidental deletion of files if the return path is the temp dir.
        if temp_output_dir.is_dir() and temp_output_dir != zip_filename: # Ensure we don't try to remove the zip itself
            try:
                print(f"\n--- Cleanup Process ---")
                print(f"Removing temporary directory: '{temp_output_dir}'")
                shutil.rmtree(temp_output_dir)
                print(f"✅ Temporary directory removed.")
            except Exception as e:
                print(f"❌ Warning: Could not remove temporary directory '{temp_output_dir}': {e}")


def select_input_file(initial_dir):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        initialdir=initial_dir,
        title="Select Input Text File with Code Blocks",
        filetypes=(("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*"))
    )
    root.destroy()
    return file_path

def select_output_directory(initial_dir):
    root = tk.Tk()
    root.withdraw()
    dir_path = filedialog.askdirectory(
        initialdir=initial_dir,
        title="Select Base Output Directory (the ZIP file will be created here)"
    )
    root.destroy()
    return dir_path

if __name__ == "__main__":
    print("Welcome to the Code Block Extractor and Compressor!")
    common_initial_dir = get_initial_dialog_dir()

    print(f"\nPlease select the text file containing code blocks (e.g., a .txt or .md file).")
    print(f"(Dialog will start in: '{common_initial_dir}')")
    input_file = select_input_file(common_initial_dir)

    if input_file:
        input_file_path_obj = Path(input_file)
        print(f"Selected input file: '{input_file_path_obj.name}'")

        print(f"\nPlease select the base directory where the compressed ZIP file will be saved.")
        print(f"(A temporary working directory will be created and then removed.)")
        print(f"(Dialog will start in: '{common_initial_dir}')")

        output_dir_base = select_output_directory(common_initial_dir)

        if output_dir_base:
            print(f"Selected base output directory: '{output_dir_base}'")
            final_output_artifact_path = extract_code_blocks(input_file, output_dir_base)

            if final_output_artifact_path:
                print(f"\n--- Program Result ---")
                if final_output_artifact_path.suffix == '.zip':
                    print(f"✅ Successfully created a compressed ZIP archive: '{final_output_artifact_path}'")
                    folder_to_open = final_output_artifact_path.parent
                else: # This means zipping failed, and the temporary directory with extracted files is returned
                    print(f"⚠️ Compression failed. The extracted files are located in the temporary directory: '{final_output_artifact_path}'")
                    folder_to_open = final_output_artifact_path # Open the temp dir, as it contains the files

                print(f"Opening folder: '{folder_to_open}'")
                open_folder_in_explorer(folder_to_open)
            else:
                print("\n⚠️ Code block extraction process was cancelled or no code blocks were found, so no output was generated.")

            print("\nProgram execution finished.")
        else:
            print("Base output directory selection cancelled. Exiting.")
    else:
        print("Input file selection cancelled. Exiting.")