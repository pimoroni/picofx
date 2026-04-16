QA_SCRIPT_PATH=${BASH_SOURCE-$0}
QA_SCRIPT_PATH=$(dirname "$QA_SCRIPT_PATH")
QA_SCRIPT_PATH=$(realpath "$QA_SCRIPT_PATH")

function qa_prepare_all {
    pip install ruff
}

function qa_check {
    ruff check --config "$QA_SCRIPT_PATH/ruff.toml" "$1"
}

function qa_fix {
    ruff check --config "$QA_SCRIPT_PATH/ruff.toml" --fix "$1"
}

function qa_examples_check {
    qa_check examples/
}

function qa_examples_fix {
    qa_fix examples/
}

function qa_libs_check {
    qa_check boards/*/frozen_libs
    qa_check boards/*/visible_libs
}

function qa_libs_fix {
    qa_fix boards/*/frozen_libs
    qa_fix boards/*/visible_libs
}

function qa_picofx_check {
    qa_check picofx/
}

function qa_picofx_fix {
    qa_fix picofx/
}
