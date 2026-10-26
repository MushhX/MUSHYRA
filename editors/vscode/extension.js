const cp = require('child_process');
const vscode = require('vscode');

class MUSHYRAClient {
  constructor(context) {
    this.context = context;
    this.output = vscode.window.createOutputChannel('MUSHYRA Language Server');
    this.diagnostics = vscode.languages.createDiagnosticCollection('myr');
    this.pending = new Map();
    this.nextId = 1;
    this.buffer = Buffer.alloc(0);
    this.process = null;
    this.ready = false;
  }

  start() {
    const config = vscode.workspace.getConfiguration('myr');
    const configuredValue = (settings, key) => {
      const values = settings.inspect(key);
      return values?.workspaceFolderLanguageValue ?? values?.workspaceFolderValue
        ?? values?.workspaceLanguageValue ?? values?.workspaceValue
        ?? values?.globalLanguageValue ?? values?.globalValue;
    };
    const command = configuredValue(config, 'serverPath') ?? 'myr';
    const args = configuredValue(config, 'serverArgs') ?? ['--lsp'];
    const cwd = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    this.buffer = Buffer.alloc(0);
    this.process = cp.spawn(command, args, {
      cwd,
      shell: process.platform === 'win32',
      windowsHide: true,
    });
    this.process.stdout.on('data', chunk => this._receive(chunk));
    this.process.stderr.on('data', chunk => this.output.append(chunk.toString()));
    this.process.on('error', error => this.output.appendLine(`No se pudo iniciar MUSHYRA: ${error.message}`));
    this.process.on('exit', (code, signal) => {
      this.output.appendLine(`Servidor MUSHYRA finalizado (código ${code ?? signal ?? 'desconocido'}).`);
      for (const item of this.pending.values()) item.reject(new Error('Servidor MUSHYRA detenido'));
      this.pending.clear();
      this.process = null;
    });
    const root = vscode.workspace.workspaceFolders?.[0]?.uri.toString();
    this.request('initialize', {
      processId: process.pid,
      rootUri: root || null,
      capabilities: { textDocument: { definition: {}, references: {}, completion: {}, documentSymbol: {} } },
      clientInfo: { name: 'MUSHYRA VS Code extension', version: '2.0.0' },
    }).then(() => {
      this.ready = true;
      this.notify('initialized', {});
      for (const document of vscode.workspace.textDocuments) {
        if (document.languageId === 'myr') this.open(document);
      }
    }).catch(error => this.output.appendLine(`Inicialización LSP fallida: ${error.message}`));
  }

  stop() {
    if (this.process) {
      try { this.notify('exit'); } catch (_) { /* process may already be closing */ }
      this.process.kill();
    }
    this.diagnostics.dispose();
    this.output.dispose();
  }

  dispose() { this.stop(); }

  _send(message) {
    if (!this.process || !this.process.stdin.writable) return;
    const body = Buffer.from(JSON.stringify(message), 'utf8');
    this.process.stdin.write(Buffer.from(`Content-Length: ${body.length}\r\n\r\n`, 'ascii'));
    this.process.stdin.write(body);
  }

  request(method, params) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this._send({ jsonrpc: '2.0', id, method, params });
    });
  }

  notify(method, params = {}) {
    this._send({ jsonrpc: '2.0', method, params });
  }

  _receive(chunk) {
    this.buffer = Buffer.concat([this.buffer, chunk]);
    while (true) {
      const boundary = this.buffer.indexOf('\r\n\r\n');
      if (boundary < 0) return;
      const header = this.buffer.subarray(0, boundary).toString('ascii');
      const match = header.match(/(?:^|\r\n)Content-Length:\s*(\d+)/i);
      if (!match) {
        this.output.appendLine('Respuesta LSP sin Content-Length.');
        this.buffer = Buffer.alloc(0);
        return;
      }
      const length = Number(match[1]);
      const start = boundary + 4;
      if (this.buffer.length < start + length) return;
      const body = this.buffer.subarray(start, start + length).toString('utf8');
      this.buffer = this.buffer.subarray(start + length);
      try { this._handle(JSON.parse(body)); }
      catch (error) { this.output.appendLine(`Respuesta LSP no válida: ${error.message}`); }
    }
  }

  _handle(message) {
    if (message.id !== undefined && this.pending.has(message.id)) {
      const item = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) item.reject(new Error(message.error.message));
      else item.resolve(message.result);
      return;
    }
    if (message.method === 'textDocument/publishDiagnostics') {
      const params = message.params;
      const uri = vscode.Uri.parse(params.uri);
      const items = (params.diagnostics || []).map(item => {
        const severity = item.severity === 1 ? vscode.DiagnosticSeverity.Error
          : item.severity === 3 ? vscode.DiagnosticSeverity.Information
            : vscode.DiagnosticSeverity.Warning;
        const diagnostic = new vscode.Diagnostic(this._range(item.range), item.message, severity);
        diagnostic.code = item.code;
        diagnostic.source = item.source || 'MUSHYRA';
        return diagnostic;
      });
      this.diagnostics.set(uri, items);
    }
  }

  _position(position) { return { line: position.line, character: position.character }; }
  _range(range) {
    return new vscode.Range(
      new vscode.Position(range.start.line, range.start.character),
      new vscode.Position(range.end.line, range.end.character));
  }
  _textDocument(document) { return { uri: document.uri.toString(), version: document.version }; }
  open(document) {
    if (!this.ready) return;
    this.notify('textDocument/didOpen', { textDocument: {
      ...this._textDocument(document), languageId: document.languageId, text: document.getText(),
    } });
  }
  change(document) {
    if (!this.ready) return;
    this.notify('textDocument/didChange', {
      textDocument: this._textDocument(document),
      contentChanges: [{ text: document.getText() }],
    });
  }
  close(document) {
    if (!this.ready) return;
    this.notify('textDocument/didClose', { textDocument: { uri: document.uri.toString() } });
  }
  params(document, position) {
    return { textDocument: { uri: document.uri.toString() }, position: this._position(position) };
  }
}

function activate(context) {
  const client = new MUSHYRAClient(context);
  client.start();
  context.subscriptions.push(client);

  context.subscriptions.push(vscode.workspace.onDidOpenTextDocument(document => {
    if (document.languageId === 'myr') client.open(document);
  }));
  context.subscriptions.push(vscode.workspace.onDidChangeTextDocument(event => {
    if (event.document.languageId === 'myr') client.change(event.document);
  }));
  context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(document => {
    if (document.languageId === 'myr') client.notify('textDocument/didSave', {
      textDocument: { uri: document.uri.toString() }, text: document.getText(),
    });
  }));
  context.subscriptions.push(vscode.workspace.onDidCloseTextDocument(document => {
    if (document.languageId === 'myr') client.close(document);
  }));

  const selector = { language: 'myr' };
  context.subscriptions.push(vscode.languages.registerCompletionItemProvider(selector, {
    async provideCompletionItems(document, position) {
      const result = await client.request('textDocument/completion', client.params(document, position));
      return (result?.items || []).map(item => {
        const completion = new vscode.CompletionItem(item.label,
          item.kind === 14 ? vscode.CompletionItemKind.Keyword : vscode.CompletionItemKind.Variable);
        completion.detail = item.detail;
        return completion;
      });
    },
  }, '.'));
  context.subscriptions.push(vscode.languages.registerDefinitionProvider(selector, {
    async provideDefinition(document, position) {
      const result = await client.request('textDocument/definition', client.params(document, position));
      return result ? new vscode.Location(vscode.Uri.parse(result.uri), client._range(result.range)) : undefined;
    },
  }));
  context.subscriptions.push(vscode.languages.registerReferenceProvider(selector, {
    async provideReferences(document, position, context) {
      const result = await client.request('textDocument/references', {
        ...client.params(document, position), context: { includeDeclaration: context.includeDeclaration },
      });
      return (result || []).map(item => new vscode.Location(
        vscode.Uri.parse(item.uri), client._range(item.range)));
    },
  }));
  context.subscriptions.push(vscode.languages.registerRenameProvider(selector, {
    async provideRenameEdits(document, position, newName) {
      const result = await client.request('textDocument/rename', {
        ...client.params(document, position), newName,
      });
      if (!result) return undefined;
      const edit = new vscode.WorkspaceEdit();
      for (const [uri, changes] of Object.entries(result.changes || {})) {
        for (const change of changes) {
          edit.replace(vscode.Uri.parse(uri), client._range(change.range), change.newText);
        }
      }
      return edit;
    },
  }));
  context.subscriptions.push(vscode.languages.registerDocumentSymbolProvider(selector, {
    async provideDocumentSymbols(document) {
      const result = await client.request('textDocument/documentSymbol', {
        textDocument: { uri: document.uri.toString() },
      });
      return (result || []).map(item => new vscode.DocumentSymbol(
        item.name, '', item.kind === 12 ? vscode.SymbolKind.Function : vscode.SymbolKind.Variable,
        client._range(item.range), client._range(item.selectionRange)));
    },
  }));
  context.subscriptions.push(vscode.languages.registerWorkspaceSymbolProvider({
    async provideWorkspaceSymbols(query) {
      const result = await client.request('workspace/symbol', { query });
      return (result || []).map(item => new vscode.SymbolInformation(
        item.name,
        item.kind === 12 ? vscode.SymbolKind.Function : vscode.SymbolKind.Variable,
        '',
        new vscode.Location(vscode.Uri.parse(item.location.uri), client._range(item.location.range))));
    },
  }));
  context.subscriptions.push(vscode.languages.registerHoverProvider(selector, {
    async provideHover(document, position) {
      const result = await client.request('textDocument/hover', client.params(document, position));
      return result ? new vscode.Hover(result.contents.value, client._range(result.range)) : undefined;
    },
  }));
}

function deactivate() {}

module.exports = { activate, deactivate };
