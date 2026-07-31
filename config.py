"""
Master resume content bank.

RULE: This file is the single source of truth for everything true about
Srikar's resume. The tailoring pipeline (pipeline/tailor.py) is only allowed
to REORDER and RELABEL content that already exists here. It must never
invent a skill, number, or achievement that isn't in this file.
"""

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

WORK_AUTH = (
    "Work Authorization: German student residence permit (\u00a716 AufenthG) "
    "\u2014 authorized to work up to 140 full days / 280 half days per year; "
    "visa extension currently in process."
)

AVAILABILITY = "available from August 2026 for 5\u20136 months (per program requirement)"

SKILLS = {
    "ai_ml": {
        "label": "AI/ML & NLP",
        "items": "PyTorch (fundamentals), spaCy (NLP), sentence-transformers / FAISS "
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
    "languages": {
        "label": "Languages (spoken)",
        "items": "English (Fluent), German (A2, progressing to B1)",
        "keywords": ["german", "english", "language"],
    },
}

EXPERIENCE = [
    {
        "title": "Application Developer",
        "org": "Vavili Technologies",
        "location": "Hyderabad, India",
        "dates": "May 2023 \u2013 Aug 2025",
        "bullets": [
            "Built and shipped responsive full-stack features (React, Node.js, Flask) for "
            "templeswiki.com, a multi-language content platform, improving page-load "
            "performance and overall user experience.",
            "Designed and deployed an NLP-powered chatbot that automated routine user queries, "
            "measurably reducing manual support workload and increasing user engagement on the "
            "platform.",
            "Automated multi-language content-label generation across the platform's full "
            "language set via a Python ETL pipeline, eliminating manual translation work from "
            "every release.",
            "Authored a structured test plan and full test-case suite as QA lead for the "
            "platform, materially reducing post-release defects.",
            "Built and deployed an in-house attendance tool adopted across the engineering "
            "team, streamlining day-to-day operations.",
        ],
    },
    {
        "title": "Trainee Software Engineer",
        "org": "ValueLabs",
        "location": "Hyderabad, India",
        "dates": "Jan 2022 \u2013 Feb 2023",
        "bullets": [
            "Improved application stability through systematic debugging and performance "
            "optimization of software modules alongside cross-functional teams, contributing "
            "to higher release quality.",
            "Increased defect-detection coverage and reduced post-release issues by authoring "
            "and executing detailed manual test plans and test cases across core "
            "functionalities.",
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
        "links": [("skilsync.srikarkodi.dev", "https://skilsync.srikarkodi.dev")],
        "bullets": [
            "Built and deployed a full-stack tool that parses a job description, extracts "
            "required skills via NLP, and matches them against a candidate profile using "
            "semantic similarity search to surface skill gaps; live at a public URL.",
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

EDUCATION = [
    {
        "degree": "MSc Computer Science \u2014 Big Data & Artificial Intelligence",
        "dates": "Expected 2027",
        "detail": "SRH University of Applied Sciences, Berlin \u00b7 Currently enrolled \u2014 "
                  "mandatory internship (Pflichtpraktikum) required as part of program",
    },
    {
        "degree": "B.Tech Electronics & Communication Engineering",
        "dates": "2016 \u2013 2020",
        "detail": "MVGR College of Engineering, India",
    },
]

VARIANTS = {
    "data_engineer": {
        "title_line": "Data Engineer  \u00b7  AI/ML & Full-Stack Background",
        "summary": (
            "Data Engineer with 3 years of production experience building Python ETL "
            "pipelines, data validation systems, and schema design, alongside NLP/RAG "
            "features and full-stack delivery (React, FastAPI, Node.js). Currently completing "
            "an MSc in Computer Science (Big Data & AI) in Berlin. Shipped multiple live "
            "products under my own domain, including CreditLens, a portfolio-monitoring tool "
            "with an automated data-validation pipeline and star-schema design. Seeking a "
            f"Pflichtpraktikum (mandatory internship) in Data Engineering, {AVAILABILITY}. "
            "English (Fluent), German (A2, progressing to B1)."
        ),
        "skill_order": ["data_eng", "ai_ml", "backend", "frontend", "cloud", "qa", "languages"],
        "creditlens_order": ["etl", "schema", "deploy", "watchlist", "rag"],
        "keywords": SKILLS["data_eng"]["keywords"],
    },
    "ai_ml": {
        "title_line": "AI/ML & Data Engineer  \u00b7  Full-Stack Background",
        "summary": (
            "AI/ML & Data Engineer with 3 years of production experience building NLP "
            "features, RAG pipelines, and Python ETL/data pipelines, alongside full-stack "
            "delivery (React, FastAPI, Node.js). Currently completing an MSc in Computer "
            "Science (Big Data & AI) in Berlin. Shipped multiple live AI-powered products "
            "under my own domain, including a RAG-based portfolio-monitoring and document "
            "Q&A tool (CreditLens) and an NLP-driven skill-matching engine (SkillSync). "
            f"Seeking a Pflichtpraktikum (mandatory internship) in AI/ML or Data Engineering, "
            f"{AVAILABILITY}. English (Fluent), German (A2, progressing to B1)."
        ),
        "skill_order": ["ai_ml", "data_eng", "backend", "frontend", "cloud", "qa", "languages"],
        "creditlens_order": ["etl", "schema", "watchlist", "rag", "deploy"],
        "keywords": SKILLS["ai_ml"]["keywords"],
    },
    "nlp": {
        "title_line": "NLP Engineer  \u00b7  AI/ML & Full-Stack Background",
        "summary": (
            "NLP Engineer with 3 years of production experience building chatbot systems, "
            "semantic search, and RAG-based document Q&A, alongside Python data pipelines and "
            "full-stack delivery (React, FastAPI, Node.js). Currently completing an MSc in "
            "Computer Science (Big Data & AI) in Berlin. Shipped multiple live NLP-powered "
            "products under my own domain, including CreditLens (RAG document Q&A with cited "
            "sources) and SkillSync (semantic skill-matching). Seeking a Pflichtpraktikum "
            f"(mandatory internship) in NLP or AI Engineering, {AVAILABILITY}. English "
            "(Fluent), German (A2, progressing to B1)."
        ),
        "skill_order": ["ai_ml", "data_eng", "backend", "frontend", "cloud", "qa", "languages"],
        "creditlens_order": ["rag", "etl", "watchlist", "schema", "deploy"],
        "keywords": ["nlp", "chatbot", "spacy"] + SKILLS["ai_ml"]["keywords"],
    },
}

KNOWN_GAPS = ["docker", "kubernetes", "airflow", "dbt", "ci/cd", "spark streaming",
              "computer vision", "opencv", "tensorflow"]