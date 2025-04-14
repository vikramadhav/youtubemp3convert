#!/bin/bash

# Directory containing the files to rename
DIR="downloads"

# Make sure the directory exists
if [ ! -d "$DIR" ]; then
    echo "Error: Directory '$DIR' not found!"
    exit 1
fi

# Change to the target directory
cd "$DIR" || exit 1

# Process each file in the directory
for file in *; do
    # Skip if it's not a file
    [ -f "$file" ] || continue
    
    # Get the directory, filename, and extension
    filename=$(basename -- "$file")
    extension="${filename##*.}"
    name="${filename%.*}"
    
    # Sanitize the filename:
    # 1. Convert to lowercase first
    # 2. Remove leading/trailing quotes and spaces
    # 3. Replace special chars (except spaces) with space
    # 4. Remove duplicate spaces
    # 5. Remove leading/trailing spaces
    # 6. Convert to sentence case (first letter capital)
    newname=$(echo "$name" | \
        tr '[:upper:]' '[:lower:]' | \
        sed -E 's/^[ '"'"'""]*//' | \
        sed -E 's/[ '"'"'"]*$//' | \
        sed -E 's/[^[:alnum:] ]/ /g' | \
        sed -E 's/  */ /g' | \
        sed -E 's/^ *//' | \
        sed -E 's/ *$//' | \
        sed -E 's/^./\U&/')
    
    # Add back the extension
    newfile="${newname}.${extension}"
    
    # Rename only if the filename has changed
    if [ "$file" != "$newfile" ]; then
        echo "Renaming: '$file' -> '$newfile'"
        mv "$file" "$newfile"
    fi
done

echo "File renaming complete!"