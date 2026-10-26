# PowerShell completion for the Mux CLI. Dot-source this file from your profile.
Register-ArgumentCompleter -Native -CommandName myr, mux -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    $options = @(
        '--version', '--repl', '--check', '--lint', '--format', '--write-format',
        '--watch', '--watch-interval', '--tokens', '--ast', '--max-steps',
        '--max-call-depth', '--sandbox-root', '--sandbox', '--no-sandbox',
        '--max-output-bytes', '--max-allocation-bytes', '--timeout-seconds',
        '--config', '--diagnostics-format', '--time', '--debug', '--debugger',
        '--lsp', '--help'
    )
    if ($wordToComplete.StartsWith('-')) {
        $options | Where-Object { $_.StartsWith($wordToComplete, [StringComparison]::OrdinalIgnoreCase) } |
            ForEach-Object { [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) }
        return
    }
    $directory = Split-Path -Parent $wordToComplete
    if (-not $directory) { $directory = '.' }
    $leaf = Split-Path -Leaf $wordToComplete
    Get-ChildItem -LiteralPath $directory -Name -ErrorAction SilentlyContinue |
        Where-Object { $_.StartsWith($leaf, [StringComparison]::OrdinalIgnoreCase) } |
        ForEach-Object {
            $candidate = if ($directory -eq '.') { $_ } else { Join-Path $directory $_ }
            [System.Management.Automation.CompletionResult]::new($candidate, $candidate, 'File', $candidate)
        }
}
