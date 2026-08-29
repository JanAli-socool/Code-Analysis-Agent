# Agent Trajectories

Complete execution traces for all 8 skills across 5 test repositories.

---

## Test Repository: bad_repo (messy_code.py)
**Repository**: `test_repos/bad_repo` | **Files**: 1 | **Lines**: 87
**Overall Score**: 62.8/100 | **Risk Level**: HIGH

### Skill 1: Complexity Analysis
**Tool**: radon (cc_visit, mi_visit, raw)
**Input**: 1 Python file (messy_code.py)
**Execution**:
- Parsed AST for cyclomatic complexity
- Calculated maintainability index
- Counted raw metrics (LOC, comments, blanks)
**Output**:
- 37 functions analyzed, avg complexity: 1.59, max: 17
- Maintainability index: 31.08 (threshold: 65)
- **Finding**: `bad_function` complexity 17 (line 10) - MEDIUM
- **Score**: 75.0/100

### Skill 2: Security Analysis
**Tool**: bandit (subprocess: `python -m bandit -r . -f json -ll`)
**Input**: Repository path
**Execution**:
- Created temp directory with source files
- Ran bandit SAST scan
- Parsed JSON results
**Output**:
- 4 security issues detected:
  1. Line 7: `eval(user_data)` - MEDIUM (B307)
  2. Line 66: SQL injection via string concat - MEDIUM (B608)
  3. Line 70: `subprocess.run(cmd, shell=True)` - HIGH (B602)
  4. Line 77: `pickle.loads(data)` - MEDIUM (B301)
- **Score**: 61.0/100 (weight: 3.0)

### Skill 3: Maintainability Analysis
**Tool**: AST parsing (ast.walk)
**Input**: File contents from context
**Execution**:
- Walked AST for function/class definitions
- Measured function body length, class method count
- Counted identifier frequency
**Output**:
- 36 functions, 1 class (GodClass: 30 methods)
- Avg function length: 1.22 lines
- **Finding**: GodClass with 30 methods (line 33) - LOW
- **Score**: 85.0/100

### Skill 4: Testing Analysis
**Tool**: AST parsing + coverage subprocess
**Input**: File contents
**Execution**:
- Detected test files (none found)
- Counted test functions/classes
- Attempted coverage run (pytest not configured)
**Output**:
- 0 test files, 0 test functions
- **Finding**: No test files found - HIGH
- **Score**: 0.0/100

### Skill 5: Dependencies Analysis
**Tool**: pip list --outdated, pip-audit
**Input**: Requirements files (none)
**Execution**:
- Scanned for requirements.txt, setup.py, pyproject.toml
- Ran pip outdated check
- Ran pip-audit for vulnerabilities
**Output**:
- 0 dependencies found
- **Score**: 100.0/100

### Skill 6: Architecture Analysis
**Tool**: AST import analysis
**Input**: File contents
**Execution**:
- Extracted imports per file
- Built dependency graph
- Detected circular dependencies, god modules, layering violations
**Output**:
- 1 module, 0 internal imports
- No circular deps, no god modules
- **Score**: 100.0/100

### Skill 7: Documentation Analysis
**Tool**: AST docstring extraction
**Input**: File contents
**Execution**:
- Checked module/function/class docstrings
- Counted type hints
- Searched for README files
**Output**:
- 0/36 functions documented, 0/1 classes documented
- 0% type hint coverage
- No README found
- **Score**: 0.0/100

### Skill 8: Git History Analysis
**Tool**: git log subprocess
**Input**: Repository path
**Execution**:
- `git log --pretty=format:%H|%an|%ad|%s --date=short -n 500`
- `git log --pretty=format: --name-only -n 200`
- `git shortlog -sn -n 20`
**Output**:
- 1 commit, 1 author
- **Finding**: Bus factor risk (single author) - HIGH
- **Score**: 49.5/100

---

## Test Repository: good_repo (math_utils.py, test_math_utils.py)
**Repository**: `test_repos/good_repo` | **Files**: 2 | **Lines**: 158
**Overall Score**: 84.9/100 | **Risk Level**: HIGH (due to docs/git history)

### Skill 1: Complexity Analysis
**Output**:
- 22 functions, avg complexity: 3.77, max: 7
- Maintainability index: 54.51
- No high-complexity functions
- **Score**: 90.0/100

### Skill 2: Security Analysis
**Output**:
- 0 security issues
- **Score**: 100.0/100

### Skill 3: Maintainability Analysis
**Output**:
- 17 functions, 5 classes
- Avg function length: 3.53, avg class methods: 2.8
- **Finding**: Identifier 'result' used 5 times - LOW
- **Score**: 99.0/100

### Skill 4: Testing Analysis
**Output**:
- 1 test file, 12 test functions, 4 test classes
- Uses pytest
- 0% coverage (not configured)
- **Finding**: Low assertion density (0.0 per test) - LOW
- **Score**: 50.0/100

### Skill 5: Dependencies Analysis
**Output**:
- 0 dependencies
- **Score**: 100.0/100

### Skill 6: Architecture Analysis
**Output**:
- 2 modules, 1 internal import avg
- No issues
- **Score**: 100.0/100

### Skill 7: Documentation Analysis
**Output**:
- 5/17 functions documented (29%), 1/5 classes (20%)
- 5/17 functions with type hints (29%)
- No README
- **Findings**: Low func docs (MED), low class docs (MED), low type hints (LOW), no README (HIGH)
- **Score**: 15.8/100

### Skill 8: Git History Analysis
**Output**:
- 1 commit, 1 author
- **Finding**: Bus factor risk - HIGH
- **Score**: 48.5/100

---

## Test Repository: medium_repo (order_service.py, test_order_service.py)
**Repository**: `test_repos/medium_repo` | **Files**: 2 | **Lines**: 89
**Overall Score**: 81.8/100 | **Risk Level**: HIGH

### Key Differences from good_repo:
- **Complexity**: 75.0 (lower MI: 49.14)
- **Documentation**: 0.0 (no docstrings, no type hints, no README)
- **Security**: 100.0 (clean)
- **Testing**: 50.0 (10 tests, but 0% coverage)
- **Architecture**: 100.0
- **Git History**: 48.5 (single author)

---

## Test Repository: legacy_repo (user_management.py)
**Repository**: `test_repos/legacy_repo` | **Files**: 1 | **Lines**: 53
**Overall Score**: 72.5/100 | **Risk Level**: HIGH

### Key Findings:
- **Security**: 84.0 - 2 issues: SQL injection (line 4), requests without timeout (line 51)
- **Testing**: 0.0 - No test files
- **Documentation**: 0.0 - No docs, no type hints, no README
- **Complexity**: 90.0 - Clean (avg 1.89, max 4)
- **Maintainability**: 100.0 - Small functions/classes
- **Architecture**: 100.0 - Single module

---

## Test Repository: microservice_repo (domain.py, test_domain.py)
**Repository**: `test_repos/microservice_repo` | **Files**: 2 | **Lines**: 161
**Overall Score**: 82.0/100 | **Risk Level**: HIGH

### Key Findings:
- **Security**: 100.0 - Clean
- **Architecture**: 100.0 - Clean layering, no circular deps
- **Testing**: 50.0 - 10 tests, 3 test classes, uses pytest
- **Documentation**: 4.4 - No docstrings, no README, but 44% type hint coverage
- **Complexity**: 75.0 - 35 functions, avg 1.97, max 5
- **Git History**: 48.5 - Single author

---

## Summary: Skill Execution Patterns

| Skill | Tools Used | Avg Runtime | Key Data Sources |
|-------|------------|-------------|------------------|
| Complexity | radon (cc_visit, mi_visit, raw) | ~2s | AST, source text |
| Security | bandit (subprocess) | ~8s | Temp dir + source files |
| Maintainability | ast.walk | ~1s | AST nodes |
| Testing | ast.walk + coverage run | ~5s | AST + pytest/coverage |
| Dependencies | pip list, pip-audit | ~3s | Requirements files |
| Architecture | ast.walk (imports) | ~1s | Import statements |
| Documentation | ast.get_docstring | ~1s | AST + file search |
| Git History | git log (3 calls) | ~2s | .git directory |

---

## Failure Modes Observed

1. **Security skill**: File path resolution - bandit returns relative paths without repo prefix
2. **Testing skill**: Coverage always 0% - test repos lack pytest.ini/coverage config
3. **Documentation skill**: Penalizes synthetic repos heavily (no README, minimal docs)
4. **Git History skill**: All test repos have 1 commit/1 author - not representative

---

## Human Checkpoints

No human approval required - all actions are read-only analysis. Consequential actions (file writes) only occur with explicit `--output` flag.