#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

cat README.md TODO.md combined_docs.md combined_src.md > combined_all.md
echo "Combined source files: combined_all.md"
