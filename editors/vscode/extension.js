const vscode = require('vscode');
const cp = require('child_process');
const lc = require('vscode-languageclient/node');

let client;
function activate(context) {
  const serverOptions = () => cp.spawn('agilang', ['lsp']);
  const clientOptions = { documentSelector: [{ scheme: 'file', language: 'agilang' }] };
  client = new lc.LanguageClient('agilang', 'AGILANG Language Server', serverOptions, clientOptions);
  context.subscriptions.push(client.start());
}
function deactivate() {
  if (!client) return undefined;
  return client.stop();
}
module.exports = { activate, deactivate };
