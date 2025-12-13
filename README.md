# FnO — Futures & Options Trading Helpers

FnO is a small Python project providing helper components for working with Futures & Options (FnO) trading workflows. It includes a DecisionMaker component that evaluates positions and makes trading decisions, plus API service wrappers for fetching positions and options data and unit tests for the trading logic.

> Note: This is a draft README. Adjust the example commands and environment variables below to match your repository layout and the actual class/method names in your code.

## Features
- DecisionMaker: core trading decision logic (injectable services).
- GetApiService: fetches positions and market/option data from upstream APIs.
- OptionsService: helpers for option symbol generation and related utilities.
- Unit tests covering trading logic.

## Requirements
- Python 3.9+ (or the version your project targets)
- pip
- Virtual environment tooling (venv or similar)

## Installation (local)
1. Clone the repository:
   git clone https://github.com/naveenkusakula/FnO.git
   cd FnO

2. Create and activate a virtual environment:
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell: .venv\Scripts\Activate.ps1)

3. Install dependencies:
   pip install -r requirements.txt
   (or)
   pip install .

If the repository uses pyproject.toml / poetry, use the relevant commands (poetry install, etc.).

## Configuration
The project interacts with external APIs. Provide credentials and configuration via environment variables or a config file. Use secure storage for secrets — never commit them to the repo.

Typical environment variables (example names; adapt to your code):
- FNO_API_KEY — API key for market/data provider
- FNO_API_SECRET — API secret (if required)
- FNO_BASE_URL — API base URL (optional)
- FNO_ACCOUNT_ID — trading account identifier (optional)

Example (Linux/macOS):
export FNO_API_KEY="your_api_key"
export FNO_API_SECRET="your_api_secret"

## Usage examples
Below are illustrative examples showing how to import and run the core components. Update the module and class names to match the code in this repository.

Example: simple script to run DecisionMaker (illustrative)
```python
import os
from decision_maker import DecisionMaker
from services import GetApiService, OptionsService

# Configure API services using environment variables
api_key = os.getenv("FNO_API_KEY")
api_secret = os.getenv("FNO_API_SECRET")
base_url = os.getenv("FNO_BASE_URL", "https://api.example.com")

get_api = GetApiService(api_key=api_key, api_secret=api_secret, base_url=base_url)
options_service = OptionsService(get_api)

# Inject services into the DecisionMaker
dm = DecisionMaker(get_api_service=get_api, options_service=options_service)

# Run evaluation (method name is illustrative — replace with actual API)
decisions = dm.evaluate_positions()
print("Decisions:", decisions)
```

If the project provides a runnable script (e.g., `decision_maker.py` or a CLI), run:
python decision_maker.py --config config.yaml

## Running tests
This project includes unit tests for the trading logic. To run tests:
1. Ensure dev/test dependencies are installed:
   pip install -r requirements-dev.txt

2. Run pytest:
   pytest -q

If tests use a particular pytest configuration or fixtures that require API keys or recorded responses (VCR/cassettes), set the environment variables or mocks accordingly before running tests.

## Development tips
- Formatting: use Black (black .)
- Linting: use ruff/flake8
- Type checking: use mypy if type hints are present

Suggested dev dependencies:
- black
- ruff or flake8
- pytest
- mypy (optional)

## CI
Add a GitHub Actions workflow to run tests on push/PR:
- Setup Python
- Install dependencies
- Run lint and tests

A minimal job:
- uses: actions/checkout@v4
- uses: actions/setup-python@v4
- run: pip install -r requirements.txt
- run: pytest -q

## Security and secrets
- Never commit API keys or secrets.
- Use GitHub Secrets for CI.
- Add a `.gitignore` to exclude local env files and `.venv`.

## Contributing
- Open an issue or PR with a clear description.
- Add tests for new features and bug fixes.
- Follow the project's style (formatting, typing) — consider adding a CONTRIBUTING.md later.

## License
This repository currently has no license. If you plan to share it publicly, add a LICENSE file (MIT, Apache-2.0, etc.) to clarify reuse terms.

## Contact
Repository owner: @naveenkusakula
