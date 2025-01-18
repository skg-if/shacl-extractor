import codecs
import os

def fix_file_encoding(filepath):
    try:
        # Read content in binary mode
        with open(filepath, 'rb') as f:
            content = f.read()
            
        # Try different encodings to decode the content
        encodings = ['utf-8', 'utf-16', 'utf-16le', 'utf-16be', 'ascii', 'iso-8859-1']
        decoded_content = None
        
        for encoding in encodings:
            try:
                # Remove BOM if present
                if content.startswith(codecs.BOM_UTF8):
                    content = content[len(codecs.BOM_UTF8):]
                elif content.startswith(codecs.BOM_UTF16_LE):
                    content = content[len(codecs.BOM_UTF16_LE):]
                elif content.startswith(codecs.BOM_UTF16_BE):
                    content = content[len(codecs.BOM_UTF16_BE):]
                
                decoded_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if decoded_content is None:
            raise UnicodeDecodeError("Could not decode file with any known encoding")
            
        # Write back in UTF-8 without BOM
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(decoded_content)
            
        print(f"✓ Successfully fixed encoding for {filepath}")
    except Exception as e:
        print(f"✗ Error processing {filepath}: {e}")

# Files to check
files_to_check = [
    'README.md',
    'pyproject.toml',
    'src/__init__.py',
    'src/main.py',
    'test_main.py'
]

print("\nStarting encoding fix process...")
for file in files_to_check:
    if os.path.exists(file):
        fix_file_encoding(file)
    else:
        print(f"! File not found: {file}")
print("\nEncoding fix process completed.")