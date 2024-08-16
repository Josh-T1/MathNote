#!/bin/bash

PROJECT_NAME="MathNote"
CURRENT_DIR="$(pwd)"
FILE_DIR_NAME="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$FILE_DIR_NAME")"
VENV_DIR="$PROJECT_DIR/Venv"
INTERPRETER_PATH="$VENV_DIR/$PROJECT_NAME/bin/python3"

module_path="$PROJECT_NAME.cli"

cd "$PROJECT_DIR"
"$INTERPRETER_PATH" -m "$module_path" "$@"
cd "$CURRENT_DIR"


