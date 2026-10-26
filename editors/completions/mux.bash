# Bash completion for the Mux CLI. Source this file from your shell profile.
_mux_complete() {
    local current previous options completion
    current="${COMP_WORDS[COMP_CWORD]}"
    previous="${COMP_WORDS[COMP_CWORD-1]}"
    options="--version --repl --check --lint --format --write-format --watch --watch-interval --tokens --ast --max-steps --max-call-depth --sandbox-root --sandbox --no-sandbox --max-output-bytes --max-allocation-bytes --timeout-seconds --config --diagnostics-format --time --debug --debugger --lsp --help"

    case "$previous" in
        --sandbox-root|--config)
            compopt -o filenames
            COMPREPLY=()
            while IFS= read -r completion; do COMPREPLY+=("$completion"); done < <(compgen -f -- "$current")
            return
            ;;
    esac
    if [[ "$current" == -* ]]; then
        COMPREPLY=( $(compgen -W "$options" -- "$current") )
    else
        compopt -o filenames
        COMPREPLY=()
        while IFS= read -r completion; do COMPREPLY+=("$completion"); done < <(compgen -f -- "$current")
    fi
}
complete -F _mux_complete mux
