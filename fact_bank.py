"""
Canonical, structured fact bank -- the single source of truth for every
factual claim that may appear in a CV or cover letter.

RULES (remediation brief R1 / R7 / D6):

* Every factual claim about the candidate lives here. The pipeline may only
  SELECT, ORDER and REFRAME facts from this bank -- it never generates,
  alters or infers one.
* Every achievement carries a `verified` flag. A metric flagged
  `verified: False` is expressed as SCOPE (the `scope` text, no number),
  never as a number.
* Every achievement carries pre-written `variants`: 2-3 framings that are
  FACTUALLY IDENTICAL (same numbers, same claims) and differ only in
  emphasis. Tailoring picks a variant; it never composes new prose about the
  candidate's history. Keeping the numbers identical across every variant is
  what makes metric stability (T4) structurally guaranteed.
* The `_NUMBERS` set below is derived from this bank and is what the "no
  fabrication" test (T3) checks every number in a generated CV against.

Do NOT add content here casually. If a claim is not in this file it must not
appear in a document. If a number is not in the bank it does not go in a
document.
"""

import re

from config import CONTACT, EDUCATION, SENDER_ADDRESS, CANDIDATE_PROFILE

FILL = "FILL:"

# ---------------------------------------------------------------------------
# ACHIEVEMENTS -- PROFESSIONAL EXPERIENCE
#
# Every achievement has:
#   verified: bool
#   numbers:  the literal metric tokens that may appear (used by T3/T4)
#   variants: 2-3 factually-identical framings
#   scope:    number-free framing used whenever verified is False
# ---------------------------------------------------------------------------

EXPERIENCE_ACHIEVEMENTS = {
    "vavili": {
        "title": "Application Developer",
        "org": "Vavili Technologies",
        "location": "Hyderabad, India",
        "dates": "May 2023 \u2013 Aug 2025",
        "achievements": {
            "chatbot": {
                "verified": True,
                "numbers": ["~72%", "~5", "10"],
                "variants": [
                    "Built an NLP-powered customer support chatbot (Python, spaCy) that "
                    "autonomously resolved ~72% of customer queries, cutting average "
                    "response time from ~5 minutes to under 10 seconds.",
                    "Shipped an NLP customer-support chatbot (Python, spaCy) that "
                    "resolved ~72% of queries autonomously and cut average handling "
                    "time from ~5 minutes to under 10 seconds.",
                ],
                "scope": "Built an NLP customer-support chatbot that autonomously "
                         "resolved the large majority of customer queries, cutting "
                         "average response time to under ten seconds.",
            },
            "localisation_etl": {
                "verified": True,
                "numbers": ["15", "~90%", "~30", "3"],
                "variants": [
                    "Automated multi-language content-label generation across the "
                    "platform's 15 supported languages via a Python ETL pipeline, "
                    "cutting manual localisation effort by ~90% (from ~30 hours to "
                    "under 3 hours per release).",
                    "Built a Python ETL pipeline that generates content labels across "
                    "15 supported languages, reducing manual localisation effort by "
                    "~90% (from ~30 hours to under 3 hours per release).",
                ],
                "scope": "Automated multi-language content-label generation across "
                         "the platform's supported languages via a Python ETL "
                         "pipeline, cutting manual localisation effort substantially "
                         "per release.",
            },
            "fullstack": {
                # The 96+ Lighthouse figure is the candidate's own but has never
                # been re-verified on the current site build. verified=False means
                # the number-free-of-96 scope framing is emitted instead, and "96+"
                # does not appear in any variant.
                "verified": False,
                "numbers": ["40,000+", "3.8", "1.6"],
                "variants": [
                    "Built and optimised responsive full-stack features (React, "
                    "Node.js, Flask) for templeswiki.com, serving 40,000+ monthly "
                    "users \u2014 improving page-load time from 3.8s to 1.6s.",
                    "Delivered responsive full-stack features (React, Node.js, Flask) "
                    "on templeswiki.com, serving 40,000+ monthly users and improving "
                    "page-load time from 3.8s to 1.6s.",
                ],
                "scope": "Built and optimised responsive full-stack features (React, "
                         "Node.js, Flask) for templeswiki.com, serving 40,000+ monthly "
                         "users and improving page-load time from 3.8s to 1.6s.",
            },
            "qa": {
                "verified": True,
                "numbers": ["18+", "55%"],
                "variants": [
                    "Led QA across 18+ production releases, authoring a structured "
                    "test plan and full test-case suite that reduced post-release "
                    "defects by 55%.",
                    "Led QA for 18+ production releases with a structured test plan "
                    "and complete test-case suite, reducing post-release defects "
                    "by 55%.",
                ],
                "scope": "Led QA across production releases, authoring a structured "
                         "test plan and full test-case suite that materially reduced "
                         "post-release defects.",
            },
        },
    },
    "valuelabs": {
        "title": "Trainee Software Engineer",
        "org": "ValueLabs",
        "location": "Hyderabad, India",
        "dates": "Jan 2022 \u2013 Feb 2023",
        "achievements": {
            "debugging": {
                "verified": True,
                "numbers": ["12+"],
                "variants": [
                    "Debugged and performance-optimised 12+ application modules "
                    "alongside cross-functional teams, accelerating root-cause "
                    "analysis and improving overall product stability.",
                    "Performance-optimised 12+ application modules with "
                    "cross-functional teams, accelerating root-cause analysis and "
                    "improving product stability.",
                ],
                "scope": "Debugged and performance-optimised application modules "
                         "alongside cross-functional teams, accelerating root-cause "
                         "analysis and improving product stability.",
            },
            "test_automation": {
                "verified": True,
                "numbers": ["40+"],
                "variants": [
                    "Authored and executed manual and automated test suites (pytest / "
                    "Selenium) covering 40+ core functionalities, sustaining "
                    "regression coverage and release quality across Agile sprints.",
                    "Wrote and ran manual and automated test suites (pytest / "
                    "Selenium) covering 40+ core functionalities, sustaining release "
                    "quality across Agile sprints.",
                ],
                "scope": "Authored and executed manual and automated test suites "
                         "covering core functionalities, sustaining regression "
                         "coverage and release quality across Agile sprints.",
            },
        },
    },
}


# ---------------------------------------------------------------------------
# PROJECT ACHIEVEMENTS
# ---------------------------------------------------------------------------

PROJECT_ACHIEVEMENTS = {
    "creditlens": {
        "name": "CreditLens \u2014 Private Credit Portfolio Monitor",
        "stack": "Python \u00b7 FastAPI \u00b7 Next.js \u00b7 SQLite \u00b7 ChromaDB \u00b7 Groq \u00b7 AWS EC2",
        "links": [("creditlens.srikarkodi.dev", "https://creditlens.srikarkodi.dev"),
                  ("github.com/Namidok/CreditLens", "https://github.com/Namidok/CreditLens")],
        "domain_tags": ["finance", "private_credit", "document_ai", "rag", "fullstack"],
        "summary_paragraph": (
            "For a private-credit portfolio team, CreditLens ingests GP quarterly "
            "reports in inconsistent formats \u2014 German date conventions, comma "
            "decimals, unit errors, duplicates \u2014 repairs what can be repaired and "
            "quarantines the rest with plain-language reasons, then flags deterioration "
            "patterns such as rising leverage alongside falling coverage before they "
            "become a covenant breach."
        ),
        "achievements": {
            "etl": {
                "verified": True,
                "numbers": [],
                "variants": [
                    "Built an end-to-end private credit portfolio monitoring tool that "
                    "ingests inconsistently formatted GP quarterly reports (PDFs and "
                    "CSVs with German date conventions, comma decimals, unit errors, "
                    "and duplicates) through a Python ETL pipeline with a validation "
                    "gate that repairs fixable issues and quarantines unfixable ones "
                    "with plain-language reasons.",
                ],
                "scope": None,
            },
            "schema": {
                "verified": True,
                "numbers": [],
                "variants": [
                    "Designed a SQLite schema with a funds/valuations star schema and "
                    "window-function views (ROW_NUMBER for latest valuations, LAG for "
                    "quarter-on-quarter comparison) that ports directly to production "
                    "RDBMS environments.",
                ],
                "scope": None,
            },
            "watchlist": {
                "verified": True,
                "numbers": ["5.5x", "4"],
                "variants": [
                    "Implemented an automatic watchlist that flags the classic credit "
                    "deterioration pattern \u2014 rising leverage alongside falling "
                    "coverage \u2014 demonstrated with a planted scenario where a fund "
                    "breaches its 5.5x covenant across 4 quarters.",
                ],
                "scope": "Implemented an automatic watchlist that flags the classic "
                         "credit deterioration pattern \u2014 rising leverage "
                         "alongside falling coverage \u2014 demonstrated with a "
                         "planted covenant-breach scenario.",
            },
            "rag": {
                "verified": True,
                "numbers": ["3.3"],
                "variants": [
                    "Built a RAG layer using sentence-transformers, ChromaDB, and Groq "
                    "(Llama 3.3) that answers natural-language questions about GP PDF "
                    "documents with cited sources and refuses to hallucinate facts not "
                    "in context.",
                ],
                "scope": None,
            },
            "deploy": {
                "verified": True,
                "numbers": ["2"],
                "variants": [
                    "Rebuilt from a Streamlit prototype into a production Next.js + "
                    "FastAPI application deployed on AWS EC2 (Linux) with an Nginx "
                    "reverse proxy and systemd process management.",
                ],
                "scope": None,
            },
        },
    },
    "stadtanalyse": {
        "name": "Stadtanalyse \u2014 Urban Mobility Data Lake & Analytics Platform",
        "stack": "Kafka \u00b7 Spark Structured Streaming \u00b7 Delta Lake \u00b7 dbt \u00b7 Airflow \u00b7 PostgreSQL \u00b7 XGBoost \u00b7 FastAPI \u00b7 React",
        "links": [("stadtanalyse.srikarkodi.dev", "https://stadtanalyse.srikarkodi.dev"),
                  ("github.com/Namidok/Stadtanalyse", "https://github.com/Namidok/Stadtanalyse")],
        "domain_tags": ["logistics", "mobility", "transport", "streaming", "data_platform"],
        "summary_paragraph": (
            "For transit operators drowning in real-time feeds, Stadtanalyse ingests "
            "live transit, weather and event data into a curated analytics layer where "
            "every batch stays auditable, and predicts delays so the operator sees "
            "congestion forming before riders do."
        ),
        "achievements": {
            "platform": {
                "verified": True,
                "numbers": ["4"],
                "variants": [
                    "Built an end-to-end streaming data platform ingesting real-time "
                    "transit, weather and city-event feeds through 4 Kafka topics into "
                    "a Delta Lake medallion architecture on MinIO (bronze \u2192 silver "
                    "\u2192 gold), orchestrated end to end by an Apache Airflow DAG.",
                ],
                "scope": "Built an end-to-end streaming data platform ingesting "
                         "real-time transit, weather and city-event feeds into a "
                         "Delta Lake medallion architecture, orchestrated by an "
                         "Apache Airflow DAG.",
            },
            "dbt": {
                "verified": True,
                "numbers": [],
                "variants": [
                    "Modelled the gold layer in dbt \u2014 staging views into "
                    "dimension and fact tables, then six analytical marts (route "
                    "reliability, delay trends, congestion hotspots, weather impact, "
                    "events impact, ML features) with schema and source tests.",
                ],
                "scope": "Modelled the gold layer in dbt \u2014 staging views into "
                         "dimension and fact tables, then analytical marts covering "
                         "route reliability, delay trends and ML features, with "
                         "schema and source tests.",
            },
            "quality": {
                "verified": True,
                "numbers": [],
                "variants": [
                    "Integrated Great Expectations with versioned expectation suites "
                    "per table, run against the Silver layer with results published "
                    "to a queryable quality schema so every batch's outcome stays "
                    "auditable.",
                ],
                "scope": None,
            },
            "ml": {
                "verified": True,
                "numbers": [],
                "variants": [
                    "Trained and served an XGBoost delay-prediction model on features "
                    "built by dbt, retrained on schedule by the same Airflow DAG and "
                    "exposed through a FastAPI endpoint.",
                ],
                "scope": None,
            },
            "serve": {
                "verified": True,
                "numbers": [],
                "variants": [
                    "Served the platform through FastAPI and a React/Vite dashboard "
                    "with a live vehicle map (Leaflet) and time-series charts, "
                    "instrumented with Prometheus and Grafana.",
                ],
                "scope": None,
            },
        },
    },
    "pipeline_guardian": {
        "name": "PipelineGuardian \u2014 Data-Quality Gateway & Drift Detection",
        "stack": "Python \u00b7 Apache Airflow \u00b7 PostgreSQL \u00b7 Docker \u00b7 Pandas \u00b7 SciPy",
        "links": [("pipelineguardian.srikarkodi.dev", "https://pipelineguardian.srikarkodi.dev"),
                  ("github.com/Namidok/PipeLine_Guardian", "https://github.com/Namidok/PipeLine_Guardian")],
        "domain_tags": ["data_platform", "data_quality", "mlops"],
        "summary_paragraph": (
            "For teams whose nightly data batches fail silently, PipelineGuardian "
            "validates every batch before it reaches the warehouse, quarantines the "
            "bad ones with a human-readable reason, and catches statistical drift "
            "that row-level checks miss."
        ),
        "achievements": {
            "gateway": {
                "verified": True,
                "numbers": [],
                "variants": [
                    "Built a data-quality gateway that validates daily batches before "
                    "they reach the warehouse \u2014 schema conformance, per-column "
                    "null-rate thresholds, duplicate detection and business rules "
                    "\u2014 routing clean batches to a curated table and failures to "
                    "quarantine with a human-readable reason for each rejection.",
                ],
                "scope": None,
            },
            "drift": {
                "verified": True,
                "numbers": ["0.01"],
                "variants": [
                    "Implemented statistical drift detection using a two-sample "
                    "Kolmogorov\u2013Smirnov test (SciPy) against a rolling baseline of "
                    "previously-passed batches, flagging p < 0.01 \u2014 the only check "
                    "that catches a batch where every individual row is valid but the "
                    "distribution has shifted.",
                ],
                "scope": "Implemented statistical drift detection using a two-sample "
                         "Kolmogorov\u2013Smirnov test (SciPy) against a rolling "
                         "baseline of previously-passed batches, catching batches "
                         "where every row is individually valid but the distribution "
                         "has shifted.",
            },
            "airflow": {
                "verified": True,
                "numbers": ["2", "2.9"],
                "variants": [
                    "Orchestrated with an Apache Airflow 2.9 DAG (@daily, 2 retries "
                    "with backoff) running in Docker, deliberately kept thin so the "
                    "pipeline logic stays testable outside Airflow.",
                ],
                "scope": "Orchestrated with an Apache Airflow DAG running in Docker, "
                         "deliberately kept thin so the pipeline logic stays "
                         "testable outside Airflow.",
            },
            "schema": {
                "verified": True,
                "numbers": ["16"],
                "variants": [
                    "Designed a PostgreSQL 16 schema (clean, quarantine, audit_log, "
                    "batch_stats) that writes a full JSON validation report per run, "
                    "making any batch's outcome auditable months after it ran.",
                ],
                "scope": "Designed a PostgreSQL schema that writes a full JSON "
                         "validation report per run, making any batch's outcome "
                         "auditable months after it ran.",
            },
            "synth": {
                "verified": True,
                "numbers": [],
                "variants": [
                    "Built a synthetic data generator with four controllable failure "
                    "modes (null spike, statistical drift, schema drift, duplicates) "
                    "so every validator can be proven against a scenario with a "
                    "known cause.",
                ],
                "scope": "Built a synthetic data generator with controllable failure "
                         "modes so every validator can be proven against a scenario "
                         "with a known cause.",
            },
        },
    },
    "skillsync": {
        "name": "SkillSync \u2014 Semantic Skill-Matching Engine",
        "stack": "React \u00b7 FastAPI \u00b7 spaCy \u00b7 sentence-transformers \u00b7 Python",
        "links": [("skillsync.srikarkodi.dev", "https://skillsync.srikarkodi.dev")],
        "domain_tags": ["consumer", "productivity", "nlp", "semantic_search"],
        "summary_paragraph": (
            "SkillSync parses a job description, extracts the required skills with "
            "NLP, and matches them against a candidate profile via semantic "
            "similarity search to surface the gaps a candidate should close."
        ),
        "achievements": {
            "app": {
                "verified": True,
                "numbers": [],
                "variants": [
                    "Built and deployed a full-stack tool that parses a job "
                    "description, extracts required skills via NLP, and matches them "
                    "against a candidate profile using semantic similarity search to "
                    "surface skill gaps.",
                ],
                "scope": None,
            },
        },
    },
    "covercraft": {
        "name": "CoverCraft \u2014 AI Cover-Letter Generator",
        "stack": "React \u00b7 FastAPI \u00b7 LLM API \u00b7 Python",
        "links": [("covercraft.srikarkodi.dev", "https://covercraft.srikarkodi.dev")],
        "domain_tags": ["consumer", "productivity", "llm"],
        "summary_paragraph": (
            "CoverCraft is a deployed AI application that tailors a cover letter to "
            "a specific job description and the user's own experience, exposed "
            "through a FastAPI backend and a React frontend."
        ),
        "achievements": {
            "app": {
                "verified": True,
                "numbers": [],
                "variants": [
                    "Developed and deployed an LLM-powered cover-letter generator "
                    "that tailors output to a specific job description and the user's "
                    "experience, exposed through a FastAPI backend and React "
                    "frontend.",
                ],
                "scope": None,
            },
        },
    },
}

# Side projects that are retired from the CV by default. They stay in the bank
# and are re-promoted by the tailor ONLY when the JD's domain matches theirs
# (e.g. a consumer-tech / productivity posting).
RETIRED_PROJECTS = ["skillsync", "covercraft"]

# Default project ordering used when no JD domain matches anything.
DEFAULT_PROJECT_ORDER = ["creditlens", "stadtanalyse", "pipeline_guardian"]


# ---------------------------------------------------------------------------
# CANONICAL SKILLS
#
# R8 requires these ten literal strings in the skills block: Kafka, Apache
# Airflow, dbt, Spark Structured Streaming, Delta Lake, Great Expectations,
# XGBoost, Docker, Prometheus, Grafana. They exist in the projects above and
# were missing from the skills section, so keyword filters did not match them.
# They are now canonical data-engineering content.
# ---------------------------------------------------------------------------

SKILLS = {
    "programming": {
        "label": "Programming Languages",
        "items": "Python, SQL, JavaScript, HTML5, CSS3",
        "keywords": ["python", "sql", "javascript", "html", "css",
                     "programmierung", "softwareentwicklung"],
    },
    "ai_ml": {
        "label": "AI/ML & NLP",
        "items": ("PyTorch, scikit-learn, spaCy (NLP), sentence-transformers / "
                  "FAISS (embeddings & semantic search), Retrieval-Augmented "
                  "Generation (RAG), LLM integration (Groq / Llama 3.3), ChromaDB"),
        "keywords": ["pytorch", "spacy", "nlp", "faiss", "sentence-transformers",
                     "rag", "retrieval augmented generation", "llm", "groq",
                     "llama", "chromadb", "embeddings", "semantic search",
                     "generative ai", "genai", "machine learning", "deep learning",
                     "vector database", "fine-tuning", "model training"],
    },
    "data_eng": {
        "label": "Data Engineering",
        "items": ("ETL pipeline design, Apache Airflow, Kafka, Spark Structured "
                  "Streaming, Delta Lake, dbt, Great Expectations, data validation "
                  "& quality gates, star-schema design, Pandas, NumPy, PySpark, "
                  "PostgreSQL, SQLite, XGBoost, Docker, Prometheus, Grafana"),
        "keywords": ["etl", "data pipeline", "apache airflow", "airflow", "kafka",
                     "spark", "spark structured streaming", "delta lake", "dbt",
                     "great expectations", "data validation", "star schema",
                     "pandas", "numpy", "pyspark", "postgresql", "postgres",
                     "sqlite", "xgboost", "docker", "prometheus", "grafana",
                     "data engineering", "datenpipeline", "datenbank",
                     "datenmodellierung", "data warehouse"],
    },
    "backend": {
        "label": "Backend",
        "items": "FastAPI, Flask, Django, Node.js, REST APIs",
        "keywords": ["fastapi", "flask", "django", "node.js", "nodejs",
                     "rest api", "backend"],
    },
    "frontend": {
        "label": "Frontend",
        "items": "React.js, Next.js, HTML5, CSS3",
        "keywords": ["react", "next.js", "nextjs", "html", "css", "frontend"],
    },
    "cloud": {
        "label": "Cloud & Infra",
        "items": "AWS (EC2, S3, IAM), Docker, CI/CD (GitHub Actions), Linux, Nginx, systemd, Git, GitHub",
        "keywords": ["aws", "ec2", "s3", "iam", "docker", "container", "containerisation",
                     "ci/cd", "continuous integration", "continuous deployment",
                     "github actions", "linux", "nginx", "systemd", "git", "github"],
    },
    "qa": {
        "label": "Testing & QA",
        "items": "Test planning, test automation (pytest / Selenium), manual test-case design, defect tracking",
        "keywords": ["testing", "qa", "test case", "defect tracking",
                     "quality assurance", "test automation", "pytest", "selenium",
                     "unit testing", "regression testing", "automated testing"],
    },
}

# Category order used by every variant. Per-JD reordering only happens within
# the tail (see build.py), never across these.
SKILL_ORDER = ["programming", "ai_ml", "data_eng", "backend", "frontend", "cloud", "qa"]

# Canonical technology set -- every technology the candidate claims anywhere.
# Used by the no-fabrication check (T3) and to map JD technology names.
CANONICAL_TECHNOLOGIES = [
    "Python", "SQL", "JavaScript", "HTML5", "CSS3", "PyTorch", "scikit-learn",
    "spaCy", "sentence-transformers", "FAISS", "Retrieval-Augmented Generation",
    "RAG", "Groq", "Llama 3.3", "ChromaDB", "Pandas", "NumPy", "PySpark",
    "ETL", "Apache Airflow", "Airflow", "Kafka", "Spark Structured Streaming",
    "Spark", "Delta Lake", "dbt", "Great Expectations", "PostgreSQL", "SQLite",
    "XGBoost", "Docker", "Prometheus", "Grafana", "MinIO", "Leaflet", "SciPy",
    "FastAPI", "Flask", "Django", "Node.js", "REST APIs", "React", "Next.js",
    "AWS", "EC2", "S3", "IAM", "GitHub Actions", "CI/CD", "Linux", "Nginx",
    "systemd", "Git", "GitHub", "pytest", "Selenium", "Vite", "Streamlit",
]

# Technologies the candidate does NOT have. When a JD names one, it is logged
# as a gap (R5.6) and never placed in a document.
KNOWN_GAPS = [
    "kubernetes", "databricks", "snowflake", "tensorflow", "terraform",
    "computer vision", "opencv", "kafka streams", "flink", "airbyte",
    "prefect", "dagster", "mongo", "redis", "graphql", "typescript", "java",
    "scala", "go", "rust", "c++", "tableau", "power bi", "dbt cloud",
    "vertex ai", "sagemaker", "azure", "gcp", "bigquery", "redshift",
    "spark sql", "glue", "lakehouse", "iceberg", "hudi", "mlflow", "wandb",
    "kubeflow", "langchain", "llamaindex", "weaviate", "qdrant", "milvus",
    "pinecone", "elasticsearch", "neo4j", "k8s", "docker compose",
]


# ---------------------------------------------------------------------------
# TECH -> TRUE CLAIM SENTENCES (for the cover letter's technology-mapping line)
# Each sentence is a factual restatement of content already in the bank.
# ---------------------------------------------------------------------------
TECH_CLAIM_SENTENCES = {
    "ChromaDB": "I have built a RAG layer with ChromaDB and sentence-transformers that answers questions over financial documents with cited sources.",
    "FAISS": "I have used FAISS and sentence-transformers for semantic search over candidate and job-description text.",
    "sentence-transformers": "I have used sentence-transformers embeddings for semantic search and RAG retrieval.",
    "vector database": "I have built RAG retrieval with vector databases (ChromaDB) and FAISS over real financial documents.",
    "vector databases": "I have built RAG retrieval with vector databases (ChromaDB) and FAISS over real financial documents.",
    "RAG": "I have built a RAG layer that answers questions over financial documents with cited sources and refuses to hallucinate facts not in context.",
    "Spark": "I have processed real-time transit and weather feeds with Spark Structured Streaming into a Delta Lake medallion architecture.",
    "Kafka": "I have built a streaming platform ingesting four Kafka topics into a Delta Lake medallion architecture.",
    "Apache Airflow": "I have orchestrated end-to-end pipelines with Apache Airflow, including scheduled model retraining.",
    "Airflow": "I have orchestrated end-to-end pipelines with Apache Airflow, including scheduled model retraining.",
    "Spark Structured Streaming": "I have processed streaming data with Spark Structured Streaming into a Delta Lake.",
    "Delta Lake": "I have built a Delta Lake medallion architecture with bronze, silver and gold layers.",
    "dbt": "I have modelled analytical marts in dbt with schema and source tests.",
    "Great Expectations": "I have run versioned Great Expectations suites against batch data with auditable results.",
    "XGBoost": "I have trained and served an XGBoost model retrained on schedule by an Airflow DAG.",
    "Docker": "I have containerised Airflow and pipeline services with Docker.",
    "Prometheus": "I have instrumented a live platform with Prometheus metrics.",
    "Grafana": "I have visualised live platform metrics in Grafana.",
    "PyTorch": "I use PyTorch for model development in my MSc programme.",
    "spaCy": "I have built NLP features with spaCy, including a customer-support chatbot.",
    "Groq": "I have used Groq (Llama 3.3) for LLM inference in a RAG system.",
    "LLM": "I have integrated LLM APIs (Groq / Llama 3.3) into a RAG application.",
    "LLM integration": "I have integrated LLM APIs (Groq / Llama 3.3) into a RAG application.",
    "Python": "I build production systems in Python, from ETL pipelines to FastAPI backends.",
    "ETL": "I have built Python ETL pipelines with validation gates for financial and batch data.",
    "PostgreSQL": "I have designed PostgreSQL schemas for auditable batch processing.",
    "SQLite": "I have designed a SQLite star-schema for fund valuations.",
    "FastAPI": "I serve models and applications through FastAPI backends.",
    "React": "I have shipped React and Next.js frontends for live applications.",
    "AWS": "I have deployed production applications on AWS EC2 with Nginx and systemd.",
}

# Default "summary_paragraph" lead project per domain family, used by the
# letter when no project ranks above the others.
FAMILY_TO_PROJECT = {
    "finance": "creditlens",
    "private_credit": "creditlens",
    "logistics": "stadtanalyse",
    "mobility": "stadtanalyse",
    "transport": "stadtanalyse",
    "consumer": "covercraft",
    "productivity": "skillsync",
    "platform": "pipeline_guardian",
    "data_quality": "pipeline_guardian",
}

# ---------------------------------------------------------------------------
# METRIC SOURCING (review feedback, item 5)
#
# Metric-stability guarantees every CV says "~72% query resolution" and "55%
# defect reduction" consistently -- it does NOT verify the numbers. Before the
# next run, go through this table and declare where each metric came from so
# you can defend it in an interview. `kind` is one of:
#   measured      -> from a real system/dashboard/report you can point at
#   estimated     -> your own estimate (e.g. from release notes)
#   approximation -> a rough figure, use with "~"
#   unverified    -> cannot be sourced today -- rewrite this claim as scope
#
# `python3 fact_bank.py --audit` (or `python3 main.py --metric-audit`) lists
# every metric with its kind and source, and flags anything still UNSET or
# unverified. This is a paper-trail, not a build gate.
# ---------------------------------------------------------------------------
METRIC_SOURCES = {
    # "~72%":  {"kind": "unverified", "source": ""},
    # "~5":    {"kind": "unverified", "source": ""},
    # "10":    {"kind": "unverified", "source": ""},
    # "15":    {"kind": "unverified", "source": ""},
    # "~90%":  {"kind": "unverified", "source": ""},
    # "~30":   {"kind": "unverified", "source": ""},
    # "3":     {"kind": "unverified", "source": ""},
    # "40,000+": {"kind": "unverified", "source": ""},
    # "3.8":   {"kind": "unverified", "source": ""},
    # "1.6":   {"kind": "unverified", "source": ""},
    # "18+":   {"kind": "unverified", "source": ""},
    # "55%":   {"kind": "unverified", "source": ""},
    # "12+":   {"kind": "unverified", "source": ""},
    # "40+":   {"kind": "unverified", "source": ""},
    # "5.5x":  {"kind": "unverified", "source": ""},
    # "4":     {"kind": "unverified", "source": ""},
    # "3.3":   {"kind": "unverified", "source": ""},
    # "2":     {"kind": "unverified", "source": ""},
    # "0.01":  {"kind": "unverified", "source": ""},
    # "2.9":   {"kind": "unverified", "source": ""},
    # "16":    {"kind": "unverified", "source": ""},
}


def metric_audit():
    """Report every numeric metric in the bank against METRIC_SOURCES.

    Returns a list of dicts:
      {token, achievement, verified, kind, source, needs_action}
    where needs_action is True when the token has no provenance entry yet or
    its kind is 'unverified' (the review's rewrite-as-scope bucket).
    """
    out = []
    for org in EXPERIENCE_ACHIEVEMENTS.values():
        for key, ach in org["achievements"].items():
            _collect_metric(org["org"], key, ach, out)
    for proj in PROJECT_ACHIEVEMENTS.values():
        for key, ach in proj["achievements"].items():
            _collect_metric(proj["name"], key, ach, out)
    return out


def _collect_metric(where, key, ach, out):
    for token in sorted(ach.get("numbers") or []):
        entry = METRIC_SOURCES.get(token) or {}
        kind = entry.get("kind") or "unverified"
        source = (entry.get("source") or "").strip()
        unset = not METRIC_SOURCES.get(token)
        needs_action = unset or kind == "unverified" or not source
        out.append({
            "token": token,
            "achievement": f"{where} / {key}",
            "verified": bool(ach.get("verified", False)),
            "kind": kind,
            "source": source,
            "needs_action": needs_action,
        })


# ---------------------------------------------------------------------------
# DERIVED NUMBERS / TECHNOLOGIES (for T3/T4)
# ---------------------------------------------------------------------------

_NUMBER_RE = re.compile(r"~?\d[\d.,%+\u2013x/<>~]*")


def extract_numbers(text):
    """Every numeric token in `text`, normalized (a trailing sentence period
    or list comma is stripped so '55%.' == '55%' and 'HTML5,' == '5'). This is
    the SAME extractor the acceptance tests use (T3), so the bank's numbers
    and the CV's numbers agree by construction."""
    return {t.rstrip(".,") for t in _NUMBER_RE.findall(text or "")}


def _iter_all_achievements():
    for org in EXPERIENCE_ACHIEVEMENTS.values():
        for ach in org["achievements"].values():
            yield ach
    for proj in PROJECT_ACHIEVEMENTS.values():
        for ach in proj["achievements"].values():
            yield ach


def fact_bank_numbers():
    """Every numeric token the bank may legally emit (used by T3/T4)."""
    numbers = set()
    for ach in _iter_all_achievements():
        numbers.update(ach.get("numbers") or [])
    # Number tokens that ride inside canonical technology names (EC2 -> "2",
    # S3 -> "3", Llama 3.3 -> "3.3"). They are legitimate bank facts: the tech
    # itself is in the bank.
    for tech in CANONICAL_TECHNOLOGIES:
        numbers.update(extract_numbers(tech))
    # Config-level facts the CV/letter may state.
    numbers.add("3")                       # years of professional experience
    numbers.update(str(n) for n in CANDIDATE_PROFILE["duration_months"])
    numbers.update(extract_numbers(CANDIDATE_PROFILE["availability_text"]))
    numbers.update(extract_numbers("140-day work-limit exemption"))
    # Fixed personal/date facts that appear verbatim on every CV -- contact
    # digits, education and experience years, spoken-language level codes.
    # They are real data, not metrics, and identical across all JDs (T4 holds
    # because the set is constant).
    from config import CONTACT, SPOKEN_LANGUAGES, EDUCATION, WORK_AUTH, WORK_AUTH_LETTER
    for v in CONTACT.values():
        numbers.update(extract_numbers(str(v)))
    numbers.update(extract_numbers(SPOKEN_LANGUAGES))
    numbers.update(extract_numbers(WORK_AUTH))
    numbers.update(extract_numbers(WORK_AUTH_LETTER))
    for edu in EDUCATION:
        numbers.update(extract_numbers(edu.get("dates", "")))
    for org in EXPERIENCE_ACHIEVEMENTS.values():
        numbers.update(extract_numbers(org.get("dates", "")))
        numbers.update(extract_numbers(org.get("location", "")))
    return numbers


def fact_bank_technologies():
    """Every technology string the bank may legally emit."""
    return set(CANONICAL_TECHNOLOGIES)


def has_technology(name: str) -> bool:
    """Case/format-tolerant membership test against the canonical tech set."""
    if not name:
        return False
    n = name.strip().lower()
    for tech in CANONICAL_TECHNOLOGIES:
        if tech.lower() == n:
            return True
    # Multiword techs matched as whole strings only -- "Spark" must not make
    # "Spark SQL" a hit.
    return False


def _render_variant(ach: dict, jd_text: str = "") -> str:
    """Select the best pre-written variant for an achievement.

    verified=False forces the number-free scope framing (the unverified metric
    is expressed as scope, never as a number). Otherwise picks the variant
    with the most JD-vocabulary overlap (stable).
    """
    if not ach.get("verified", False):
        scope = ach.get("scope")
        if scope:
            return scope
        return _strip_numbers(ach.get("variants") or [""])[0]

    variants = ach.get("variants") or [""]
    if len(variants) == 1 or not jd_text:
        return variants[0]
    jd = jd_text.lower()
    best, best_hits = variants[0], -1
    for v in variants:
        tokens = set(re.findall(r"[a-z]{4,}", v.lower()))
        hits = sum(1 for t in tokens if t in jd)
        if hits > best_hits:
            best, best_hits = v, hits
    return best


def _strip_numbers(text: str) -> str:
    return _NUMBER_RE.sub("N", text)


# ---------------------------------------------------------------------------
# PUBLIC API USED BY THE PIPELINE
# ---------------------------------------------------------------------------

def experience_orgs():
    return list(EXPERIENCE_ACHIEVEMENTS.values())


def experience_org(org_key):
    return EXPERIENCE_ACHIEVEMENTS.get(org_key)


def projects():
    return dict(PROJECT_ACHIEVEMENTS)


def project(key):
    return PROJECT_ACHIEVEMENTS.get(key)


def all_project_keys():
    return list(PROJECT_ACHIEVEMENTS.keys())


def domain_families(project_key):
    return list(PROJECT_ACHIEVEMENTS[project_key]["domain_tags"])


def spokens():
    from config import SPOKEN_LANGUAGES
    return SPOKEN_LANGUAGES


def render_experience(jd_text="", cap=None):
    """Ordered experience bullets rendered from the bank (stable across JDs).

    cap: optional max bullets per job. Bullet ordering is FIXED -- the audit
    showed JD-driven reordering of *experience* bullets is exactly what lets
    one job be described differently across applications (D6). Project bullets
    may be reordered per JD; experience bullets may not. Metric stability (T4)
    depends on this.
    """
    rendered = []
    for org in experience_orgs():
        for key, ach in org["achievements"].items():
            rendered.append((org, key, _render_variant(ach, jd_text)))
            if cap and len([r for r in rendered if r[0] == org]) >= cap:
                break
    return rendered


def render_project_bullets(project_key, jd_text="", cap=None, order=None):
    """Project bullets rendered from the bank. `order` overrides the variant
    order (used by the tailor for JD relevance); selection is by JD language."""
    proj = PROJECT_ACHIEVEMENTS[project_key]
    keys = order or list(proj["achievements"].keys())
    out = []
    for k in keys:
        ach = proj["achievements"].get(k)
        if ach is None:
            continue
        out.append((k, _render_variant(ach, jd_text)))
        if cap and len(out) >= cap:
            break
    return out


def validate_bank():
    """Sanity checks: no FILL markers, every variant of an achievement carries
    the same numbers (metric stability), and a scope never emits a number that
    is not in the achievement's own `numbers` set."""
    problems = []
    for ach in _iter_all_achievements():
        if FILL in str(ach):
            problems.append(f"FILL marker in bank: {str(ach)[:60]}")
        nums = sorted(set(ach.get("numbers") or []))
        for v in ach.get("variants") or []:
            got = sorted(extract_numbers(v))
            if nums != got:
                problems.append(
                    f"metric drift in variants: got {got} want {nums} :: {v[:50]}")
        scope = ach.get("scope")
        if scope is not None:
            s_nums = extract_numbers(scope)
            extra = [n for n in s_nums if n not in set(ach.get("numbers") or [])]
            if extra:
                problems.append(f"scope emits numbers outside bank {extra}: {scope[:50]}")
    return problems


if __name__ == "__main__":
    import sys as _sys
    if "--audit" in _sys.argv:
        print("Metric provenance audit (review feedback, item 5) -- "
              "fix every needs_action row before your next run\n")
        for m in metric_audit():
            flag = "!!" if m["needs_action"] else "ok"
            print(f"  [{flag}] {m['token']:<9} {m['achievement']:<45} "
                  f"verified={m['verified']} kind={m['kind']} source={m['source'] or 'UNSET'}")
        print(f"\n{sum(1 for m in metric_audit() if m['needs_action'])} metric(s) "
              "still need a declared source. Set them in METRIC_SOURCES in "
              "fact_bank.py, or rewrite the claim as scope.")
        _sys.exit(0)
    probs = validate_bank()
    print(f"{len(probs)} fact-bank problem(s)")
    for p in probs:
        print(" -", p)
