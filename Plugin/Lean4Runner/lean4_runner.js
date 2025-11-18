/*
  Lean4Runner: 通过 VCP 调用 Lean4/Lake
  - 支持口令式 token 与结构化 command 两种模式
  - 兼容 Windows/Linux/MacOS，优先从环境变量 LEAN_BIN/LAKE_BIN 或 ~/.elan/bin 探测
*/

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');
// 加载根级与插件级 config.env，实现灵活配置（同仓库既有插件的做法）
try {
  const dotenv = require('dotenv');
  // 主配置（VCPToolBox/config.env）
  dotenv.config({ path: path.resolve(__dirname, '../../config.env') });
  // 插件本地配置（VCPToolBox/Plugin/Lean4Runner/config.env）
  dotenv.config({ path: path.join(__dirname, 'config.env') });
} catch (_) {
  // 忽略 dotenv 不存在的情况（在根 package.json 已声明依赖，一般可用）
}

function detectBins() {
  const cfgLean = process.env.LEAN_BIN && process.env.LEAN_BIN.trim();
  const cfgLake = process.env.LAKE_BIN && process.env.LAKE_BIN.trim();
  const home = os.homedir();
  const isWin = process.platform === 'win32';
  const elanDir = isWin ? path.join(process.env.USERPROFILE || home, '.elan', 'bin')
                        : path.join(home, '.elan', 'bin');
  const candidates = [];
  if (cfgLean) candidates.push({ lean: cfgLean });
  if (cfgLake) candidates.push({ lake: cfgLake });
  candidates.push({ lean: isWin ? path.join(elanDir, 'lean.exe') : path.join(elanDir, 'lean') });
  candidates.push({ lake: isWin ? path.join(elanDir, 'lake.exe') : path.join(elanDir, 'lake') });
  return {
    lean: cfgLean || (isWin ? path.join(elanDir, 'lean.exe') : path.join(elanDir, 'lean')),
    lake: cfgLake || (isWin ? path.join(elanDir, 'lake.exe') : path.join(elanDir, 'lake')),
    elanBinDir: elanDir,
    isWin,
  };
}

function ensureWorkdir(workspaceDir) {
  const envWorkdir = (process.env.WORKDIR || '').trim();
  return workspaceDir?.trim() || envWorkdir || process.cwd();
}

function buildTempLeanContent({ kind, expr, imports }) {
  const importList = (imports || process.env.DEFAULT_IMPORTS || 'Mathlib')
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);
  const header = importList.map(mod => `import ${mod}`).join('\n');
  if (kind === 'eval') {
    return `${header}\n\n#eval ${expr}`;
  } else { // check
    return `${header}\n\n#check ${expr}`;
  }
}

function runProc(cmd, args, options = {}) {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, { ...options, shell: false });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (d) => { stdout += d.toString(); });
    child.stderr.on('data', (d) => { stderr += d.toString(); });
    child.on('error', (err) => {
      resolve({ code: -1, stdout, stderr: (stderr + '\n' + err.message).trim() });
    });
    child.on('close', (code) => {
      resolve({ code, stdout, stderr });
    });
  });
}

async function evalOrCheck({ kind, expr, imports, workspaceDir }) {
  const bins = detectBins();
  const cwd = ensureWorkdir(workspaceDir);
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lean4runner-'));
  const tmpFile = path.join(tmpDir, `Tmp_${kind}.lean`);
  fs.writeFileSync(tmpFile, buildTempLeanContent({ kind, expr, imports }), 'utf8');

  // 优先尝试 lake env lean（若 cwd 下是 lake 项目）
  let args;
  let cmd;
  if (fs.existsSync(path.join(cwd, 'lakefile.lean')) || fs.existsSync(path.join(cwd, 'lakefile.toml'))) {
    cmd = bins.lake;
    args = ['env', bins.lean, tmpFile];
  } else {
    cmd = bins.lean;
    args = [tmpFile];
  }
  const { code, stdout, stderr } = await runProc(cmd, args, { cwd, env: { ...process.env, PATH: `${bins.elanBinDir}${path.delimiter}${process.env.PATH}` } });
  // 提取关键信息：Lean 会把 #eval/#check 输出到 stdout
  const combined = [stdout, stderr].filter(Boolean).join('\n').trim();
  const ok = code === 0;
  // 简单清理临时目录
  try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch {}
  return { success: ok, message: ok ? stdout.trim() : combined };
}

async function runFile({ file, workspaceDir }) {
  const bins = detectBins();
  const cwd = ensureWorkdir(workspaceDir);
  const target = path.isAbsolute(file) ? file : path.join(cwd, file);
  const { code, stdout, stderr } = await runProc(bins.lean, ['--run', target], {
    cwd,
    env: { ...process.env, PATH: `${bins.elanBinDir}${path.delimiter}${process.env.PATH}` }
  });
  const ok = code === 0;
  return { success: ok, message: ok ? stdout.trim() : (stdout + '\n' + stderr).trim() };
}

async function lakeCmd({ sub, workspaceDir, targets }) {
  const bins = detectBins();
  const cwd = ensureWorkdir(workspaceDir);
  const args = [sub];
  if (sub === 'build' && targets) {
    const list = targets.split(',').map(s => s.trim()).filter(Boolean);
    args.push(...list);
  }
  const { code, stdout, stderr } = await runProc(bins.lake, args, {
    cwd,
    env: { ...process.env, PATH: `${bins.elanBinDir}${path.delimiter}${process.env.PATH}` }
  });
  const ok = code === 0;
  return { success: ok, message: (stdout + (stderr ? '\n' + stderr : '')).trim() };
}

function parseToken(token) {
  // 简单口令格式：以分号分隔的键值对或以空格分隔的子命令
  // 示例：
  //   eval: (Nat.succ 1); imports=Mathlib; dir=D:/MATH Studio/math_studio
  //   check: (Nat.succ 1); imports=Mathlib
  //   run: file=Main.lean; dir=D:/MATH Studio/math_studio
  //   lake: build targets=math_studio; dir=D:/MATH Studio/math_studio
  const s = token.trim();
  const lower = s.toLowerCase();
  if (lower.startsWith('eval:')) {
    const expr = s.slice(s.indexOf(':') + 1).trim();
    const params = kvBlock(expr);
    return { command: 'EvalExpr', params };
  }
  if (lower.startsWith('check:')) {
    const body = s.slice(s.indexOf(':') + 1).trim();
    const params = kvBlock(body);
    return { command: 'Typecheck', params };
  }
  if (lower.startsWith('run:')) {
    const body = s.slice(s.indexOf(':') + 1).trim();
    const params = kvBlock(body);
    return { command: 'RunFile', params };
  }
  if (lower.startsWith('lake:')) {
    const rest = s.slice(s.indexOf(':') + 1).trim();
    const first = rest.split(/\s+/)[0];
    const kvs = kvBlock(rest.slice(first.length).trim());
    if (first === 'build') return { command: 'LakeBuild', params: { targets: kvs.targets, workspaceDir: kvs.dir || kvs.workspaceDir } };
    if (first === 'update') return { command: 'LakeUpdate', params: { workspaceDir: kvs.dir || kvs.workspaceDir } };
  }
  // 默认当作 eval 纯表达式
  return { command: 'EvalExpr', params: { expr: s } };
}

function kvBlock(text) {
  // 解析形如：expr=...(或起始裸表达式); imports=Mathlib; dir=...
  const res = {};
  const parts = text.split(';').map(x => x.trim()).filter(Boolean);
  if (parts.length === 0) return res;
  // 如果第一段不是 k=v，认为它就是 expr
  if (!parts[0].includes('=')) {
    res.expr = parts[0];
    parts.shift();
  }
  for (const p of parts) {
    const eq = p.indexOf('=');
    if (eq > 0) {
      const k = p.slice(0, eq).trim();
      const v = p.slice(eq + 1).trim();
      res[k] = v;
    }
  }
  return res;
}

async function dispatch(req) {
  const cmd = (req.command || '').trim();
  if (cmd === 'EvalExpr') {
    if (!req.expr) return { success: false, message: '缺少参数: expr' };
    return evalOrCheck({ kind: 'eval', expr: req.expr, imports: req.imports, workspaceDir: req.workspaceDir });
  }
  if (cmd === 'Typecheck') {
    if (!req.expr) return { success: false, message: '缺少参数: expr' };
    return evalOrCheck({ kind: 'check', expr: req.expr, imports: req.imports, workspaceDir: req.workspaceDir });
  }
  if (cmd === 'RunFile') {
    if (!req.file) return { success: false, message: '缺少参数: file' };
    return runFile({ file: req.file, workspaceDir: req.workspaceDir });
  }
  if (cmd === 'LakeBuild') {
    if (!req.workspaceDir) return { success: false, message: '缺少参数: workspaceDir' };
    return lakeCmd({ sub: 'build', workspaceDir: req.workspaceDir, targets: req.targets });
  }
  if (cmd === 'LakeUpdate') {
    if (!req.workspaceDir) return { success: false, message: '缺少参数: workspaceDir' };
    return lakeCmd({ sub: 'update', workspaceDir: req.workspaceDir });
  }
  if (cmd === 'Token') {
    if (!req.token) return { success: false, message: '缺少参数: token' };
    const parsed = parseToken(req.token);
    return dispatch({ ...parsed.params, command: parsed.command });
  }
  return { success: false, message: `未知命令: ${cmd}` };
}

async function main() {
  try {
    const input = fs.readFileSync(0, 'utf-8').trim();
    if (!input) {
      console.log(JSON.stringify({ status: 'error', error: '未收到任何输入' }));
      process.exit(1);
    }
    let req;
    try {
      req = JSON.parse(input);
    } catch (e) {
      console.log(JSON.stringify({ status: 'error', error: '输入 JSON 解析失败' }));
      process.exit(1);
    }
    const result = await dispatch(req);
    const payload = result.success
      ? { status: 'success', result: result.message }
      : { status: 'error', error: result.message || '未知错误' };
    console.log(JSON.stringify(payload));
    process.exit(result.success ? 0 : 1);
  } catch (e) {
    console.log(JSON.stringify({ status: 'error', error: `插件执行异常: ${e.message}` }));
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { parseToken, detectBins };
