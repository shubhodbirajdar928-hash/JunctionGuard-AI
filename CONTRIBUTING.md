# 🤝 Contributing to JunctionGuard AI

First off — **thank you for taking the time to contribute!** 🎉

JunctionGuard AI is an open-source hackathon project aimed at making Indian roads safer through AI-powered junction risk analysis. All contributions — from bug fixes to new features to documentation — are warmly welcome.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Branch & Commit Conventions](#branch--commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)
- [Project Structure](#project-structure)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](./CODE_OF_CONDUCT.md). Please read it before contributing.

---

## How Can I Contribute?

### 🐛 Reporting Bugs
- Check if the bug has already been reported in [GitHub Issues](../../issues).
- If not, open a **new issue** using the Bug Report template.
- Include: OS, Python version, steps to reproduce, expected vs. actual behavior, and any error logs.

### 💡 Suggesting Features
- Open a **Feature Request** issue with a clear description of the problem it solves.
- Explain the use case and why it benefits JunctionGuard AI users.

### 📝 Improving Documentation
- Fix typos, clarify explanations, or add missing documentation.
- Documentation PRs are just as valuable as code PRs!

### 🔧 Writing Code
- Pick an issue labeled `good first issue` or `help wanted`.
- Comment on the issue to let others know you're working on it.
- Fork → Branch → Code → Test → PR.

### 🧪 Writing Tests
- Add unit tests for untested modules in the `tests/` directory.
- Use `pytest` as the testing framework.

---

## Development Setup

### 1. Fork & Clone

```bash
git clone https://github.com/YOUR_USERNAME/JunctionGuard-AI.git
cd JunctionGuard-AI
```

### 2. Set Up Virtual Environment

```bash
python -m venv venv
source venv/bin/activate       # macOS/Linux
# venv\Scripts\activate        # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env           # Create your local .env
# Edit .env with your Supabase keys (optional)
```

### 5. Run the App Locally

```bash
streamlit run app.py
```

### 6. Run Tests

```bash
pytest tests/ -v
```

---

## Branch & Commit Conventions

### Branch Naming

```
feature/short-description       # New features
fix/short-description           # Bug fixes
docs/short-description          # Documentation only
refactor/short-description      # Code refactoring
test/short-description          # Adding/fixing tests
chore/short-description         # Build, CI, tooling changes
```

**Examples:**
```
feature/add-rtsp-stream-support
fix/gps-query-params-crash
docs/update-architecture-diagram
```

### Commit Messages

Follow the **Conventional Commits** specification:

```
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

| Type | When to Use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Formatting, no logic change |
| `refactor` | Code restructure, no behavior change |
| `test` | Adding or updating tests |
| `chore` | Tooling, dependencies, CI |
| `perf` | Performance improvement |

**Examples:**
```
feat(vision): add RTSP live stream support via yt-dlp
fix(geo): handle NaN coordinates in haversine calculation
docs(readme): add deployment instructions for Docker
test(risk_engine): add unit tests for 5-factor score normalization
```

---

## Pull Request Process

1. **Ensure your branch is up to date** with `main`:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all tests** before submitting:
   ```bash
   pytest tests/ -v
   ```

3. **Open a Pull Request** against the `main` branch with:
   - A clear title following commit conventions
   - Description of what changed and why
   - Reference to any related issue (`Closes #123`)
   - Screenshots/recordings for UI changes

4. **PR Review:**
   - At least **1 team member approval** is required before merging.
   - Address all review comments before requesting re-review.
   - Keep PRs **small and focused** — one feature or fix per PR.

5. **Do not merge your own PR** — have a teammate review and merge it.

---

## Style Guidelines

### Python

- Follow **PEP 8** style guidelines.
- Use **type hints** for all function signatures.
- Write **docstrings** for all public classes and functions (Google-style preferred).
- Maximum line length: **100 characters**.

```python
def compute_risk_score(
    historical_score: float,
    traffic_density: float,
    conflict_index: float,
    pedestrian_score: float,
    citizen_score: float,
) -> float:
    """
    Computes the final weighted risk score for a junction.

    Args:
        historical_score: Normalized 0–100 score from Kaggle accident data.
        traffic_density: Normalized 0–100 score from YOLO vehicle counts.
        conflict_index: Normalized 0–100 score from near-miss detection.
        pedestrian_score: Normalized 0–100 pedestrian activity score.
        citizen_score: Normalized 0–100 citizen report severity score.

    Returns:
        Weighted composite risk score in range [0, 100].
    """
    ...
```

### Streamlit Components

- Keep UI logic in `app/components.py` — do not embed raw HTML in `app.py` unless necessary.
- Use `st.session_state` consistently; avoid global variables.
- Prefix all custom CSS class names with `jg-` to avoid conflicts.

### SQL / Database

- Use parameterized queries — **never** string-formatted SQL (SQL injection risk).
- Always close connections in `finally` blocks or use context managers.

---

## Project Structure

Key areas for contribution:

```
src/analytics/     ← Risk scoring, data loading, indicator computation
src/vision/        ← YOLOv8, video processing, stream handling
src/               ← Database, geocoding, Supabase client
app/               ← Streamlit UI components and pages
tests/             ← Unit and integration tests
data/              ← Dataset, citizen reports, detection outputs
```

---

## Reporting Bugs

Open an issue with the following template:

```markdown
**Bug Description**
A clear and concise description of what the bug is.

**Steps to Reproduce**
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Environment**
- OS: [e.g. macOS 14, Ubuntu 22.04]
- Python version: [e.g. 3.11.2]
- Browser (if UI bug): [e.g. Chrome 120]

**Logs / Screenshots**
Paste any relevant error output or attach screenshots.
```

---

## Suggesting Features

Open an issue with:

```markdown
**Feature Request**

**Problem it solves:**
[What pain point or gap does this address?]

**Proposed solution:**
[How should this work?]

**Alternatives considered:**
[Other approaches you thought of]

**Additional context:**
[Mockups, diagrams, references]
```

---

## 🙏 Thank You

Every contribution matters — whether it's fixing a typo or building a major feature. Together we can make India's roads safer!

*JunctionGuard AI Team*
