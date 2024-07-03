#!/bin/bash

PROJECT_NAME="VectorGraphics"
FILE_DIR_NAME="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$FILE_DIR_NAME")"
VENV_DIR="$PROJECT_DIR/Venv"
INTERPRETER_PATH="$VENV_DIR/$PROJECT_NAME/bin/python3"

if [[ "$1" == "-g" ]]; then
    module_path="$PROJECT_NAME.main_gui"
else
    module_path="$PROJECT_NAME.main_cli"
fi
shift

cd "$PROJECT_DIR"
"$INTERPRETER_PATH" -m "$module_path" "$@"

