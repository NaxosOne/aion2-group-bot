# Contributing to Kisk

> 🇫🇷 Francophone ? Consultez [README.fr.md](README.fr.md) pour une présentation du projet en français.

Kisk is a community project and contributions are welcome. Whether you want to
fix a bug, improve the docs, add a translation, or build a whole new feature,
thank you for taking the time to help out.

## Before you start

If you want to work on a larger feature, please open an issue first so we can
discuss the approach before you invest time in implementing it. This avoids
duplicated effort and makes sure the change fits the direction of the project.

Small fixes (typos, obvious bugs, doc tweaks) can go straight to a pull request.

## Good areas to contribute

* 🐛 Bug fixes
* 🧪 Tests
* 📚 Documentation
* 🌍 Translations
* 🎨 Discord UX
* ⚙️ Core party logic
* 📅 Scheduling
* 👥 Legion management
* 🧠 Group formation

## Development setup

Clone the repository:

```bash
git clone https://github.com/NaxosOne/aion2-group-bot.git
cd aion2-group-bot
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate    # Linux / macOS
.venv\Scripts\activate       # Windows
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create your environment file and fill in your Discord credentials:

```bash
cp .env.example .env         # Linux / macOS
copy .env.example .env       # Windows
```

Run the bot:

```bash
python -m bot.main
```

## Running the tests

The core logic can be tested independently of Discord. Install the dev
dependencies (pytest, ruff) and run the suite:

```bash
pip install -e ".[dev]"
pytest
```

Lint your changes with ruff before pushing:

```bash
ruff check .
```

Please run the tests before opening a pull request, and add or update tests
when you change behaviour.

## Pull request checklist

1. Keep changes focused — one logical change per pull request.
2. Add or update tests where appropriate.
3. Make sure existing functionality still works.
4. Update the documentation if behaviour changes.

## Commit messages

Use conventional-style commit messages: `type: description`, where `type` is
one of:

* `feat` — a new feature
* `fix` — a bug fix
* `docs` — documentation only
* `refactor` — code change that neither fixes a bug nor adds a feature
* `test` — adding or updating tests
* `chore` — tooling, dependencies, or housekeeping
* `perf` — a performance improvement
* `ci` — continuous integration changes

Example:

```text
feat: add attendance confirmation button to events
```
