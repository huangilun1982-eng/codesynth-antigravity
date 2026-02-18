import * as vscode from 'vscode';
import { spawn, execFile, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import axios from 'axios';
import { SERVER_URL } from '../config';

export class ServerManager {
    private static _serverProcess: ChildProcess | null = null;
    private static _serverUrl = SERVER_URL;
    private static _outputChannel: vscode.OutputChannel | null = null;

    public static async start(context: vscode.ExtensionContext) {
        if (this._serverProcess) {
            // Check if it's actually responding
            const alive = await this.checkHealth();
            if (alive) { return; }
            // If process exists but not healthy, might be stuck or zombie. Kill it.
            this.stop();
        }

        if (!this._outputChannel) {
            this._outputChannel = vscode.window.createOutputChannel('CodeSynth Server');
        }
        this._outputChannel.show(true);
        this._outputChannel.appendLine('[CodeSynth] Initialization...');

        // Use the python_server bundled with the extension
        const scriptPath = context.asAbsolutePath(path.join('python_server', 'main.py'));

        // Ensure we have a valid path
        if (!scriptPath) {
            vscode.window.showErrorMessage("CodeSynth: Critical Error - Could not locate bundled python server.");
            return;
        }

        this._outputChannel.appendLine(`[CodeSynth] Starting Python Server: ${scriptPath}`);
        const cwd = path.dirname(scriptPath);
        this._outputChannel.appendLine(`[CodeSynth] CWD: ${cwd}`);

        if (!fs.existsSync(scriptPath)) {
            const msg = `[CodeSynth] Critical Error: Server script not found at ${scriptPath}`;
            this._outputChannel.appendLine(msg);
            vscode.window.showErrorMessage(msg);
            return;
        }

        if (!fs.existsSync(cwd)) {
            const msg = `[CodeSynth] Critical Error: Working directory not found at ${cwd}`;
            this._outputChannel.appendLine(msg);
            vscode.window.showErrorMessage(msg);
            return;
        }

        // Debug: Check Environment
        this._outputChannel.appendLine(`[CodeSynth] ComSpec: ${process.env.ComSpec}`);
        this._outputChannel.appendLine(`[CodeSynth] PATH length: ${process.env.PATH?.length}`);

        try {
            // Resolve python path dynamically
            const pythonCmd = await this.resolvePythonPath();
            this._outputChannel.appendLine(`[CodeSynth] Using Python Interpreter: ${pythonCmd}`);

            // Reverting shell: true because it caused cmd.exe ENOENT on some systems
            // Verify file exists
            if (path.isAbsolute(pythonCmd)) {
                if (!fs.existsSync(pythonCmd)) {
                    this._outputChannel.appendLine(`[CodeSynth] Critical Error: Python not found at ${pythonCmd}`);
                } else {
                    this._outputChannel.appendLine(`[CodeSynth] File check: OK`);
                }
            }

            // Fallback to execFile if spawn fails for absolute path on Windows
            // spawn sometimes has issues with .exe extension in quirks mode without shell
            const useExecFile = path.isAbsolute(pythonCmd) && pythonCmd.endsWith('.exe');

            if (useExecFile) {
                this._outputChannel.appendLine(`[CodeSynth] Spawning using execFile...`);
                this._serverProcess = execFile(pythonCmd, ['-u', scriptPath], {
                    cwd: path.dirname(scriptPath),
                    env: process.env
                });
            } else {
                this._serverProcess = spawn(pythonCmd, ['-u', scriptPath], {
                    cwd: path.dirname(scriptPath),
                    env: process.env
                });
            }

            this._serverProcess.on('error', (err) => {
                const msg = `[Spawn Error] Failed to start process: ${err.message}`;
                console.error(msg);
                this._outputChannel?.appendLine(msg);
                this._outputChannel?.appendLine(`[Tip] If 'python' is not found, please ensure Python is installed and added to your system PATH.`);
            });

            this._serverProcess.stdout?.on('data', (data) => {
                const msg = data.toString();
                // console.log(`[Server] ${msg}`); // Reduce noise in DevTools console
                this._outputChannel?.append(msg);
            });

            this._serverProcess.stderr?.on('data', (data) => {
                const msg = data.toString();
                console.error(`[Server Error] ${msg}`);
                this._outputChannel?.append(`[Error] ${msg}`);
            });

            this._serverProcess.on('close', (code) => {
                const msg = `[Server] Process exited with code ${code}`;
                console.log(msg);
                this._outputChannel?.appendLine(msg);
                this._serverProcess = null;
            });

            this._outputChannel.appendLine('[CodeSynth] Waiting for server to be ready...');
            const ready = await this.waitForServer(10000); // Wait up to 10s
            if (ready) {
                this._outputChannel.appendLine('[CodeSynth] Server is READY!');
                vscode.window.setStatusBarMessage('CodeSynth Server: Online', 3000);
            } else {
                this._outputChannel.appendLine('[CodeSynth] Server failed to pass health check.');
                if (this._serverProcess === null) {
                    vscode.window.showErrorMessage('CodeSynth Server 啟動失敗：進程已退出。請檢查 Output 面板中的錯誤日誌 (ImportError/SyntaxError 等)。');
                } else {
                    vscode.window.showErrorMessage('CodeSynth Server 啟動超時。請查看 Output 面板。');
                }
            }

        } catch (e: any) {
            console.error(`[CodeSynth] Failed to start server: ${e}`);
            this._outputChannel.appendLine(`[CodeSynth] Exception during spawn: ${e.message}`);
            vscode.window.showErrorMessage(`CodeSynth Server Start Failed: ${e}`);
        }
    }

    private static async waitForServer(timeoutMs: number): Promise<boolean> {
        const start = Date.now();
        while (Date.now() - start < timeoutMs) {
            // Check if process is still alive locally
            if (!this._serverProcess) {
                return false; // Process died
            }

            if (await this.checkHealth()) {
                return true;
            }
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        return false;
    }

    public static stop() {
        if (this._serverProcess) {
            try {
                // If the process has already exited, exitCode will be set.
                // Don't try to kill it again to avoid 'process not found' errors.
                if (this._serverProcess.exitCode === null && !this._serverProcess.killed) {
                    this._serverProcess.kill();
                }
            } catch (e) {
                // Ignore errors during kill (process might be gone)
                // console.warn("Failed to kill server process:", e);
            }
            this._serverProcess = null;
        }
    }

    public static async checkHealth(): Promise<boolean> {
        try {
            const res = await axios.get(`${this._serverUrl}/api/health_check`, { timeout: 2000 });
            return res.status === 200 && res.data.status === 'healthy';
        } catch (e) {
            return false;
        }
    }
    private static async resolvePythonPath(): Promise<string> {
        // 優先使用 VS Code Python 擴充的設定
        const pythonConfig = vscode.workspace.getConfiguration('python');
        const configuredPath = pythonConfig.get<string>('defaultInterpreterPath');

        const candidates: string[] = [];
        if (configuredPath && configuredPath !== 'python') {
            candidates.push(configuredPath);
        }
        candidates.push('py', 'python', 'python3');

        for (const cmd of candidates) {
            try {
                await new Promise<void>((resolve, reject) => {
                    const check = spawn(cmd, ['--version'], { env: process.env });
                    check.on('error', reject);
                    check.on('close', (code) => {
                        if (code === 0) {
                            resolve();
                        } else {
                            reject(new Error('Exit code ' + code));
                        }
                    });
                });
                return cmd;
            } catch (e) {
                // 此候選不可用，嘗試下一個
            }
        }
        return 'python'; // Fallback
    }

}
