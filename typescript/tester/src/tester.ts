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
  source_code: string;
  source_is_xml: boolean;
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

interface ParsedSoltest {
  description: string | null;
  category: string;
  points: number;
  expected_parser_exit_codes: number[] | null;
  expected_interpreter_exit_codes: number[] | null;
  source_code: string;
  source_is_xml: boolean;
}

function parseExitCode(raw: string, prefix: string): number {
  const value = Number(raw.trim());
  if (!Number.isInteger(value)) {
    throw new Error(`malformed_test_case: invalid ${prefix} exit code '${raw.trim()}'`);
  }
  return value;
}

interface ParsedSoltestHeaderState {
  description: string | null;
  category: string | null;
  points: number | null;
  parserCodes: number[];
  interpreterCodes: number[];
}

interface ParsedSoltestHeader {
  description: string | null;
  category: string;
  points: number;
  parserCodes: number[];
  interpreterCodes: number[];
}

function createEmptyHeaderState(): ParsedSoltestHeaderState {
  return {
    description: null,
    category: null,
    points: null,
    parserCodes: [],
    interpreterCodes: [],
  };
}

function parseHeaderLine(line: string, state: ParsedSoltestHeaderState): void {
  if (line.startsWith("***")) {
    const description = line.slice(3).trim();
    state.description = description.length > 0 ? description : null;
    return;
  }

  if (line.startsWith("+++")) {
    const value = line.slice(3).trim();
    if (value.length === 0) {
      throw new Error("malformed_test_case: empty category");
    }
    state.category = value;
    return;
  }

  if (line.startsWith("!C!")) {
    state.parserCodes.push(parseExitCode(line.slice(3), "parser"));
    return;
  }

  if (line.startsWith("!I!")) {
    state.interpreterCodes.push(parseExitCode(line.slice(3), "interpreter"));
    return;
  }

  if (line.startsWith(">>>")) {
    const parsedPoints = parseExitCode(line.slice(3), "points");
    if (parsedPoints <= 0) {
      throw new Error("malformed_test_case: points must be > 0");
    }
    state.points = parsedPoints;
    return;
  }

  throw new Error(`malformed_test_case: unknown header line '${line}'`);
}

function parseSoltestHeader(header: string[]): ParsedSoltestHeader {
  const state = createEmptyHeaderState();
  for (const rawLine of header) {
    parseHeaderLine(rawLine.trim(), state);
  }

  if (state.category === null) {
    throw new Error("malformed_test_case: missing category");
  }
  if (state.points === null) {
    throw new Error("malformed_test_case: missing points");
  }

  return {
    description: state.description,
    category: state.category,
    points: state.points,
    parserCodes: state.parserCodes,
    interpreterCodes: state.interpreterCodes,
  };
}

function parseExpectedExitCodes(sourceCode: string, header: ParsedSoltestHeader) {
  const sourceIsXml = sourceCode.trimStart().startsWith("<");
  const expectedParser = header.parserCodes.length > 0 ? header.parserCodes : null;
  const expectedInterpreter = header.interpreterCodes.length > 0 ? header.interpreterCodes : null;

  if (sourceIsXml) {
    if (expectedParser !== null) {
      throw new Error("cannot_determine_type");
    }
    if (expectedInterpreter === null) {
      throw new Error("malformed_test_case: missing interpreter exit codes for XML source");
    }
  } else if (expectedParser === null) {
    throw new Error("malformed_test_case: missing parser exit codes for SOL source");
  }

  return { sourceIsXml, expectedParser, expectedInterpreter };
}

function parseSoltest(content: string): ParsedSoltest {
  const lines = content.split(/\r?\n/u);
  const separatorIdx = lines.findIndex((line) => line.trim().length === 0);
  if (separatorIdx < 0) {
    throw new Error("malformed_test_case: missing blank line before source code");
  }

  const header = lines.slice(0, separatorIdx);
  const sourceLines = lines.slice(separatorIdx + 1);
  const sourceCode = sourceLines.join("\n").trimEnd();
  if (sourceCode.trim().length === 0) {
    throw new Error("malformed_test_case: missing source code");
  }

  const headerState = parseSoltestHeader(header);
  const { sourceIsXml, expectedParser, expectedInterpreter } = parseExpectedExitCodes(
    sourceCode,
    headerState
  );

  return {
    description: headerState.description,
    category: headerState.category,
    points: headerState.points,
    expected_parser_exit_codes: expectedParser,
    expected_interpreter_exit_codes: expectedInterpreter,
    source_code: sourceCode,
    source_is_xml: sourceIsXml,
  };
}

function parseTestFileRaw(filePath: string): ParsedSoltest {
  const content = readFileSync(filePath, "utf8");
  return parseSoltest(content);
}

function joinMessage(message: string, details: string): string {
  if (details.length === 0) {
    return message;
  }
  return `${message}: ${details}`;
}

function parseTestDefinition(filePath: string): TestCaseExecutionInfo {
  const raw = parseTestFileRaw(filePath);

  const testName = basename(filePath, ".test");
  const stdinPath = `${filePath.slice(0, -5)}.in`;
  const stdoutPath = `${filePath.slice(0, -5)}.out`;

  let testType: TestCaseType;
  if (raw.source_is_xml) {
    testType = TestCaseType.EXECUTE_ONLY;
  } else if (raw.expected_interpreter_exit_codes === null) {
    testType = TestCaseType.PARSE_ONLY;
  } else {
    testType = TestCaseType.COMBINED;
  }

  const definition = new TestCaseDefinition({
    name: testName,
    test_source_path: filePath,
    stdin_file: existsSync(stdinPath) ? stdinPath : null,
    expected_stdout_file: existsSync(stdoutPath) ? stdoutPath : null,
    test_type: testType,
    description: raw.description,
    category: raw.category,
    points: raw.points,
    expected_parser_exit_codes: raw.expected_parser_exit_codes,
    expected_interpreter_exit_codes: raw.expected_interpreter_exit_codes,
  });

  return { definition, source_code: raw.source_code, source_is_xml: raw.source_is_xml };
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
    args.include === null && args.include_category === null && args.include_test === null
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

function runProcess(
  command: string,
  commandArgs: string[],
  stdinInput: string | null
): ProcessResult {
  const result = spawnSync(command, commandArgs, {
    encoding: "utf8",
    input: stdinInput ?? undefined,
    maxBuffer: 10 * 1024 * 1024,
  });

  return {
    exitCode: result.status,
    stdout: result.stdout,
    stderr: result.stderr,
    cannotExecute: result.error !== undefined,
  };
}

function expectedCodesContains(
  actualCode: number | null,
  expectedCodes: number[] | null
): boolean {
  if (actualCode === null || expectedCodes === null) {
    return false;
  }
  return expectedCodes.includes(actualCode);
}

function runDiff(
  expectedStdoutPath: string,
  actualStdout: string
): {
  same: boolean;
  output: string | null;
} {
  const tempDirectory = mkdtempSync(join(tmpdir(), "sol26-diff-"));
  const actualPath = join(tempDirectory, "actual.out");
  writeFileSync(actualPath, actualStdout, "utf8");

  try {
    const diffResult = runProcess("diff", [expectedStdoutPath, actualPath], null);
    if (diffResult.cannotExecute) {
      return { same: false, output: joinMessage("Cannot execute diff", diffResult.stderr) };
    }
    if (diffResult.exitCode === 0) {
      return { same: true, output: null };
    }
    if (diffResult.exitCode === 1) {
      return { same: false, output: diffResult.stdout };
    }
    return {
      same: false,
      output: joinMessage("diff failed", `${diffResult.stdout}\n${diffResult.stderr}`.trim()),
    };
  } finally {
    rmSync(tempDirectory, { recursive: true, force: true });
  }
}

function withTemporaryXmlFile(
  xmlContent: string,
  callback: (path: string) => TestCaseReport
): TestCaseReport {
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

  if (expectedStdoutPath !== null && interpreter.exitCode === 0) {
    const diff = runDiff(expectedStdoutPath, interpreter.stdout);
    if (!diff.same) {
      return new TestCaseReport(
        TestResult.INTERPRETER_RESULT_DIFFERS,
        null,
        interpreter.exitCode,
        null,
        null,
        interpreter.stdout,
        interpreter.stderr,
        diff.output
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
  const { definition } = testCase;
  const tempDirectory = mkdtempSync(join(tmpdir(), "sol26-source-"));
  const sourcePath = join(tempDirectory, testCase.source_is_xml ? "source.xml" : "source.sol26");
  writeFileSync(sourcePath, testCase.source_code, "utf8");

  try {
    if (
      definition.test_type === TestCaseType.PARSE_ONLY ||
      definition.test_type === TestCaseType.COMBINED
    ) {
      const parser = runProcess(
        toolPaths.pythonExecutable,
        [toolPaths.parserScript, sourcePath],
        null
      );
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
      sourcePath,
      definition.stdin_file,
      definition.expected_interpreter_exit_codes,
      definition.expected_stdout_file
    );
  } finally {
    rmSync(tempDirectory, { recursive: true, force: true });
  }
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
