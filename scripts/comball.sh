#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Enable better error tracing
set -o pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMBSRC_SCRIPT="${SCRIPT_DIR}/combsrc.sh"
COMBDOCS_SCRIPT="${SCRIPT_DIR}/combdocs.sh"
OUTPUT_FILE="combined_all.md"
REQUIRED_FILES=("README.md" "TODO.md" "combined_docs.md" "combined_src.md")

# Function to check if a file exists
check_file_exists() {
  if [[ ! -f "$1" ]]; then
    echo "Error: Required file '$1' does not exist." >&2
    return 1
  fi
}

# Function to run a script
run_script() {
  local script="$1"
  if [[ ! -f "${script}" ]]; then
    echo "Error: Required script '${script}' does not exist." >&2
    exit 1
  fi
  if [[ ! -x "${script}" ]]; then
    echo "Error: Script '${script}' is not executable." >&2
    exit 1
  fi
  echo "Running ${script}..."
  "${script}" || { echo "Error: Failed to run ${script}"; exit 1; }
}

# Run the combsrc.sh script to generate combined_src.md
run_script "${COMBSRC_SCRIPT}"

# Run the combdocs.sh script to generate combined_docs.md
run_script "${COMBDOCS_SCRIPT}"

# Check if all required files exist before combining
for file in "${REQUIRED_FILES[@]}"; do
  check_file_exists "$file" || exit 1
done

# Combine all files
echo "Combining files into ${OUTPUT_FILE}..."
cat "${REQUIRED_FILES[@]}" > "${OUTPUT_FILE}"

echo "Successfully created: ${OUTPUT_FILE}"
