# OTrace - Defensive Digital-Footprint Tool

OTrace is a defensive OSINT digital-footprint tool created for cybersecurity self-assessment and identity resolution analysis. It enables users to type query attributes into **ONE smart search box** (e.g. `"Arun Nair, NIT Calicut, CSE 2024, Infosys"`), aggregates public profile data across internet sources via official APIs, computes identity confidence using a calibrated machine learning classifier, synthesizes exposure risk, and provides actionable privacy remediation steps.

> **Framing:** *"See what the internet can link to you."*  
> Used strictly on yourself or on consenting individuals only.

---

## 🌟 Key Features

1. **Single Smart Search Box**: Free text parsing supporting commas, key-value labels (`name: ..., college: ..., city: ...`), and space-separated queries with automatic college alias recognition (`NITC` = `NIT Calicut`).
2. **Multi-Source Data Collectors**:
   - GitHub REST API
   - Semantic Scholar Graph API
   - ORCID Researcher API
   - Social Media & Open Web Profile Search via **Brave Search API** or **Tavily API**
3. **Calibrated Machine Learning Matching Engine**:
   - Jaro-Winkler string similarity & token sort distance with transliteration normalizations (`Nair`/`Nayar`, `Mohammed`/`Muhammed`).
   - Institution alias matching with generic word stoplists and **HARD MISMATCH** enforcement (`NIT Calicut` vs `MIT` = 0 score).
   - `LogisticRegression` + `CalibratedClassifierCV` (Isotonic regression) saved to `models/model.joblib`.
   - Optional Anthropic Claude LLM Judge for top-5 candidates with silent fallback.
4. **Interactive Dashboard**:
   - **Results View**: Grouped into *"Most likely the same person"* and *"Other possible matches"* with score evidence expanders.
   - **Exposure Report**: Radial exposure score gauge (0-100), attacker intelligence analysis, and prioritized privacy remediation guide.
   - **Connection Graph**: SVG node graph visualizing entity links and handle reuse.
   - **Interactive Feedback**: *"This is them"* / *"Not them"* labels saved to SQLite for model retraining.
   - **Privacy History**: Browser LocalStorage history (never sent to server).
   - **PDF Report Export**: Print stylesheet for clean A4 PDF exports.

---

## 🔒 Ethics & Privacy Guardrails

- **Strict Consent Enforcement**: Both UI and API block searches unless the consent gate is checked.
- **Public Data & Official APIs Only**: Zero web scraping of logged-in social media pages, zero CAPTCHA bypassing, zero credential harvesting.
- **Data Minimisation & Hashed Audit Logging**: Search logs store **SHA256 hashes** of searched names only. No raw personal query text is retained beyond ephemeral cache with TTL.
- **India DPDP Act 2023 & GDPR Compliance**: Provides a *"Delete My Data"* action that purges SQLite cache, audit logs, and feedback labels.
- **Educational Framing**: Every search result explicitly highlights: *"Confidence is an estimate based on public evidence, not proof of identity."*

---

## 🚀 Quick Start & Setup

### Prerequisites
- Python 3.10+
- `pip` & `venv`

### Option 1: Unix / macOS (`run.sh`)

```bash
chmod +x run.sh
./run.sh
```

This will automatically create a virtualenv, install dependencies, train the calibrated model, run pytest unit tests, execute benchmark evaluations, and launch the server at `http://127.0.0.1:8000`.

### Option 2: Windows PowerShell Setup

```powershell
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Train calibrated model
python -m eval.train

# 4. Run tests
pytest -v

# 5. Run evaluation benchmark
python -m eval.evaluate

# 6. Start OTrace Web Server
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## 🔑 Configuring Search & LLM API Keys

Create a `.env` file in the root directory:

```ini
# Social Media & Open Web Profile Search API (Choose Brave or Tavily)
# Get a free Brave Search API key at: https://brave.com/search/api/
BRAVE_API_KEY=your_brave_api_key_here

# OR Tavily Search API key at: https://tavily.com/
TAVILY_API_KEY=

# Optional Anthropic API Key for top-5 LLM Judge verification
ANTHROPIC_API_KEY=
```

*Note: If no search key is configured, OTrace still functions fully using GitHub, Semantic Scholar, and ORCID APIs while displaying an informative banner.*

---

## 📊 Evaluation & Dataset Retraining

### Running Synthetic Evaluation & Benchmark
```bash
python -m eval.evaluate
```
Generates `eval/results.json` and `eval/calibration.png`.

### Measuring Live Collector Coverage
```bash
python -m eval.build_dataset
```
Reads `eval/volunteers.csv` and outputs profile discovery coverage rate.

### Exporting Volunteer Feedback Labels
Click **Export Labelled Dataset** in the web interface or call `GET /feedback/export` to export real user labels in JSON format for training.

---

## ⚠️ Limitations

1. **Private Accounts Are Invisible**: OTrace only analyzes open public web data and public search engine indices. Private Instagram or locked Twitter profiles cannot be inspected.
2. **Ambiguity of Common Names**: Common names (e.g. "John Smith") without institution or city keywords yield low confidence scores by design.
3. **Probabilistic Confidence**: Confidence scores reflect statistical feature similarity, not legal proof of personal identity.
