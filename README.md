# Job Application Pipeline

Automates Stages 2-7 of your job search: normalize, dedupe, score, tailor
resume, generate cover letter, save, log. Stage 1 (collection) is split
across three sources with different levels of automation -- see below.

## Setup (one-time)

```bash
cd jobagent
pip install -r requirements.txt --break-system-packages
```

## Running it

### Option A: Arbeitnow only (fully automatic, no setup needed)
```bash
python main.py --sources arbeitnow
```

### Option B: Add LinkedIn (needs a free Apify account, ~5 min setup)
1. Sign up at https://apify.com (free tier available)
2. Get your API token: https://console.apify.com/account/integrations
3. Set it as an environment variable:
   ```bash
   export APIFY_API_TOKEN="your_token_here"
   ```
4. Run:
   ```bash
   python main.py --sources arbeitnow linkedin
   ```

**Note on LinkedIn scraping:** the Actor used here
(`worldunboxer/rapid-linkedin-scraper`) scrapes LinkedIn WITHOUT your login
cookies -- it's not tied to your personal account, so there's no risk of your
account getting flagged. Do not swap this for an Actor that asks for your
LinkedIn session.

### Option C: Add Indeed (needs a quick hand-off from Claude in chat)
The Indeed connector only exists inside a Claude chat session -- there's no
public API key for it, so it can't run standalone in this script. Workflow:

1. In a Claude chat, ask: "pull fresh Indeed postings for AI/Data/ML
   internships in Germany and save them as JSON to data/raw/indeed.json in
   this format: [{"company":..., "title":..., "location":...,
   "date_posted":..., "jd_text":..., "apply_url":...}, ...]"
2. Save that file to `data/raw/indeed.json`
3. Run:
   ```bash
   python main.py --sources arbeitnow linkedin indeed
   ```

## What happens each run

1. Collects postings from the sources you chose
2. Dedupes against everything already in `data/postings.xlsx` (safe to
   re-run daily -- won't create duplicate entries or duplicate application
   folders)
3. Scores each NEW posting: a transparent keyword-overlap percentage
   against your real skills (NOT a universal "ATS score" -- no such single
   score exists across different ATS platforms; see `pipeline/scorer.py`
   for the honest explanation)
4. Picks the best-fit resume variant: `data_engineer`, `ai_ml`, or `nlp`
5. Generates a tailored resume in `applications/Company_Role_Date/resume.docx`
   -- same approved template every time, only reordering/relabeling truthful
   content (see `config.py` -- this is the single source of truth; nothing
   gets invented)
6. Generates `cover_letter.docx` in the same folder
7. Logs everything to `data/postings.xlsx`, including the `apply_url` you'll
   use to actually submit

## What this does NOT do

- **Does not apply for you.** No auto-submit, no logging into LinkedIn/Indeed
  on your behalf. You review each package and click Apply yourself.
- **Does not invent resume content.** All tailoring is reordering/relabeling
  facts already in `config.py`. If a JD asks for something genuinely missing
  (Docker, Kubernetes, etc.), it shows up in the `gaps` column of the Excel
  sheet instead of being silently added to your resume.
- **Does not guarantee any specific "ATS score."** The `overlap_pct` column
  is an honest, transparent proxy -- not a real score from any actual ATS
  platform.

## Files

```
config.py                  <- single source of truth for all resume content
collectors/
  arbeitnow.py              <- free public API, fully automatic
  linkedin_apify.py         <- needs your own free Apify token
  indeed_loader.py          <- reads a JSON file Claude hands you in chat
pipeline/
  scorer.py                 <- honest keyword-overlap scoring + variant selection
  excel_log.py               <- dedup + tracker
resume_builder/
  build.py                  <- generates resume.docx (matches your approved template)
  cover_letter.py            <- generates cover_letter.docx
main.py                     <- orchestrates everything
data/postings.xlsx          <- your tracker (created on first run)
applications/                <- generated resume + cover letter per posting
```
