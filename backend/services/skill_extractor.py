import re
from typing import List, Dict, Tuple

# Comprehensive taxonomy of skills mapped to categories
MASTER_SKILL_TAXONOMY: Dict[str, Tuple[str, List[str]]] = {
    # Programming Languages
    "python": ("programming", ["python", "py", "python3", "python2"]),
    "javascript": ("programming", ["javascript", "js", "ecmascript", "es6"]),
    "typescript": ("programming", ["typescript", "ts"]),
    "java": ("programming", ["java", "core java", "java 8", "java 11", "java 17", "j2ee"]),
    "c++": ("programming", ["c++", "cpp"]),
    "c#": ("programming", ["c#", "csharp", "c sharp"]),
    "c": ("programming", ["c language", "\\bc\\b"]),
    "golang": ("programming", ["golang", "\\bgo\\b"]),
    "rust": ("programming", ["rust", "rustlang"]),
    "php": ("programming", ["php", "php7", "php8"]),
    "ruby": ("programming", ["ruby", "ruby on rails"]),
    "swift": ("programming", ["swift", "swiftui"]),
    "kotlin": ("programming", ["kotlin"]),
    "r": ("programming", ["\\br\\b", "r programming", "r-project"]),
    "scala": ("programming", ["scala"]),
    "dart": ("programming", ["dart", "flutter dart"]),
    "sql": ("database", ["sql", "t-sql", "pl/sql", "ansi sql"]),
    "shell": ("programming", ["bash", "shell scripting", "powershell", "zsh", "sh"]),

    # Frameworks & Libraries
    "django": ("framework", ["django", "django rest framework", "drf"]),
    "fastapi": ("framework", ["fastapi", "fast api"]),
    "flask": ("framework", ["flask"]),
    "react": ("framework", ["react", "react.js", "reactjs", "react native"]),
    "next.js": ("framework", ["next.js", "nextjs", "next"]),
    "vue.js": ("framework", ["vue", "vue.js", "vuejs", "vue 3"]),
    "angular": ("framework", ["angular", "angularjs", "angular 2+"]),
    "node.js": ("framework", ["node.js", "nodejs", "node"]),
    "express.js": ("framework", ["express", "express.js", "expressjs"]),
    "spring boot": ("framework", ["spring boot", "spring framework", "spring mvc", "spring"]),
    "asp.net": ("framework", ["asp.net", "asp.net core", ".net core", ".net", "dotnet"]),
    "laravel": ("framework", ["laravel"]),
    "pytorch": ("ai_ml_data", ["pytorch", "torch"]),
    "tensorflow": ("ai_ml_data", ["tensorflow", "tf", "keras"]),
    "scikit-learn": ("ai_ml_data", ["scikit-learn", "sklearn"]),
    "pandas": ("ai_ml_data", ["pandas"]),
    "numpy": ("ai_ml_data", ["numpy"]),
    "hugging face": ("ai_ml_data", ["hugging face", "huggingface", "transformers"]),
    "opencv": ("ai_ml_data", ["opencv", "computer vision"]),
    "bootstrap": ("framework", ["bootstrap", "bootstrap 5", "bootstrap 4"]),
    "tailwind css": ("framework", ["tailwind", "tailwindcss"]),
    "html5": ("framework", ["html", "html5"]),
    "css3": ("framework", ["css", "css3", "sass", "scss", "less"]),
    "jquery": ("framework", ["jquery"]),
    "redux": ("framework", ["redux", "redux toolkit"]),
    "graphql": ("framework", ["graphql", "apollo"]),
    "rest api": ("framework", ["rest", "rest api", "restful", "restful apis", "web services"]),

    # Databases & Storage
    "mysql": ("database", ["mysql"]),
    "postgresql": ("database", ["postgresql", "postgres", "psql"]),
    "mongodb": ("database", ["mongodb", "mongo"]),
    "redis": ("database", ["redis"]),
    "sqlite": ("database", ["sqlite", "sqlite3"]),
    "oracle": ("database", ["oracle database", "oracle db", "oracle sql"]),
    "microsoft sql server": ("database", ["sql server", "ms sql", "mssql"]),
    "elasticsearch": ("database", ["elasticsearch", "elastic search", "elk"]),

    # Cloud & DevOps
    "aws": ("cloud_devops", ["aws", "amazon web services", "ec2", "s3", "lambda"]),
    "azure": ("cloud_devops", ["azure", "microsoft azure"]),
    "gcp": ("cloud_devops", ["gcp", "google cloud", "google cloud platform"]),
    "docker": ("cloud_devops", ["docker", "containerization"]),
    "kubernetes": ("cloud_devops", ["kubernetes", "k8s"]),
    "terraform": ("cloud_devops", ["terraform", "iac", "infrastructure as code"]),
    "ci/cd": ("cloud_devops", ["ci/cd", "continuous integration", "continuous deployment", "cicd"]),
    "jenkins": ("cloud_devops", ["jenkins"]),
    "github actions": ("cloud_devops", ["github actions", "gitlab ci"]),
    "linux": ("cloud_devops", ["linux", "ubuntu", "centos", "redhat", "debian"]),
    "nginx": ("cloud_devops", ["nginx", "apache web server"]),

    # AI, ML & Data Science
    "machine learning": ("ai_ml_data", ["machine learning", "\\bml\\b", "supervised learning"]),
    "deep learning": ("ai_ml_data", ["deep learning", "\\bdl\\b", "neural networks", "cnn", "rnn"]),
    "natural language processing": ("ai_ml_data", ["natural language processing", "\\bnlp\\b"]),
    "large language models": ("ai_ml_data", ["llm", "llms", "large language models", "generative ai", "genai"]),
    "data science": ("ai_ml_data", ["data science", "data analysis", "data analytics"]),
    "power bi": ("ai_ml_data", ["power bi", "powerbi", "tableau"]),
    "apache spark": ("ai_ml_data", ["spark", "apache spark", "pyspark"]),

    # Developer Tools & Soft Skills
    "git": ("tools", ["git", "github", "gitlab", "bitbucket"]),
    "jira": ("tools", ["jira", "confluence", "trello"]),
    "postman": ("tools", ["postman", "swagger", "openapi"]),
    "pytest": ("tools", ["pytest", "unittest", "selenium"]),
    "agile": ("soft_skills", ["agile", "scrum", "kanban"]),
    "problem solving": ("soft_skills", ["problem solving", "analytical thinking"]),
    "communication": ("soft_skills", ["communication", "team collaboration"]),
    "leadership": ("soft_skills", ["leadership", "mentoring", "project management"]),
}

def extract_skills_from_text(text: str) -> List[Dict[str, str]]:
    """Extract skills and categories from input text using taxonomy matching."""
    if not text:
        return []

    text_lower = " " + text.lower() + " "
    found_skills: Dict[str, Dict[str, str]] = {}

    for canonical_name, (category, aliases) in MASTER_SKILL_TAXONOMY.items():
        for alias in aliases:
            if alias.startswith("\\b"):
                pattern = alias
            else:
                escaped = re.escape(alias)
                pattern = rf"(?<![\w#+.-]){escaped}(?![\w#+.-])"

            if re.search(pattern, text_lower, re.IGNORECASE):
                display_name = canonical_name.title()
                if canonical_name in ["sql", "html5", "css3", "aws", "gcp", "ci/cd", "jira", "llm", "ai", "ml", "nlp", "rest api"]:
                    display_name = canonical_name.upper()
                elif canonical_name in ["c++", "c#", ".net", "node.js", "vue.js", "next.js", "express.js", "power bi"]:
                    display_name = canonical_name.upper() if canonical_name in ["c++", "c#"] else canonical_name.title()

                found_skills[canonical_name] = {
                    "name": display_name,
                    "canonical": canonical_name,
                    "category": category,
                    "matched_alias": alias
                }
                break

    return list(found_skills.values())
