# Solution Video Script (≤5 minutes)

## Target: 4:30 minutes | Record at 1080p, narrate clearly

---

### 0:00-0:30 | Problem & User (30s)
**[Screen: Title slide - "Code Analysis Agent for Technical Due Diligence"]**

**Narration**: "Engineers and investors evaluating code repositories for acquisition face a critical bottleneck: manual code review takes days, is inconsistent across reviewers, and misses security vulnerabilities, architecture decay, and test gaps. There's no repeatable, automated way to produce a defensible quality score."

**[Screen: Show the 4 questions from hackathon]**
- Who has this problem? → Technical due diligence teams, engineering leads, investors
- What bottleneck? → No automated, multi-dimensional quality assessment
- Does the agent solve it? → Yes, 8 skills in minutes with evidence
- Can another reproduce? → Yes, full guide with 5 test repos

---

### 0:30-1:15 | Baseline Demo (45s)
**[Screen: Terminal - run baseline on bad_repo]**

```bash
python baseline/analyze.py test_repos/bad_repo
```

**[Show output: score 90/100]**

**Narration**: "The baseline uses only radon for cyclomatic complexity and comment ratio. It gives bad_repo a 90/100 - completely missing the eval, SQL injection, shell=True, pickle vulnerabilities, GodClass, and zero tests."

**[Screen: Run baseline on good_repo - also 90/100]**

```bash
python baseline/analyze.py test_repos/good_repo
```

**Narration**: "Same score for good_repo. Zero discrimination. The baseline is useless for real decisions."

---

### 1:15-2:30 | Advanced Solution Walkthrough (75s)
**[Screen: Terminal - run advanced on bad_repo]**

```bash
python -m advanced.orchestrator test_repos/bad_repo
```

**[Show human-readable output with category scores]**

**Narration**: "The advanced orchestrator runs 8 specialized skills with calibrated weights. Security (weight 3.0) catches 4 vulnerabilities. Testing (weight 2.0) finds zero tests. Complexity (weight 2.0) flags the 17-complexity function. Overall: 62.8/100, HIGH risk."

**[Screen: Run advanced on good_repo]**

```bash
python -m advanced.orchestrator test_repos/good_repo
```

**[Show output: 84.9/100, strengths in security/complexity/architecture]**

**Narration**: "good_repo scores 84.9 - strong security (100), complexity (90), architecture (100). Weaknesses are only documentation and git history - artifacts of being a synthetic test repo."

**[Screen: Show JSON output structure]**

```bash
python -m advanced.orchestrator test_repos/bad_repo --json | head -50
```

**Narration**: "Every finding includes file, line number, severity, evidence, and remediation link. Machine-readable for CI/CD integration."

---

### 2:30-3:30 | Architecture & Design Choices (60s)
**[Screen: Show project structure / skills diagram]**

**Narration**: "Each skill is a focused module using the right tool: radon for complexity, bandit for security, AST for maintainability/architecture/documentation, git CLI for history, pip-audit for dependencies. They share a context object with file contents and repo path."

**[Screen: Show weight configuration in orchestrator]**

**Narration**: "Critical insight: equal weights failed. Weight calibration was the single biggest improvement. Security=3.0, Testing=2.0, Architecture=2.0, Complexity=2.0. Docs/Git=0.5 because synthetic repos lack them. This creates 22-point discrimination vs 0 for baseline."

---

### 3:30-4:15 | Changelog & Key Insights (45s)
**[Screen: Show CHANGELOG.md highlights]**

**Narration**: "Nine iterations. Key lessons:
1. Weight calibration > more skills. Three skills with right weights beat eight with equal weights.
2. Synthetic test repos penalize documentation/git history unfairly - in production these work well.
3. Evidence-backed findings (file, line, code snippet, CWE link) make output actionable for human reviewers.
4. The 'agentic' part isn't agent count - it's deliberate design of what each skill measures and how they combine."

---

### 4:15-4:30 | Evaluation Results & Close (15s)
**[Screen: Show evaluation summary table]**

| Repo | Baseline | Advanced | Discrimination |
|------|----------|----------|----------------|
| good_repo | 90 | 84.9 | ✓ |
| microservice_repo | 90 | 82.0 | ✓ |
| bad_repo | 90 | 62.8 | ✓ |

**Narration**: "Advanced discriminates quality across 5 diverse repos. Baseline fails completely. Full reproduction guide in README. Code at github.com/yourrepo/code_analysis_agent. Thanks!"

---

## Recording Tips

1. **Prepare terminal**: Clean prompt, large font (16pt), dark theme
2. **Pre-run commands**: Have them ready in history (up-arrow)
3. **Zoom on output**: Use terminal zoom (Ctrl++) for JSON/category scores
4. **Cut silence**: Edit out command typing time
5. **Add captions**: Key metrics (weights, scores, findings)
6. **Background music**: Optional, low volume

---

## Alternative: If No Time to Record

Create a 5-slide presentation video:
1. Problem & User (static slide)
2. Baseline Failure (screenshot)
3. Advanced Success (screenshot)
4. Architecture & Weights (diagram)
5. Results & Link (table + URL)

Record voiceover over slides - faster to produce.