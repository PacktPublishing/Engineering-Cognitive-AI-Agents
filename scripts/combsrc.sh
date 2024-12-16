#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

combine_md ./src '*.py' combined_src.md
combine_md ./tests '*.py' combined_tests.md
combine_md ./config '*.yaml' combined_config.md
combine_md ./examples '*.py' combined_examples.md
cat README.md TODO.md combined_docs.md combined_src.md combined_ui.md combined_tests.md combined_guidelines.md > combined_all.md
echo "Combined source files: combined_all.md"
