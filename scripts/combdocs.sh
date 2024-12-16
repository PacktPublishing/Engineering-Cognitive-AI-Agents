#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

combine_md ./docs '*.md' combined_docs.md
echo "Combined docs files: combined_docs.md"
