// 游戏跨平台运行适配管理系统
// 软著源代码节选

import { createHash } from "node:crypto";
import { execFile, spawn } from "node:child_process";
import * as fs from "node:fs";
import { promises as fsp } from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

type PlatformType = "windows" | "linux" | "macos" | "ios" | "android";
type ToolchainType = "msvc" | "gcc" | "clang" | "xcode" | "android_ndk";

interface PlatformTarget {
  platform: PlatformType;
  toolchain: ToolchainType;
  toolchainVersion: string;
  arch: string;
  defines: Record<string, string>;
  extraFlags: string[];
  outputName: string;
  assetDir: string;
}

interface RuntimeEnv {
  platform: PlatformType;
  platformVersion: string;
  arch: string;
  cpuCores: number;
  totalMemory: number;
  freeMemory: number;
  hostname: string;
  permissions: string[];
}

interface BuildResult {
  success: boolean;
  platform: PlatformType;
  outputPath: string;
  exitCode: number;
  durationMs: number;
  stdout: string;
  stderr: string;
  artifactHash: string;
  manifestPath: string;
}

interface CompilePlan {
  platform: PlatformType;
  toolchain: ToolchainType;
  command: string;
  args: string[];
  sourceFiles: string[];
  outputPath: string;
  workDir: string;
  env: Record<string, string>;
}

interface ApiMapping {
  apiId: string;
  nativeApi: string;
  platform: PlatformType;
  minVersion: string;
}

interface CompatRule {
  apiId: string;
  platform: PlatformType;
  minVersion: string;
  maxVersion?: string;
  fallback?: string;
}

interface PlatformConfig {
  projectName: string;
  version: string;
  projectRoot: string;
  outputRoot: string;
  assetRoot: string;
  targets: PlatformTarget[];
  apiMappings: ApiMapping[];
  compatRules: CompatRule[];
  logFile: string;
}

const PLATFORM_MAP: Record<string, PlatformType> = {
  win32: "windows", windows: "windows", linux: "linux",
  darwin: "macos", macos: "macos", ios: "ios", android: "android",
};

function detectPlatform(): PlatformType {
  return PLATFORM_MAP[process.platform] || "linux";
}

function normalizePlatform(input: string | undefined | null): PlatformType {
  if (!input) return "linux";
  return PLATFORM_MAP[input.toLowerCase().trim()] || "linux";
}

function parseVersion(v: string): { major: number; minor: number; patch: number } {
  const parts = v.replace(/^v/i, "").split(/[.-]/);
  return {
    major: Number.parseInt(parts[0] || "0", 10),
    minor: Number.parseInt(parts[1] || "0", 10),
    patch: Number.parseInt(parts[2] || "0", 10),
  };
}

function cmpVersion(a: string, b: string): number {
  const x = parseVersion(a), y = parseVersion(b);
  if (x.major !== y.major) return x.major - y.major;
  if (x.minor !== y.minor) return x.minor - y.minor;
  return x.patch - y.patch;
}

function inVersionRange(v: string, min: string, max?: string): boolean {
  if (cmpVersion(v, min) < 0) return false;
  if (max && cmpVersion(v, max) > 0) return false;
  return true;
}

function fmtTime(ts: number): string {
  return new Date(ts).toISOString();
}

function fmtDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}

function ensureDir(dir: string): void {
  if (!dir) return;
  fs.mkdirSync(dir, { recursive: true });
}

async function readJson<T>(file: string, fallback: T): Promise<T> {
  if (!fs.existsSync(file)) return fallback;
  const raw = await fsp.readFile(file, "utf8");
  if (!raw.trim()) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    throw new Error(`配置文件解析失败: ${file}`);
  }
}

async function writeJson(file: string, data: unknown): Promise<void> {
  ensureDir(path.dirname(file));
  await fsp.writeFile(file, JSON.stringify(data, null, 2) + "\n", "utf8");
}

async function writeText(file: string, text: string): Promise<void> {
  ensureDir(path.dirname(file));
  await fsp.writeFile(file, text.endsWith("\n") ? text : text + "\n", "utf8");
}

function hashStr(s: string): string {
  return createHash("sha256").update(s, "utf8").digest("hex");
}

async function hashFile(file: string): Promise<string> {
  if (!fs.existsSync(file)) return "";
  return hashStr(fs.readFileSync(file));
}

class Log {
  private entries: Array<{ ts: number; lv: string; msg: string; meta?: Record<string, unknown> }> = [];

  constructor(private scope: string, private minLevel = "info") {}

  private log(lv: string, msg: string, meta?: Record<string, unknown>): void {
    const order: Record<string, number> = { debug: 0, info: 1, warn: 2, error: 3 };
    if (order[lv] < order[this.minLevel]) return;
    this.entries.push({ ts: Date.now(), lv, msg, meta });
    const prefix = `[${fmtTime(Date.now())}] [${lv.toUpperCase()}] [${this.scope}]`;
    if (lv === "error") {
      console.error(prefix, msg, meta || "");
    } else if (lv === "warn") {
      console.warn(prefix, msg, meta || "");
    } else {
      console.log(prefix, msg, meta || "");
    }
  }

  debug(msg: string, m?: Record<string, unknown>) { this.log("debug", msg, m); }
  info(msg: string, m?: Record<string, unknown>) { this.log("info", msg, m); }
  warn(msg: string, m?: Record<string, unknown>) { this.log("warn", msg, m); }
  error(msg: string, e?: unknown, m?: Record<string, unknown>) {
    const extra = e instanceof Error ? { err: e.message, ...m } : m;
    this.log("error", msg, extra);
  }

  getEntries() { return this.entries.map(e => ({ ...e })); }

  async flush(file: string): Promise<void> {
    if (!file) return;
    ensureDir(path.dirname(file));
    await writeText(file, this.entries.map(e => JSON.stringify(e)).join("\n"));
  }
}

async function probeTool(tool: ToolchainType): Promise<{ found: boolean; version: string }> {
  const map: Record<ToolchainType, { cmd: string; args: string[] }> = {
    android_ndk: { cmd: "ndk-build", args: ["--version"] },
    xcode: { cmd: "xcodebuild", args: ["-version"] },
    msvc: { cmd: "cl.exe", args: ["/Bv"] },
    gcc: { cmd: "g++", args: ["--version"] },
    clang: { cmd: "clang++", args: ["--version"] },
  };
  const { cmd, args } = map[tool] || { cmd: tool, args: [] };

  return new Promise(resolve => {
    execFile(cmd, args, { timeout: 5000, windowsHide: true }, (err, out, errOut) => {
      if (err) { resolve({ found: false, version: "" }); return; }
      const ver = (out || errOut || "").toString().split("\n")[0].slice(0, 80);
      resolve({ found: true, version: ver });
    });
  });
}

function resolveEnv(overrides: Partial<RuntimeEnv> = {}): RuntimeEnv {
  const platform = detectPlatform();
  return {
    platform,
    platformVersion: overrides.platformVersion || os.release(),
    arch: overrides.arch || process.arch,
    cpuCores: Math.max(1, overrides.cpuCores || os.cpus().length),
    totalMemory: overrides.totalMemory || os.totalmem(),
    freeMemory: overrides.freeMemory || os.freemem(),
    hostname: overrides.hostname || os.hostname(),
    permissions: overrides.permissions || ["filesystem", "network"],
  };
}

function getOutputExt(p: PlatformType): string {
  if (p === "windows") return ".exe";
  if (p === "ios") return ".ipa";
  if (p === "android") return ".apk";
  return "";
}

function sanitize(s: string): string {
  return s.trim().replace(/\s+/g, "-").replace(/[^a-zA-Z0-9._-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 64) || "package";
}

function resolveAssetPaths(p: PlatformType, base: string): Record<string, string> {
  const variant = p === "android" ? "android" : p === "ios" ? "ios" : "common";
  return {
    shared: path.resolve(base, "assets", "shared"),
    ui: path.resolve(base, "assets", "ui"),
    audio: path.resolve(base, "assets", "audio"),
    locale: path.resolve(base, "assets", "locale"),
    platformSpecific: path.resolve(base, "assets", variant),
    shaders: path.resolve(base, "shaders"),
  };
}

function checkMissingAssets(base: string, paths: Record<string, string>): string[] {
  const missing: string[] = [];
  for (const [k, v] of Object.entries(paths)) {
    if (!fs.existsSync(v)) missing.push(`${k}: ${v}`);
  }
  return missing;
}

const SOURCE_EXTENSIONS = new Set([".c", ".cc", ".cpp", ".cxx", ".m", ".mm"]);
const SOURCE_EXCLUDE_DIRS = new Set([".git", "build", "dist", "out", "logs", "reports", "node_modules"]);

function collectSourceFiles(rootDir: string): string[] {
  if (!fs.existsSync(rootDir)) return [];

  const files: string[] = [];
  const visit = (dir: string): void => {
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (SOURCE_EXCLUDE_DIRS.has(entry.name.toLowerCase())) continue;
        visit(fullPath);
        continue;
      }

      if (SOURCE_EXTENSIONS.has(path.extname(entry.name).toLowerCase())) {
        files.push(fullPath);
      }
    }
  };

  visit(rootDir);
  return files.sort((a, b) => a.localeCompare(b));
}

function resolveSourceFiles(target: PlatformTarget, projectRoot: string): string[] {
  const roots = [
    path.resolve(target.assetDir, "src"),
    path.resolve(target.assetDir, "source"),
    path.resolve(target.assetDir, "app"),
    path.resolve(target.assetDir, "native"),
    path.resolve(target.assetDir),
    path.resolve(projectRoot, "src"),
    path.resolve(projectRoot, "source"),
    path.resolve(projectRoot, "app"),
  ];

  for (const root of roots) {
    const files = collectSourceFiles(root);
    if (files.length > 0) return files;
  }

  return [];
}

function buildAndroidCompileArgs(target: PlatformTarget, outputDir: string): { cmd: string; args: string[] } {
  const ndkRoot = process.env["ANDROID_NDK_ROOT"] || process.env["NDK_ROOT"] || "/usr/local/android-ndk";
  const buildScript = path.join(target.assetDir, "jni", "Android.mk");

  if (!fs.existsSync(buildScript)) {
    throw new Error(`Android构建脚本不存在: ${buildScript}`);
  }

  return {
    cmd: path.join(ndkRoot, "ndk-build"),
    args: [
      "V=1",
      `APP_ABI=${target.arch}`,
      `APP_PLATFORM=android-${(target.defines["ANDROID_API"] || "26").replace(/\D/g, "")}`,
      `NDK_DEBUG=0`,
      `APP_STL=c++_shared`,
    ],
  };
}

function buildCompilePlan(config: PlatformConfig, target: PlatformTarget): CompilePlan {
  const platform = normalizePlatform(target.platform);
  const outputDir = path.resolve(config.outputRoot, platform, target.arch);
  const ext = getOutputExt(platform);
  const outputName = target.outputName.endsWith(ext) ? target.outputName : target.outputName + ext;
  const outputPath = path.join(outputDir, outputName);

  let command = "";
  const args: string[] = [];
  const env: Record<string, string> = {
    PROJECT_NAME: config.projectName,
    PLATFORM: platform.toUpperCase(),
    OUTPUT_DIR: outputDir,
  };

  if (platform === "android") {
    const android = buildAndroidCompileArgs(target, outputDir);
    command = android.cmd;
    args.push(...android.args);
    env["ANDROID_NDK_ROOT"] = process.env["ANDROID_NDK_ROOT"] || "/usr/local/android-ndk";
    env["NDK_PROJECT_PATH"] = target.assetDir;
    env["APP_BUILD_SCRIPT"] = path.join(target.assetDir, "jni", "Android.mk");
  } else if (platform === "ios") {
    command = "xcodebuild";
    args.push("-scheme", target.outputName, "-configuration", "Release", "-arch", target.arch);
  } else {
    const sourceFiles = resolveSourceFiles(target, config.projectRoot);
    if (sourceFiles.length === 0) {
      throw new Error(`未找到可编译源文件: ${target.assetDir}`);
    }

    const useMsvc = target.toolchain === "msvc";
    command = useMsvc ? "cl.exe" : target.toolchain === "gcc" ? "g++" : "clang++";

    if (useMsvc) {
      args.push("/nologo", `/Fe:${outputPath}`, "/std:c++17", ...target.extraFlags);
      for (const [k, v] of Object.entries(target.defines)) {
        args.push(`/D${k}=${v}`);
      }
      args.push(...sourceFiles);
    } else {
      args.push(...sourceFiles, "-o", outputPath, "-std=c++17", ...target.extraFlags);
      for (const [k, v] of Object.entries(target.defines)) {
        args.push(`-D${k}="${v}"`);
      }
    }

    return { platform, toolchain: target.toolchain, command, args, sourceFiles, outputPath, workDir: target.assetDir, env };
  }

  return { platform, toolchain: target.toolchain, command, args, sourceFiles: [], outputPath, workDir: target.assetDir, env };
}

async function runBuild(plan: CompilePlan, logger: Log): Promise<BuildResult> {
  const start = Date.now();
  const manifestPath = plan.outputPath + ".manifest.json";

  logger.info(`开始构建 ${plan.platform}`, { cmd: plan.command, args: plan.args });

  if (plan.platform === "android") {
    return runAndroidBuild(plan, manifestPath, logger, start);
  }

  return runGenericBuild(plan, manifestPath, logger, start);
}

async function runAndroidBuild(plan: CompilePlan, manifestPath: string, logger: Log, start: number): Promise<BuildResult> {
  return new Promise(resolve => {
    const proc = spawn(plan.command, plan.args, {
      cwd: plan.workDir,
      env: { ...process.env, ...plan.env },
      windowsHide: true,
    });

    let stdout = "";
    let stderr = "";

    proc.stdout?.on("data", d => { stdout += d.toString(); });
    proc.stderr?.on("data", d => { stderr += d.toString(); });

    proc.on("error", err => {
      const duration = Date.now() - start;
      logger.error(`Android构建进程失败`, err);
      resolve({ success: false, platform: plan.platform, outputPath: plan.outputPath, exitCode: -1, durationMs: duration, stdout: stdout.slice(0, 1000), stderr: err.message, artifactHash: "", manifestPath });
    });

    proc.on("close", async code => {
      const duration = Date.now() - start;
      const exitCode = code ?? -1;
      const exists = fs.existsSync(plan.outputPath);
      const hash = exists ? await hashFile(plan.outputPath) : "";

      if (exitCode === 0 && exists) {
        await writeJson(manifestPath, {
          platform: plan.platform,
          command: plan.command,
          args: plan.args,
          sourceFiles: plan.sourceFiles,
          outputPath: plan.outputPath,
          artifactHash: hash,
          builtAt: fmtTime(Date.now()),
          durationMs: duration,
        });
        logger.info(`Android构建完成`, { durationMs: duration, hash: hash.slice(0, 12) });
      } else {
        logger.error(`Android构建失败`, new Error(stderr.slice(0, 300)));
      }

      resolve({
        success: exitCode === 0 && exists,
        platform: plan.platform,
        outputPath: plan.outputPath,
        exitCode,
        durationMs: duration,
        stdout: stdout.slice(0, 1000),
        stderr: stderr.slice(0, 1000),
        artifactHash: hash,
        manifestPath,
      });
    });
  });
}

async function runGenericBuild(plan: CompilePlan, manifestPath: string, logger: Log, start: number): Promise<BuildResult> {
  return new Promise(resolve => {
    execFile(plan.command, plan.args, {
      timeout: 60000,
      maxBuffer: 512 * 1024,
      env: { ...process.env, ...plan.env },
      windowsHide: true,
    }, async (err, stdout, stderr) => {
      const duration = Date.now() - start;
      const exitCode = (err as NodeJS.ErrnoException & { code?: number })?.code ?? (err ? -1 : 0);
      const exists = fs.existsSync(plan.outputPath);
      const hash = exists ? await hashFile(plan.outputPath) : "";

      const result: BuildResult = {
        success: exitCode === 0 && exists,
        platform: plan.platform,
        outputPath: plan.outputPath,
        exitCode,
        durationMs: duration,
        stdout: (stdout || "").toString().slice(0, 1000),
        stderr: (stderr || "").toString().slice(0, 1000),
        artifactHash: hash,
        manifestPath,
      };

      if (result.success) {
        await writeJson(manifestPath, {
          platform: plan.platform,
          command: plan.command,
          args: plan.args,
          sourceFiles: plan.sourceFiles,
          outputPath: plan.outputPath,
          artifactHash: hash,
          builtAt: fmtTime(Date.now()),
          durationMs: duration,
        });
        logger.info(`构建成功: ${plan.platform}`, { durationMs: duration });
      } else {
        logger.error(`构建失败: ${plan.platform}`, new Error(stderr || `exit ${exitCode}`));
      }

      resolve(result);
    });
  });
}

function checkApiAvailable(apiId: string, platform: PlatformType, version: string, mappings: ApiMapping[], rules: CompatRule[]): { status: string; native: string; note: string } {
  const mapping = mappings.find(m => m.apiId === apiId && m.platform === platform);
  if (!mapping) {
    return { status: "unavailable", native: "", note: "平台未配置此API映射" };
  }

  const rule = rules.find(r => r.apiId === apiId && r.platform === platform);
  if (rule && !inVersionRange(version, rule.minVersion, rule.maxVersion)) {
    return { status: "unavailable", native: mapping.nativeApi, note: `版本${version}不在支持范围${rule.minVersion}-${rule.maxVersion || "最新"}` };
  }

  if (!inVersionRange(version, mapping.minVersion)) {
    return { status: "deprecated", native: mapping.nativeApi, note: `低于最低版本要求${mapping.minVersion}` };
  }

  return { status: "available", native: mapping.nativeApi, note: `映射到${mapping.nativeApi}` };
}

function loadConfig(cfgPath: string, logger: Log): PlatformConfig {
  if (!fs.existsSync(cfgPath)) {
    logger.warn(`配置文件不存在: ${cfgPath}，使用默认配置`);
    return makeDefaultConfig();
  }

  try {
    const raw = JSON.parse(fs.readFileSync(cfgPath, "utf8"));
    return validateConfig(raw, logger);
  } catch (err) {
    logger.error("配置解析失败", err);
    throw new Error(`无法加载配置: ${cfgPath}`);
  }
}

function makeDefaultConfig(): PlatformConfig {
  const root = path.resolve(process.cwd());
  return {
    projectName: "游戏跨平台运行适配管理系统",
    version: "V1.0.0",
    projectRoot: root,
    outputRoot: path.resolve(root, "build"),
    assetRoot: path.resolve(root, "assets"),
    targets: [
      {
        platform: "android",
        toolchain: "android_ndk",
        toolchainVersion: "26.1",
        arch: "arm64-v8a",
        defines: { PRODUCT_NAME: "游戏跨平台运行适配管理系统", ADAPTATION_MODE: "release", ANDROID_API: "26" },
        extraFlags: ["APP_STL=c++_shared", "NDK_DEBUG=0"],
        outputName: "game-runtime",
        assetDir: path.resolve(root, "assets", "android"),
      },
    ],
    apiMappings: [
      { apiId: "resource.loader", nativeApi: "AAssetManager_open", platform: "android", minVersion: "10.0.0" },
      { apiId: "system.info", nativeApi: "android.os.Build", platform: "android", minVersion: "10.0.0" },
      { apiId: "cloud.sync", nativeApi: "ContentResolver", platform: "android", minVersion: "10.0.0" },
    ],
    compatRules: [
      { apiId: "resource.loader", platform: "android", minVersion: "10.0.0", maxVersion: "15.9.9" },
      { apiId: "system.info", platform: "android", minVersion: "10.0.0", maxVersion: "15.9.9" },
    ],
    logFile: path.resolve(root, "logs", "adaptation.log"),
  };
}

function validateConfig(raw: Partial<PlatformConfig>, logger: Log): PlatformConfig {
  const root = path.resolve(raw.projectRoot || process.cwd());
  const cfg: PlatformConfig = {
    projectName: raw.projectName || "游戏跨平台运行适配管理系统",
    version: raw.version || "V1.0.0",
    projectRoot: root,
    outputRoot: path.resolve(raw.outputRoot || path.join(root, "build")),
    assetRoot: raw.assetRoot || path.resolve(root, "assets"),
    targets: [],
    apiMappings: raw.apiMappings || [],
    compatRules: raw.compatRules || [],
    logFile: raw.logFile || path.resolve(root, "logs", "adaptation.log"),
  };

  if (raw.targets && Array.isArray(raw.targets)) {
    for (const t of raw.targets) {
      if (!t.platform) { logger.warn("跳过缺少platform字段的目标"); continue; }
      cfg.targets.push({
        platform: normalizePlatform(t.platform),
        toolchain: t.toolchain || "gcc",
        toolchainVersion: t.toolchainVersion || "1.0",
        arch: t.arch || "x64",
        defines: t.defines || {},
        extraFlags: t.extraFlags || [],
        outputName: sanitize(t.outputName || "package"),
        assetDir: path.resolve(root, t.assetDir || "assets"),
      });
    }
  }

  if (cfg.targets.length === 0) {
    logger.warn("没有有效构建目标，使用默认android配置");
    cfg.targets = makeDefaultConfig().targets;
  }

  return cfg;
}

async function generateReport(
  config: PlatformConfig,
  env: RuntimeEnv,
  results: BuildResult[],
  apiChecks: Array<ApiMapping & { status: string; native: string; note: string }>,
  durationMs: number,
): Promise<{ jsonPath: string; textPath: string; hash: string }> {
  const reportDir = path.resolve(config.outputRoot, "reports");
  ensureDir(reportDir);

  const report = {
    projectName: config.projectName,
    version: config.version,
    generatedAt: fmtTime(Date.now()),
    runtime: env,
    builds: results.map(r => ({
      platform: r.platform,
      success: r.success,
      outputPath: r.outputPath,
      artifactHash: r.artifactHash,
      exitCode: r.exitCode,
      durationMs: r.durationMs,
    })),
    apiCompatibility: apiChecks.map(item => ({
      apiId: item.apiId,
      platform: item.platform,
      native: item.native,
      status: item.status,
      note: item.note,
      minVersion: item.minVersion,
    })),
    totalTimeMs: durationMs,
  };

  const hash = hashStr(JSON.stringify(report));
  const jsonPath = path.join(reportDir, "report.json");
  const textPath = path.join(reportDir, "report.txt");

  await writeJson(jsonPath, { ...report, reportHash: hash });

  const lines = [
    `项目: ${config.projectName}`,
    `版本: ${config.version}`,
    `生成时间: ${fmtTime(Date.now())}`,
    `平台: ${env.platform} ${env.platformVersion}`,
    `架构: ${env.arch}`,
    `主机: ${env.hostname}`,
    `构建结果:`,
    ...results.map(r => `  [${r.success ? "OK" : "FAIL"}] ${r.platform}: ${r.outputPath}${r.success ? "" : ` (exit ${r.exitCode})`}`),
    `API兼容性:`,
    ...apiChecks.map(item => `  [${item.status.toUpperCase()}] ${item.platform}.${item.apiId} -> ${item.native || "n/a"}${item.note ? ` (${item.note})` : ""}`),
    `总耗时: ${fmtDuration(durationMs)}`,
    `Hash: ${hash.slice(0, 16)}...`,
  ];
  await writeText(textPath, lines.join("\n"));

  return { jsonPath, textPath, hash };
}

async function runWorkflow(cfgPath?: string): Promise<void> {
  const start = Date.now();
  const configPath = cfgPath ? path.resolve(cfgPath) : path.resolve(process.cwd(), "adaptation.config.json");
  const logger = new Log("workflow");

  logger.info("=== 游戏跨平台运行适配管理系统构建流程启动 ===");
  logger.info(`配置: ${configPath}`);

  const config = loadConfig(configPath, logger);
  logger.info(`项目: ${config.projectName} v${config.version}`);
  logger.info(`输出: ${config.outputRoot}`);

  ensureDir(config.outputRoot);

  const env = resolveEnv();
  logger.info(`运行环境: ${env.platform} ${env.platformVersion} ${env.arch}`);

  for (const t of config.targets) {
    const probe = await probeTool(t.toolchain);
    if (probe.found) {
      logger.info(`工具链检测: ${t.toolchain} ${probe.version}`);
    } else {
      logger.warn(`工具链未检测到: ${t.toolchain}`);
    }
  }

  const missingAssets: string[] = [];
  for (const t of config.targets) {
    const assetPaths = resolveAssetPaths(t.platform, config.assetRoot);
    const missing = checkMissingAssets(config.assetRoot, assetPaths);
    missingAssets.push(...missing.map(m => `[${t.platform}] ${m}`));
  }
  if (missingAssets.length > 0) {
    logger.warn("部分资源目录缺失", { missing: missingAssets.slice(0, 3) });
  }

  const plans: CompilePlan[] = [];
  for (const t of config.targets) {
    try {
      const plan = buildCompilePlan(config, t);
      plans.push(plan);
      logger.info(`编译计划: ${t.platform} -> ${plan.outputPath}`);
    } catch (err) {
      logger.error(`编译计划生成失败: ${t.platform}`, err);
    }
  }

  const results: BuildResult[] = [];
  for (const plan of plans) {
    const r = await runBuild(plan, logger);
    results.push(r);
  }

  const apiChecks = config.apiMappings.map(m => {
    const check = checkApiAvailable(m.apiId, m.platform, env.platformVersion, config.apiMappings, config.compatRules);
    return { ...m, ...check };
  });

  const reportFiles = await generateReport(config, env, results, apiChecks, Date.now() - start);

  const apiAvailable = apiChecks.filter(item => item.status === "available").length;
  const apiDeprecated = apiChecks.filter(item => item.status === "deprecated").length;
  const apiUnavailable = apiChecks.filter(item => item.status === "unavailable").length;
  logger.info("API兼容性结果", {
    available: apiAvailable,
    deprecated: apiDeprecated,
    unavailable: apiUnavailable,
  });

  logger.info("=== 构建完成 ===");
  logger.info(`报告: ${reportFiles.jsonPath}`);
  logger.info(`总耗时: ${fmtDuration(Date.now() - start)}`);

  await logger.flush(config.logFile);
}

function main(): void {
  const cfg = process.argv[2];
  runWorkflow(cfg).catch(err => {
    console.error("流程异常:", err instanceof Error ? err.stack : err);
    process.exit(1);
  });
}

if (require.main === module) {
  main();
}

export {
  detectPlatform, normalizePlatform, parseVersion, cmpVersion, inVersionRange,
  resolveEnv, buildCompilePlan, runBuild, checkApiAvailable,
  loadConfig, generateReport, Log,
};
