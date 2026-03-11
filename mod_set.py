import argparse
import zipfile
import tempfile
import os
import shutil
from mse_generate import read_names_from_file, gen_text

def get_card_text(input_text):
    card_names = read_names_from_file(input_text)
    return gen_text(card_names)

def run_update_set(input_text, set_path, output_path):
    card_text = get_card_text(input_text)
    modify_set(set_path, card_text, output_path)

def modify_set(set_path, card_text, output_path):
    """
    Modify the MSE set file by adding card_text before 'version_control:' section.
    The .mse-set file is a zip archive containing a 'set' file.
    """
    # Read the existing zip file
    with zipfile.ZipFile(set_path, 'r') as zip_read:
        # Read the existing 'set' file content
        if 'set' not in zip_read.namelist():
            raise ValueError(f"'set' file not found in {set_path}")
        
        existing_content = zip_read.read('set').decode('utf-8')
        
        # Get all other files in the zip
        other_files = {name: zip_read.read(name) for name in zip_read.namelist() if name != 'set'}
    
    # Find where to insert the card text (before 'version_control:')
    if 'version_control:' not in existing_content:
        raise ValueError("'version_control:' section not found in set file")
    
    # Split the content at version_control
    parts = existing_content.split('version_control:', 1)
    
    # Insert card_text before version_control with proper newline
    # Ensure there's a newline before the card text if needed
    prefix = parts[0].rstrip() + '\n'
    # Add the card text
    new_content = prefix + card_text + '\nversion_control:' + parts[1]
    
    # Create a temporary file in the same directory as the output file
    # This avoids cross-drive move issues on Windows
    output_dir = os.path.dirname(os.path.abspath(output_path)) or '.'
    temp_fd, tmp_path = tempfile.mkstemp(suffix='.mse-set', dir=output_dir)
    os.close(temp_fd)  # Close the file descriptor, we'll use ZipFile to write
    
    try:
        # Write the modified content to a new zip file
        with zipfile.ZipFile(tmp_path, 'w', compression=zipfile.ZIP_DEFLATED) as zip_write:
            # Write the modified 'set' file
            zip_write.writestr('set', new_content.encode('utf-8'))
            
            # Write all other files from the original zip
            for name, content in other_files.items():
                zip_write.writestr(name, content)
        
        # Move the temporary file to the output location
        # Use shutil.move for cross-drive compatibility
        shutil.move(tmp_path, output_path)
        print(f"Successfully added cards to {output_path}")
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise e

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process card names and modify MSE set file')
    parser.add_argument('input_text', help='Path to the input text file containing card names')
    parser.add_argument('set_path', help='Path to the MSE set file')
    parser.add_argument('-o', '--output', default='output.mse-set', 
                       help='Path to the output MSE set file (default: output.mse-set)')
    
    args = parser.parse_args()
    print(f"Input text file: {args.input_text}")
    print(f"Set file path: {args.set_path}")
    print(f"Output file: {args.output}")
    run_update_set(args.input_text, args.set_path, args.output)

    
