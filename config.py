"""
Master resume content bank.

RULE: This file is the single source of truth for everything true about
Srikar's resume. The tailoring pipeline is only allowed to REORDER and
RELABEL content that already exists here. It must never invent a skill,
number, or achievement that isn't in this file.

-------------------------------------------------------------------------
BEFORE YOUR NEXT RUN -- do these three things:

  1. Search this file for "FILL:" and replace every marker with a real
     number. build_resume() will refuse to run while any remain.
     If you genuinely don't have a figure, use a defensible estimate with
     "~" -- that beats the word "measurably" every time.

  2. Verify VERIFY_WORK_AUTH below with your university's international
     office. The Pflichtpraktikum exemption is the difference between
     looking restricted and looking hireable.

  3. Confirm every URL in CONTACT and PROJECTS loads in a private browser
     window. skilsync.srikarkodi.dev did not respond when last checked,
     and the domain spelling ("skilsync") doesn't match the project name
     ("SkillSync"). A dead link undercuts your whole "I ship live
     products" pitch.
-------------------------------------------------------------------------
"""

# Sentinel for facts only you have. validate() blocks the build if any survive.
FILL = "FILL:"


CONTACT = {
    "name": "SRIKAR KODI",
    "location": "Berlin, Germany",
    "phone": "+49 163 421 8928",
    "email": "kodisrikar@gmail.com",
    "site": "https://srikarkodi.dev",
    "site_label": "srikarkodi.dev",
    "linkedin": "https://linkedin.com/in/srikar-kodi-046a631b2",
    "linkedin_label": "linkedin.com/in/srikar-kodi-046a631b2",
    "github": "https://github.com/Namidok",
    "github_label": "github.com/Namidok",
}


# ---------------------------------------------------------------------------
# WORK AUTHORIZATION
#
# The old line advertised a 140-day cap and a visa extension "in process".
# Both worked against you: the cap generally does NOT apply to a
# Pflichtpraktikum that is a required part of your degree, and "in process"
# plants doubt about whether you can start at all.
#
# VERIFY the exemption with your international office, then set
# VERIFY_WORK_AUTH = True to switch to the stronger line.
# Leaving it False keeps a neutral phrasing that still avoids "in process".
# ---------------------------------------------------------------------------
VERIFY_WORK_AUTH = False

WORK_AUTH_CONFIRMED = (
    "Work Authorization: German student residence permit (\u00a716b AufenthG). "
    "This is a mandatory internship (Pflichtpraktikum) required by my degree "
    "\u2014 it does not count against the student work-day limit and needs no "
    "separate work permit."
)

WORK_AUTH_NEUTRAL = (
    "Work Authorization: German student residence permit (\u00a716b AufenthG) "
    "\u2014 eligible to complete a mandatory internship (Pflichtpraktikum) as a "
    "required part of my MSc programme."
)

WORK_AUTH = WORK_AUTH_CONFIRMED if VERIFY_WORK_AUTH else WORK_AUTH_NEUTRAL


# It is now August 2026 -- "available from August 2026" reads as a future
# date to a skimming recruiter. Say "immediately".
AVAILABILITY = "available immediately for 5\u20136 months (per programme requirement)"


# ---------------------------------------------------------------------------
# SPOKEN LANGUAGES -- deliberately NOT in SKILLS.
#
# When they lived in SKILLS, build.py's JD-relevance sort could promote
# "Languages (spoken)" to the #2 slot on an AI Scientist application,
# because a JD asking for German scored hits on english/german/language.
# Keeping them separate makes that structurally impossible.
# ---------------------------------------------------------------------------
SPOKEN_LANGUAGES = "English (Fluent), German (A2, actively progressing to B1)"


SKILLS = {
    "ai_ml": {
        "label": "AI/ML & NLP",
        # "(fundamentals)" removed from PyTorch. You were the only candidate
        # in the pile qualifying downward. Be ready to back it up in interview.
        "items": "PyTorch, spaCy (NLP), sentence-transformers / FAISS "
                 "(embeddings & semantic search), Retrieval-Augmented Generation (RAG), "
                 "LLM integration (Groq / Llama 3.3), ChromaDB",
        "keywords": ["pytorch", "spacy", "nlp", "faiss", "sentence-transformers", "rag",
                     "retrieval augmented generation", "llm", "groq", "llama", "chromadb",
                     "embeddings", "semantic search", "generative ai", "genai"],
    },
    "data_eng": {
        "label": "Data Engineering",
        "items": "Pandas, NumPy, PySpark, ETL pipeline design, data validation & quality gates, "
                 "star-schema design, PostgreSQL, SQLite",
        "keywords": ["pandas", "numpy", "pyspark", "etl", "data pipeline", "data validation",
                     "star schema", "postgresql", "postgres", "sqlite", "data engineering",
                     "data warehouse", "sql"],
    },
    "backend": {
        "label": "Backend",
        "items": "FastAPI, Flask, Django, Node.js, REST APIs",
        "keywords": ["fastapi", "flask", "django", "node.js", "nodejs", "rest api", "backend"],
    },
    "frontend": {
        "label": "Frontend",
        "items": "React.js, Next.js, HTML5, CSS3",
        "keywords": ["react", "next.js", "nextjs", "html", "css", "frontend"],
    },
    "cloud": {
        "label": "Cloud & Infra",
        "items": "AWS (EC2, S3, IAM), Linux, Nginx, systemd, Git, GitHub",
        "keywords": ["aws", "ec2", "s3", "iam", "linux", "nginx", "systemd", "git", "github"],
    },
    "qa": {
        "label": "Testing & QA",
        "items": "Test planning, manual test-case design, defect tracking",
        "keywords": ["testing", "qa", "test case", "defect tracking", "quality assurance"],
    },
}


# ---------------------------------------------------------------------------
# KEYWORD DISPLAY NAMES
#
# cover_letter._jd_line() was printing raw lowercase tokens straight into
# the letter ("aws, english, german, git"). Anything not listed here should
# be title-cased by the caller.
# ---------------------------------------------------------------------------
KEYWORD_DISPLAY = {
    "pytorch": "PyTorch", "spacy": "spaCy", "nlp": "NLP", "faiss": "FAISS",
    "sentence-transformers": "sentence-transformers", "rag": "RAG",
    "retrieval augmented generation": "Retrieval-Augmented Generation",
    "llm": "LLMs", "groq": "Groq", "llama": "Llama", "chromadb": "ChromaDB",
    "embeddings": "embeddings", "semantic search": "semantic search",
    "generative ai": "generative AI", "genai": "GenAI",
    "pandas": "Pandas", "numpy": "NumPy", "pyspark": "PySpark", "etl": "ETL",
    "data pipeline": "data pipelines", "data validation": "data validation",
    "star schema": "star-schema design", "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL", "sqlite": "SQLite",
    "data engineering": "data engineering", "data warehouse": "data warehousing",
    "sql": "SQL", "fastapi": "FastAPI", "flask": "Flask", "django": "Django",
    "node.js": "Node.js", "nodejs": "Node.js", "rest api": "REST APIs",
    "backend": "backend development", "react": "React", "next.js": "Next.js",
    "nextjs": "Next.js", "html": "HTML5", "css": "CSS3",
    "frontend": "frontend development", "aws": "AWS", "ec2": "EC2", "s3": "S3",
    "iam": "IAM", "linux": "Linux", "nginx": "Nginx", "systemd": "systemd",
    "git": "Git", "github": "GitHub", "testing": "testing",
    "qa": "QA", "test case": "test design", "defect tracking": "defect tracking",
    "quality assurance": "quality assurance",
}

# Never let these drive a "your posting highlights..." line even if matched.
# They describe you, not a technology the employer is hiring for.
NEVER_HIGHLIGHT = {"english", "german", "language", "languages", "git", "github", "html", "css"}


EXPERIENCE = [
    {
        "title": "Application Developer",
        "org": "Vavili Technologies",
        "location": "Hyderabad, India",
        "dates": "May 2023 \u2013 Aug 2025",
        "bullets": [
            # The attendance-tool bullet was cut: lowest signal for AI/ML roles
            # and it cost you a line. Re-add only if you need to fill space.

            # NOTE: your draft said "LLM-based intent recognition". Your skills
            # section lists spaCy, and the original bullet said spaCy. If the
            # chatbot genuinely used an LLM for intent classification, swap
            # "(Python, spaCy)" for "(Python, LLM-based intent recognition)".
            # If it was spaCy rules/classification, leave this as-is -- an
            # interviewer WILL ask which model and how you evaluated it.
            "Built an NLP-powered customer support chatbot (Python, spaCy) that "
            "autonomously resolved ~72% of customer queries, cutting average response "
            "time from ~5 minutes to under 10 seconds.",

            # NOTE: your draft called this "AI-powered" and said it automated
            # "content generation". The original said it generated multi-language
            # labels. Kept to the narrower, defensible claim -- add "AI-powered"
            # back only if a model was actually in the loop.
            "Automated multi-language content-label generation across the platform's 15 "
            "supported languages via a Python ETL pipeline, cutting manual localisation "
            "effort by ~90% (from ~30 hours to under 3 hours per release).",

            "Built and optimised responsive full-stack features (React, Node.js, Flask) "
            "for templeswiki.com, serving 40,000+ monthly users \u2014 improving page-load "
            "time from 3.8s to 1.6s and reaching a 96+ Lighthouse performance score.",

            "Led QA across 18+ production releases, authoring a structured test plan and "
            "full test-case suite that reduced post-release defects by 55%.",
        ],
    },
    {
        "title": "Trainee Software Engineer",
        "org": "ValueLabs",
        "location": "Hyderabad, India",
        "dates": "Jan 2022 \u2013 Feb 2023",
        "bullets": [
            "Debugged and performance-optimised 12+ application modules alongside "
            "cross-functional teams, accelerating root-cause analysis and improving "
            "overall product stability.",

            # NOTE: your draft said "manual and automated test plans". Every other
            # document you have -- the original bullet and your skills section
            # ("manual test-case design") -- says manual only. Left as manual.
            # If you did write automated tests, say so AND name the framework
            # (Selenium? pytest?), because that's the immediate follow-up question.
            "Authored and executed detailed manual test plans covering 40+ core "
            "functionalities, sustaining regression coverage and release quality across "
            "Agile sprints.",
        ],
    },
]


CREDITLENS_BULLETS = {
    "etl": "Built an end-to-end private credit portfolio monitoring tool that ingests "
           "inconsistently formatted GP quarterly reports (PDFs and CSVs with German date "
           "conventions, comma decimals, unit errors, and duplicates) through a Python ETL "
           "pipeline with a validation gate that repairs fixable issues and quarantines "
           "unfixable ones with plain-language reasons.",
    "schema": "Designed a SQLite schema with a funds/valuations star schema and window-function "
              "views (ROW_NUMBER for latest valuations, LAG for quarter-on-quarter comparison) "
              "that ports directly to production RDBMS environments.",
    "watchlist": "Implemented an automatic watchlist that flags the classic credit deterioration "
                 "pattern \u2014 rising leverage alongside falling coverage \u2014 demonstrated with a "
                 "planted scenario where fund F003 breaches its 5.5x covenant across 4 quarters.",
    "rag": "Built a RAG layer using sentence-transformers, ChromaDB, and Groq (Llama 3.3) that "
           "answers natural-language questions about GP PDF documents with cited sources and "
           "refuses to hallucinate facts not in context.",
    "deploy": "Rebuilt from a Streamlit prototype into a production Next.js + FastAPI "
              "application deployed on AWS EC2 (Linux) with an Nginx reverse proxy and systemd "
              "process management.",
}


PROJECTS = {
    "creditlens": {
        "name": "CreditLens \u2014 Private Credit Portfolio Monitor",
        "stack": "Python \u00b7 FastAPI \u00b7 Next.js \u00b7 SQLite \u00b7 ChromaDB \u00b7 Groq \u00b7 AWS EC2",
        "links": [("creditlens.srikarkodi.dev", "https://creditlens.srikarkodi.dev"),
                  ("github.com/Namidok/CreditLens", "https://github.com/Namidok/CreditLens")],
        "bullets_bank": CREDITLENS_BULLETS,
    },
    "skillsync": {
        "name": "SkillSync \u2014 Semantic Skill-Matching Engine",
        "stack": "React, FastAPI, spaCy (NLP), sentence-transformers, Python",
        # NOTE: this URL did not respond when last checked, and the domain spells
        # "skilsync" while the project is "SkillSync". Fix or remove before sending.
        "links": [("skilsync.srikarkodi.dev", "https://skilsync.srikarkodi.dev")],
        "bullets": [
            "Built and deployed a full-stack tool that parses a job description, extracts "
            "required skills via NLP, and matches them against a candidate profile using "
            "semantic similarity search to surface skill gaps.",
        ],
    },
    "covercraft": {
        "name": "CoverCraft \u2014 AI Cover-Letter Generator",
        "stack": "React, FastAPI, LLM API, Python",
        "links": [("covercraft.srikarkodi.dev", "https://covercraft.srikarkodi.dev")],
        "bullets": [
            "Developed and deployed an LLM-powered cover-letter generator that tailors output "
            "to a specific job description and the user's experience, exposed through a "
            "FastAPI backend and React frontend.",
        ],
    },
}

# Three of your four projects (SkillSync, CoverCraft, JobMan) solve your own job
# search. That reads as a narrow portfolio when submitted AS a job application.
# CreditLens is your differentiator -- it stays first in every variant below.
# Consider swapping CoverCraft for something in a different domain later.


EDUCATION = [
    {
        "degree": "MSc Computer Science \u2014 Big Data & Artificial Intelligence",
        # Start date added. Without it there was an unexplained 12-month gap
        # between Aug 2025 (Vavili) and today.
        "dates": "Sep 2025 \u2013 Expected 2027",
        "detail": "SRH University of Applied Sciences, Berlin \u00b7 Mandatory internship "
                  "(Pflichtpraktikum) required as part of programme",
    },
    {
        "degree": "B.Tech Electronics & Communication Engineering",
        "dates": "2016 \u2013 2020",
        "detail": "MVGR College of Engineering, India",
    },
]


# ---------------------------------------------------------------------------
# VARIANTS
#
# Two changes from the old version:
#
#  1. `summary` now leads with the Pflichtpraktikum ask, not "3 years of
#     production experience". You were opening every application by
#     positioning yourself as a mid-level engineer applying to an intern req.
#     The experience is still there -- it's now support, not the headline.
#
#  2. `letter_intro` is NEW. cover_letter.py used to paste `summary` verbatim
#     into the letter, producing a headless fragment:
#         "I'm writing to apply for X. AI/ML & Data Engineer with 3 years..."
#     Resume-speak and letter-prose are different registers. Use
#     letter_intro in the letter; use summary on the resume.
# ---------------------------------------------------------------------------
VARIANTS = {
    "data_engineer": {
        "title_line": "Data Engineering \u00b7 Pflichtpraktikum Candidate \u00b7 MSc Big Data & AI",
        "summary": (
            "MSc Computer Science student (Big Data & AI, Berlin) seeking a mandatory "
            "internship (Pflichtpraktikum) in Data Engineering, "
            f"{AVAILABILITY}. Backed by 3 years of professional experience building Python "
            "ETL pipelines, data validation systems, and schema design, alongside full-stack "
            "delivery (React, FastAPI, Node.js). Ships and self-hosts live products, "
            "including CreditLens, a portfolio-monitoring tool with an automated "
            f"data-validation pipeline and star-schema design. {SPOKEN_LANGUAGES}."
        ),
        "letter_intro": (
            "I am an MSc Computer Science student (Big Data & AI) in Berlin, looking for a "
            "mandatory internship (Pflichtpraktikum) in data engineering. Before starting my "
            "Master's I spent three years building production Python ETL pipelines, data "
            "validation systems, and full-stack features, and I have continued shipping and "
            "self-hosting my own projects alongside my studies."
        ),
        "skill_order": ["data_eng", "ai_ml", "backend", "frontend", "cloud", "qa"],
        "creditlens_order": ["etl", "schema", "deploy", "watchlist", "rag"],
        "keywords": SKILLS["data_eng"]["keywords"],
    },
    "ai_ml": {
        "title_line": "AI/ML Engineering \u00b7 Pflichtpraktikum Candidate \u00b7 MSc Big Data & AI",
        "summary": (
            "MSc Computer Science student (Big Data & AI, Berlin) seeking a mandatory "
            "internship (Pflichtpraktikum) in AI/ML or Data Engineering, "
            f"{AVAILABILITY}. Backed by 3 years of professional experience building NLP "
            "features, RAG pipelines, and Python ETL/data pipelines, alongside full-stack "
            "delivery (React, FastAPI, Node.js). Ships and self-hosts live AI products, "
            "including a RAG-based portfolio-monitoring and document Q&A tool (CreditLens) "
            f"and an NLP-driven skill-matching engine (SkillSync). {SPOKEN_LANGUAGES}."
        ),
        "letter_intro": (
            "I am an MSc Computer Science student (Big Data & AI) in Berlin, looking for a "
            "mandatory internship (Pflichtpraktikum) in AI/ML engineering. Before starting my "
            "Master's I spent three years building production NLP features and Python data "
            "pipelines, and I have continued shipping and self-hosting my own AI projects "
            "alongside my studies."
        ),
        "skill_order": ["ai_ml", "data_eng", "backend", "frontend", "cloud", "qa"],
        "creditlens_order": ["etl", "schema", "watchlist", "rag", "deploy"],
        "keywords": SKILLS["ai_ml"]["keywords"],
    },
    "nlp": {
        "title_line": "NLP Engineering \u00b7 Pflichtpraktikum Candidate \u00b7 MSc Big Data & AI",
        "summary": (
            "MSc Computer Science student (Big Data & AI, Berlin) seeking a mandatory "
            "internship (Pflichtpraktikum) in NLP or AI Engineering, "
            f"{AVAILABILITY}. Backed by 3 years of professional experience building chatbot "
            "systems, semantic search, and RAG-based document Q&A, alongside Python data "
            "pipelines and full-stack delivery (React, FastAPI, Node.js). Ships and "
            "self-hosts live NLP products, including CreditLens (RAG document Q&A with cited "
            f"sources) and SkillSync (semantic skill-matching). {SPOKEN_LANGUAGES}."
        ),
        "letter_intro": (
            "I am an MSc Computer Science student (Big Data & AI) in Berlin, looking for a "
            "mandatory internship (Pflichtpraktikum) in NLP engineering. Before starting my "
            "Master's I spent three years building production NLP systems, including a "
            "support chatbot and semantic search features, and I have continued shipping and "
            "self-hosting my own NLP projects alongside my studies."
        ),
        "skill_order": ["ai_ml", "data_eng", "backend", "frontend", "cloud", "qa"],
        "creditlens_order": ["rag", "etl", "watchlist", "schema", "deploy"],
        "keywords": ["nlp", "chatbot", "spacy"] + SKILLS["ai_ml"]["keywords"],
    },
}


KNOWN_GAPS = ["docker", "kubernetes", "airflow", "dbt", "ci/cd", "spark streaming",
              "computer vision", "opencv", "tensorflow"]


# ---------------------------------------------------------------------------
# HARD BLOCKERS
#
# Postings that will reject you regardless of how good the CV is. Feed these
# to a blocker filter so you stop spending your limited time on them.
# German fluency is the big one -- at A2 you are not a realistic candidate
# for a posting demanding C1, and those applications are pure time cost.
# ---------------------------------------------------------------------------
BLOCKER_PATTERNS = [
    r"\bC1\b", r"\bC2\b",
    r"verhandlungssicher(?:e[sn]?)?\s+Deutsch",
    r"flie\u00dfend(?:e[sn]?)?\s+Deutsch",
    r"Deutsch\s+auf\s+(?:mutter|verhandlungs)",
    r"native\s+German", r"fluent\s+German",
    r"German\s+\(C1", r"German\s+\(C2",
    r"\bPhD\s+(?:required|candidate)",
    r"minimum\s+of\s+[5-9]\+?\s+years",
]


def validate(strict=True):
    """Refuse to build documents that still contain FILL markers.

    Call this at the top of build_resume() and build_cover_letter().
    Sending a resume that says 'deflecting FILL: % of support tickets' is
    worse than sending nothing at all.
    """
    import re

    problems = []
    for job in EXPERIENCE:
        for b in job["bullets"]:
            if FILL in b:
                problems.append(f"{job['org']}: {b[:70]}...")

    if problems and strict:
        raise SystemExit(
            "\n".join([
                "",
                "=" * 68,
                f"  {len(problems)} bullet(s) still contain FILL markers.",
                "  Replace them with real numbers before generating documents.",
                "  A defensible estimate with '~' beats a placeholder.",
                "=" * 68,
                "",
            ] + [f"  - {p}" for p in problems] + [""])
        )
    return problems


if __name__ == "__main__":
    remaining = validate(strict=False)
    print(f"{len(remaining)} bullet(s) still need real numbers:\n")
    for p in remaining:
        print(f"  - {p}")
    print(f"\nWork auth mode: {'CONFIRMED' if VERIFY_WORK_AUTH else 'NEUTRAL (verify to upgrade)'}")
    print(f"Availability:   {AVAILABILITY}")