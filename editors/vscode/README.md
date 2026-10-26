# VS Code language support

This folder contains a local extension for `.myr` and legacy `.mux` file association, TextMate syntax highlighting, block indentation, bracket matching, snippets, and semantic editor features backed by MUSHYRA's built-in language server. The server provides diagnostics, completion, document-local go-to-definition, references and conservative rename, document and open-workspace symbols, and basic hover information. Rename is disabled for a name if the server sees declarations in multiple scopes or a collision, since the current index does not yet resolve every shadowed binding.

Install MUSHYRA so `myr --lsp` is available on `PATH`, then open this folder in VS Code and press **F5** to launch an Extension Development Host. Open a `.myr` or `.mux` file to start the server. Set `myr.serverPath` and `myr.serverArgs` in VS Code settings if the executable is installed elsewhere. Programs run with `myr file.myr` in the terminal.
