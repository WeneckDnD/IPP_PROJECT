#!/usr/bin/env node
/**
 * An integration testing script for the SOL26 interpreter.
 * *
 * IPP: You can implement the entire tool in this file if you wish, but it is recommended to split
 *      the code into multiple files and modules as you see fit.
 *
 *      Below, you have some code to get you started with the CLI argument parsing and logging setup,
 *      but you are **free to modify it** in whatever way you like.
 *
 * Author: Ondřej Ondryáš <iondryas@fit.vut.cz>
 * Author: Tadeas Bujdoso <xbujdot00>
 * 
 * AI usage notice: The author used OpenAI Codex to create the implementation of this
 *                  module based on its Python counterpart.
*/
import {
  existsSync,
  lstatSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, extname, join, resolve } from "node:path";
import { parseArgs } from "node:util";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

import {
  CategoryReport,
  TestCaseDefinition,
  TestCaseType,
  TestCaseReport,
  TestReport,
  TestResult,
  UnexecutedReason,
  UnexecutedReasonCode,
} from "./models.js";
import { pino } from "pino";

type JsonLike = string | number | boolean | null | JsonLike[] | { [k: string]: JsonLike };

interface CliArguments {
  tests_dir: string;
  recursive: boolean;
  output: string | null;
  dry_run: boolean;
  include: string[] | null;
  include_category: string[] | null;
  include_test: string[] | null;
  exclude: string[] | null;
  exclude_category: string[] | null;
  exclude_test: string[] | null;
  verbose: number;
  regex_filters: boolean;
}

interface TestCaseExecutionInfo {
  definition: TestCaseDefinition;
  source_file: string | null;
}

interface ProcessResult {
  exitCode: number | null;
  stdout: string;
  stderr: string;
  cannotExecute: boolean;
}

const logger = pino({
  transport: {
    target: "pino-pretty",
    options: {
      colorize: true,
      destination: 2,
    },
  },
});

const DOUBLE_LETTER_SHORT_OPTION_NORMALIZATION = new Map<string, string>([
  ["-ic", "--include-category"],
  ["-it", "--include-test"],
  ["-ec", "--exclude-category"],
  ["-et", "--exclude-test"],
]);

const HELP_TEXT = [
  "Usage:",
  "  tester [options] tests_dir",
  "",
  "Positional arguments:",
  "  tests_dir                 Path to a directory with the test cases in the SOLtest format.",
  "",
  "Options:",
  "  -h, --help                Show this help message and exit.",
  "  -r, --recursive           Recursively search for test cases in subdirectories of the provided directory.",
  "  -o, --output <path>       The output file to write the test results to. If not provided, results will be printed to standard output.",
  "  --dry-run                 Perform a dry run: discover the test cases but don't actually execute them.",
  "  -i, --include <value>     Include only test cases with the specified name or category. Can be used multiple times to specify multiple criteria.Can be combined with -ic and -it.",
  "  -ic, --include-category <value>",
  "                            Include only test cases with the specified category. Can be used multiple times to specify multiple accepted categories. Can be combined with -it and -i.",
  "  -it, --include-test <value>",
  "                            Include only test cases with the specified name. Can be used multiple times to specify multiple accepted names. Can be combined with -ic and -i.",
  "  -e, --exclude <value>     Exclude test cases with the specified name or category. Can be used multiple times to specify multiple criteria.Can be combined with -ic and -it.",
  "  -ec, --exclude-category <value>",
  "                            Exclude test cases with the specified category. Can be used multiple times to specify multiple accepted categories. Can be combined with -it and -i.",
  "  -et, --exclude-test <value>",
  "                            Exclude test cases with the specified name. Can be used multiple times to specify multiple accepted names. Can be combined with -ic and -i.",
  "  -g                        When used, the filters specified with -i[ct]/-e[ct] will be interpreted as regular expressions instead of literal strings.",
  "  -v, --verbose             Enable verbose logging output (using once = INFO level, using twice = DEBUG level).",
];

const PARSE_OPTIONS = {
  help: { type: "boolean", short: "h", default: false },
  recursive: { type: "boolean", short: "r", default: false },
  output: { type: "string", short: "o" },
  "dry-run": { type: "boolean", default: false },
  include: { type: "string", short: "i", multiple: true },
  "include-category": { type: "string", multiple: true },
  "include-test": { type: "string", multiple: true },
  exclude: { type: "string", short: "e", multiple: true },
  "exclude-category": { type: "string", multiple: true },
  "exclude-test": { type: "string", multiple: true },
  "regex-filters": { type: "boolean", short: "g", default: false },
  verbose: { type: "boolean", short: "v", multiple: true },
} as const;

function writeResult(resultReport: TestReport, outputFile: string | null): void {
  const resultJson = JSON.stringify(resultReport.toJSON(), null, 2);
  if (outputFile !== null) {
    writeFileSync(outputFile, resultJson, "utf8");
    return;
  }

  console.log(resultJson);
}

function normalizeArgv(argv: string[]): string[] {
  return argv.map((arg) => DOUBLE_LETTER_SHORT_OPTION_NORMALIZATION.get(arg) ?? arg);
}

function printHelp(): void {
  console.log(HELP_TEXT.join("\n"));
}

function listOrNull(values: string[] | undefined): string[] | null {
  if (values === undefined || values.length === 0) {
    return null;
  }
  return values;
}

function parseCliArgumentsRaw(argv: string[]) {
  return parseArgs({
    args: normalizeArgv(argv),
    options: PARSE_OPTIONS,
    allowPositionals: true,
    strict: true,
  } as const);
}

function parseArguments(): CliArguments {
  let parsed: ReturnType<typeof parseCliArgumentsRaw>;
  try {
    parsed = parseCliArgumentsRaw(process.argv.slice(2));
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(message);
    process.exit(2);
  }

  const parsedValues = parsed.values;

  if (parsedValues["help"]) {
    printHelp();
    process.exit(0);
  }

  if (parsed.positionals.length !== 1 || parsed.positionals[0] === undefined) {
    console.error("Exactly one positional argument (tests_dir) is required.");
    process.exit(2);
  }

  const args: CliArguments = {
    tests_dir: resolve(parsed.positionals[0]),
    recursive: parsedValues["recursive"],
    output: parsedValues["output"] ?? null,
    dry_run: parsedValues["dry-run"],
    include: listOrNull(parsedValues["include"]),
    include_category: listOrNull(parsedValues["include-category"]),
    include_test: listOrNull(parsedValues["include-test"]),
    exclude: listOrNull(parsedValues["exclude"]),
    exclude_category: listOrNull(parsedValues["exclude-category"]),
    exclude_test: listOrNull(parsedValues["exclude-test"]),
    verbose: parsedValues["verbose"]?.length ?? 0,
    regex_filters: parsedValues["regex-filters"],
  };

  if (!existsSync(args.tests_dir) || !lstatSync(args.tests_dir).isDirectory()) {
    console.error("The provided path is not a directory.");
    process.exit(1);
  }

  if (args.output !== null) {
    const outputParent = dirname(args.output);
    if (!existsSync(outputParent)) {
      console.error("The parent directory of the output file does not exist.");
      process.exit(1);
    }

    if (existsSync(args.output)) {
      logger.warn("The output file will be overwritten: %s", args.output);
    }
  }

  return args;
}

function repositoryRootFromScript(): string {
  const scriptDir = dirname(fileURLToPath(import.meta.url));
  return resolve(scriptDir, "..", "..", "..");
}

function resolvePythonExecutable(pythonRoot: string): string {
  const envPython = process.env["IPP_TESTER_PYTHON"];
  if (envPython !== undefined && envPython.length > 0) {
    return envPython;
  }

  const venvPython = resolve(pythonRoot, "int", ".venv", "bin", "python");
  if (existsSync(venvPython)) {
    return venvPython;
  }

  return "python3";
}

function resolveToolPaths() {
  const repoRoot = repositoryRootFromScript();
  const pythonRoot = resolve(process.env["IPP_PYTHON_ROOT"] ?? resolve(repoRoot, "python"));
  const parserScript = resolve(
    process.env["IPP_SOL2XML_PATH"] ?? resolve(repoRoot, "sol2xml", "sol_to_xml.py")
  );
  const interpreterScript = resolve(
    process.env["IPP_SOLINT_PATH"] ?? resolve(pythonRoot, "int", "src", "solint.py")
  );
  const pythonExecutable = resolvePythonExecutable(pythonRoot);

  return {
    parserScript,
    interpreterScript,
    pythonExecutable,
  };
}

function discoverTestFiles(testsDir: string, recursive: boolean): string[] {
  const discovered: string[] = [];

  function scanDirectory(currentPath: string): void {
    const entries = readdirSync(currentPath, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = join(currentPath, entry.name);
      if (entry.isDirectory()) {
        if (recursive) {
          scanDirectory(fullPath);
        }
        continue;
      }
      if (entry.isFile() && extname(entry.name) === ".test") {
        discovered.push(fullPath);
      }
    }
  }

  scanDirectory(testsDir);
  discovered.sort((left, right) => left.localeCompare(right));
  return discovered;
}

function parseSimpleLiteral(raw: string): JsonLike {
  const trimmed = raw.trim();
  if (trimmed === "null") {
    return null;
  }
  if (trimmed === "true") {
    return true;
  }
  if (trimmed === "false") {
    return false;
  }
  if (/^-?\d+$/.test(trimmed)) {
    return Number(trimmed);
  }
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1);
  }
  if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
    const inner = trimmed.slice(1, -1).trim();
    if (inner.length === 0) {
      return [];
    }
    return inner.split(",").map((item) => parseSimpleLiteral(item));
  }
  return trimmed;
}

function parseSimpleKeyValue(content: string): Record<string, JsonLike> {
  const result: Record<string, JsonLike> = {};
  const lines = content.split(/\r?\n/u);
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.length === 0 || trimmed.startsWith("#") || trimmed.startsWith("//")) {
      continue;
    }
    const match = trimmed.match(/^([A-Za-z_][A-Za-z0-9_-]*)\s*[:=]\s*(.+)$/u);
    if (match === null) {
      throw new Error(`Cannot parse line: ${line}`);
    }
    const key = match[1];
    const valueRaw = match[2];
    if (key === undefined || valueRaw === undefined) {
      throw new Error(`Cannot parse line: ${line}`);
    }
    result[key] = parseSimpleLiteral(valueRaw);
  }
  return result;
}

function parseTestFileRaw(filePath: string): Record<string, JsonLike> {
  const content = readFileSync(filePath, "utf8");
  try {
    const parsed = JSON.parse(content) as unknown;
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("JSON root must be an object.");
    }
    return parsed as Record<string, JsonLike>;
  } catch {
    return parseSimpleKeyValue(content);
  }
}

function asString(value: JsonLike | undefined): string | null {
  return typeof value === "string" ? value : null;
}

function asNumberArray(value: JsonLike | undefined): number[] | null {
  if (value === undefined || value === null) {
    return null;
  }
  if (typeof value === "number") {
    return [value];
  }
  if (Array.isArray(value)) {
    const mapped = value.map((item) => {
      if (typeof item !== "number") {
        throw new Error("Exit code array contains a non-number value.");
      }
      return item;
    });
    return mapped;
  }
  throw new Error("Expected an exit code list or number.");
}

function mapTestType(value: JsonLike | undefined): TestCaseType | null {
  if (value === undefined || value === null) {
    return null;
  }
  if (typeof value === "number") {
    if (value === TestCaseType.PARSE_ONLY) {
      return TestCaseType.PARSE_ONLY;
    }
    if (value === TestCaseType.EXECUTE_ONLY) {
      return TestCaseType.EXECUTE_ONLY;
    }
    if (value === TestCaseType.COMBINED) {
      return TestCaseType.COMBINED;
    }
    throw new Error(`Unknown numeric test type: ${value}`);
  }
  if (typeof value !== "string") {
    throw new Error("Invalid test_type value.");
  }

  const normalized = value.toLowerCase();
  if (normalized === "parse_only" || normalized === "parse" || normalized === "parser") {
    return TestCaseType.PARSE_ONLY;
  }
  if (
    normalized === "execute_only" ||
    normalized === "execute" ||
    normalized === "interpreter" ||
    normalized === "int"
  ) {
    return TestCaseType.EXECUTE_ONLY;
  }
  if (normalized === "combined" || normalized === "both") {
    return TestCaseType.COMBINED;
  }

  throw new Error(`Unknown test_type: ${value}`);
}

function joinMessage(message: string, details: string): string {
  if (details.length === 0) {
    return message;
  }
  return `${message}: ${details}`;
}

function inferTypeFromFields(
  parserCodes: number[] | null,
  interpreterCodes: number[] | null,
  sourceFile: string | null
): TestCaseType | null {
  const hasParser = parserCodes !== null;
  const hasInterpreter = interpreterCodes !== null;
  if (hasParser && !hasInterpreter) {
    return TestCaseType.PARSE_ONLY;
  }
  if (!hasParser && hasInterpreter) {
    if (sourceFile !== null) {
      const extension = extname(sourceFile).toLowerCase();
      if (extension === ".xml") {
        return TestCaseType.EXECUTE_ONLY;
      }
      if (extension === ".sol26" || extension === ".sol") {
        return TestCaseType.COMBINED;
      }
    }
    return null;
  }
  if (hasParser && hasInterpreter) {
    if (parserCodes.length === 1 && parserCodes[0] === 0) {
      return TestCaseType.COMBINED;
    }
    return null;
  }
  return null;
}

function firstExistingPath(paths: string[]): string | null {
  for (const filePath of paths) {
    if (existsSync(filePath)) {
      return filePath;
    }
  }
  return null;
}

function resolveSourceFile(
  raw: Record<string, JsonLike>,
  testFilePath: string,
  testType: TestCaseType | null
): string | null {
  const explicitSource =
    asString(raw["source"]) ?? asString(raw["source_file"]) ?? asString(raw["program"]);
  if (explicitSource !== null) {
    return resolve(dirname(testFilePath), explicitSource);
  }

  const stem = testFilePath.slice(0, -extname(testFilePath).length);
  const solCandidates = [`${stem}.sol26`, `${stem}.sol`];
  const xmlCandidate = `${stem}.xml`;

  if (testType === TestCaseType.EXECUTE_ONLY) {
    return firstExistingPath([xmlCandidate]);
  }
  if (testType === TestCaseType.PARSE_ONLY || testType === TestCaseType.COMBINED) {
    return firstExistingPath(solCandidates);
  }

  return firstExistingPath([xmlCandidate, ...solCandidates]);
}

function parseTestDefinition(filePath: string): TestCaseExecutionInfo {
  const raw = parseTestFileRaw(filePath);

  const parserCodes = asNumberArray(raw["expected_parser_exit_codes"] ?? raw["parser_exit_codes"]);
  const interpreterCodes = asNumberArray(
    raw["expected_interpreter_exit_codes"] ?? raw["interpreter_exit_codes"]
  );
  let testType = mapTestType(raw["test_type"]);
  const sourceBeforeInfer = resolveSourceFile(raw, filePath, testType);

  if (testType === null) {
    testType = inferTypeFromFields(parserCodes, interpreterCodes, sourceBeforeInfer);
    if (testType === null) {
      throw new Error("cannot_determine_type");
    }
  }

  const sourceFile = sourceBeforeInfer ?? resolveSourceFile(raw, filePath, testType);
  const testName = basename(filePath, ".test");
  const stdinPath = `${filePath.slice(0, -5)}.in`;
  const stdoutPath = `${filePath.slice(0, -5)}.out`;

  const points = typeof raw["points"] === "number" ? raw["points"] : null;

  const definition = new TestCaseDefinition({
    name: testName,
    test_source_path: filePath,
    stdin_file: existsSync(stdinPath) ? stdinPath : null,
    expected_stdout_file: existsSync(stdoutPath) ? stdoutPath : null,
    test_type: testType,
    description: asString(raw["description"]),
    category: asString(raw["category"]) ?? "default",
    ...(points !== null ? { points } : {}),
    expected_parser_exit_codes: parserCodes,
    expected_interpreter_exit_codes: interpreterCodes,
  });

  return { definition, source_file: sourceFile };
}

function isMatch(value: string, filters: string[] | null, useRegex: boolean): boolean {
  if (filters === null || filters.length === 0) {
    return false;
  }
  return filters.some((filterValue) => {
    if (useRegex) {
      try {
        return new RegExp(filterValue, "u").test(value);
      } catch {
        return false;
      }
    }
    return value === filterValue;
  });
}

function shouldIncludeTest(testCase: TestCaseDefinition, args: CliArguments): boolean {
  const included =
    args.include === null &&
    args.include_category === null &&
    args.include_test === null
      ? true
      : isMatch(testCase.name, args.include_test, args.regex_filters) ||
        isMatch(testCase.category, args.include_category, args.regex_filters) ||
        isMatch(testCase.name, args.include, args.regex_filters) ||
        isMatch(testCase.category, args.include, args.regex_filters);
  if (!included) {
    return false;
  }

  const excluded =
    isMatch(testCase.name, args.exclude_test, args.regex_filters) ||
    isMatch(testCase.category, args.exclude_category, args.regex_filters) ||
    isMatch(testCase.name, args.exclude, args.regex_filters) ||
    isMatch(testCase.category, args.exclude, args.regex_filters);

  return !excluded;
}

function runProcess(command: string, commandArgs: string[], stdinInput: string | null): ProcessResult {
  const result = spawnSync(command, commandArgs, {
    encoding: "utf8",
    input: stdinInput ?? undefined,
    maxBuffer: 10 * 1024 * 1024,
  });

  return {
    exitCode: result.status,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
    cannotExecute: result.error !== undefined,
  };
}

function expectedCodesContains(actualCode: number | null, expectedCodes: number[] | null): boolean {
  if (actualCode === null || expectedCodes === null) {
    return false;
  }
  return expectedCodes.includes(actualCode);
}

function makeSimpleDiff(expected: string, actual: string): string {
  if (expected === actual) {
    return "";
  }
  const expectedLines = expected.split(/\r?\n/u);
  const actualLines = actual.split(/\r?\n/u);
  const maxLen = Math.max(expectedLines.length, actualLines.length);

  const output: string[] = [];
  for (let index = 0; index < maxLen; index += 1) {
    const expectedLine = expectedLines[index];
    const actualLine = actualLines[index];
    if (expectedLine === actualLine) {
      continue;
    }
    output.push(`- ${expectedLine ?? ""}`);
    output.push(`+ ${actualLine ?? ""}`);
    if (output.length >= 20) {
      output.push("... (diff truncated)");
      break;
    }
  }
  return output.join("\n");
}

function withTemporaryXmlFile(xmlContent: string, callback: (path: string) => TestCaseReport): TestCaseReport {
  const tempDirectory = mkdtempSync(join(tmpdir(), "sol26-int-"));
  const xmlPath = join(tempDirectory, "combined.xml");
  writeFileSync(xmlPath, xmlContent, "utf8");
  try {
    return callback(xmlPath);
  } finally {
    rmSync(tempDirectory, { recursive: true, force: true });
  }
}

function executeInterpreter(
  interpreterExecutable: string,
  interpreterScript: string,
  xmlPath: string,
  stdinPath: string | null,
  expectedCodes: number[] | null,
  expectedStdoutPath: string | null
): TestCaseReport {
  const args = [interpreterScript, "--source", xmlPath];
  if (stdinPath !== null) {
    args.push("--input", stdinPath);
  }
  const interpreter = runProcess(interpreterExecutable, args, null);

  if (interpreter.cannotExecute) {
    return new TestCaseReport(
      TestResult.UNEXPECTED_INTERPRETER_EXIT_CODE,
      null,
      interpreter.exitCode,
      null,
      null,
      interpreter.stdout,
      joinMessage("Cannot execute interpreter", interpreter.stderr),
      null
    );
  }

  if (!expectedCodesContains(interpreter.exitCode, expectedCodes)) {
    return new TestCaseReport(
      TestResult.UNEXPECTED_INTERPRETER_EXIT_CODE,
      null,
      interpreter.exitCode,
      null,
      null,
      interpreter.stdout,
      interpreter.stderr,
      null
    );
  }

  if (expectedStdoutPath !== null) {
    const expectedStdout = readFileSync(expectedStdoutPath, "utf8");
    if (expectedStdout !== interpreter.stdout) {
      return new TestCaseReport(
        TestResult.INTERPRETER_RESULT_DIFFERS,
        null,
        interpreter.exitCode,
        null,
        null,
        interpreter.stdout,
        interpreter.stderr,
        makeSimpleDiff(expectedStdout, interpreter.stdout)
      );
    }
  }

  return new TestCaseReport(
    TestResult.PASSED,
    null,
    interpreter.exitCode,
    null,
    null,
    interpreter.stdout,
    interpreter.stderr,
    null
  );
}

function executeTestCase(
  testCase: TestCaseExecutionInfo,
  toolPaths: ReturnType<typeof resolveToolPaths>
): TestCaseReport | UnexecutedReason {
  const { definition, source_file: sourceFile } = testCase;
  if (sourceFile === null || !existsSync(sourceFile)) {
    return new UnexecutedReason(
      UnexecutedReasonCode.CANNOT_EXECUTE,
      "Missing source file for the test case."
    );
  }

  if (definition.test_type === TestCaseType.PARSE_ONLY || definition.test_type === TestCaseType.COMBINED) {
    const parser = runProcess(toolPaths.pythonExecutable, [toolPaths.parserScript, sourceFile], null);
    if (parser.cannotExecute) {
      return new UnexecutedReason(
        UnexecutedReasonCode.CANNOT_EXECUTE,
        joinMessage("Cannot execute parser", parser.stderr)
      );
    }

    if (!expectedCodesContains(parser.exitCode, definition.expected_parser_exit_codes)) {
      return new TestCaseReport(
        TestResult.UNEXPECTED_PARSER_EXIT_CODE,
        parser.exitCode,
        null,
        parser.stdout,
        parser.stderr,
        null,
        null,
        null
      );
    }

    if (definition.test_type === TestCaseType.PARSE_ONLY) {
      return new TestCaseReport(
        TestResult.PASSED,
        parser.exitCode,
        null,
        parser.stdout,
        parser.stderr,
        null,
        null,
        null
      );
    }

    return withTemporaryXmlFile(parser.stdout, (xmlPath) => {
      const interpreterResult = executeInterpreter(
        toolPaths.pythonExecutable,
        toolPaths.interpreterScript,
        xmlPath,
        definition.stdin_file,
        definition.expected_interpreter_exit_codes,
        definition.expected_stdout_file
      );
      return new TestCaseReport(
        interpreterResult.result,
        parser.exitCode,
        interpreterResult.interpreter_exit_code,
        parser.stdout,
        parser.stderr,
        interpreterResult.interpreter_stdout,
        interpreterResult.interpreter_stderr,
        interpreterResult.diff_output
      );
    });
  }

  return executeInterpreter(
    toolPaths.pythonExecutable,
    toolPaths.interpreterScript,
    sourceFile,
    definition.stdin_file,
    definition.expected_interpreter_exit_codes,
    definition.expected_stdout_file
  );
}

function main(): void {
  logger.level = "warn";
  const args = parseArguments();

  if (args.verbose >= 2) {
    logger.level = "debug";
  } else if (args.verbose === 1) {
    logger.level = "info";
  }

  const testFiles = discoverTestFiles(args.tests_dir, args.recursive);
  const discovered: TestCaseExecutionInfo[] = [];
  const unexecuted: Record<string, UnexecutedReason> = {};

  for (const testFile of testFiles) {
    const testName = basename(testFile, ".test");
    try {
      discovered.push(parseTestDefinition(testFile));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      const reasonCode =
        message === "cannot_determine_type"
          ? UnexecutedReasonCode.CANNOT_DETERMINE_TYPE
          : UnexecutedReasonCode.MALFORMED_TEST_CASE_FILE;
      unexecuted[testName] = new UnexecutedReason(reasonCode, message);
    }
  }

  const report = new TestReport({
    discovered_test_cases: discovered.map((item) => item.definition),
    unexecuted,
    results: null,
  });

  if (args.dry_run) {
    writeResult(report, args.output);
    return;
  }

  const toolPaths = resolveToolPaths();
  const categoryResults = new Map<
    string,
    {
      total_points: number;
      passed_points: number;
      test_results: Record<string, TestCaseReport>;
    }
  >();

  for (const testCase of discovered) {
    if (!shouldIncludeTest(testCase.definition, args)) {
      unexecuted[testCase.definition.name] = new UnexecutedReason(
        UnexecutedReasonCode.FILTERED_OUT,
        "Filtered out by include/exclude rules."
      );
      continue;
    }

    const executionResult = executeTestCase(testCase, toolPaths);
    if (executionResult instanceof UnexecutedReason) {
      unexecuted[testCase.definition.name] = executionResult;
      continue;
    }

    const category = testCase.definition.category;
    const previous = categoryResults.get(category) ?? {
      total_points: 0,
      passed_points: 0,
      test_results: {},
    };

    previous.total_points += testCase.definition.points;
    if (executionResult.result === TestResult.PASSED) {
      previous.passed_points += testCase.definition.points;
    }
    previous.test_results[testCase.definition.name] = executionResult;
    categoryResults.set(category, previous);
  }

  const resultsObject: Record<string, CategoryReport> = {};
  for (const [category, result] of categoryResults.entries()) {
    resultsObject[category] = new CategoryReport(
      result.total_points,
      result.passed_points,
      result.test_results
    );
  }

  const finalReport = new TestReport({
    discovered_test_cases: report.discovered_test_cases,
    unexecuted: report.unexecuted,
    results: Object.keys(resultsObject).length === 0 ? null : resultsObject,
  });
  writeResult(finalReport, args.output);
}

main();
