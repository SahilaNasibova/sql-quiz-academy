# SQL Quiz Academy

An Oracle SQL and PL/SQL quiz platform with an Azerbaijani user interface. Built with Streamlit, it features a dark sidebar, a purple welcome banner, live statistics, and topic cards.

## Run locally

Use Python 3.12:

```bash
cd /workspace/sql-quiz-academy
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py --server.address 0.0.0.0
```

SQLite is created automatically for local development. Use Supabase PostgreSQL for persistent storage in a public deployment. Local SQLite data may be lost when Streamlit Community Cloud restarts the application.

## Teacher account and secrets

The default teacher email is `sahila.nasibova1@gmail.com`. Public registration is blocked for this address. The account is created only when `TEACHER_PASSWORD` is configured on the server. The password must contain at least 10 characters and is hashed with scrypt. Changing this variable does not change an existing account's password. You can remove it from the configuration after the account has been created.

Add the following settings in **Streamlit Community Cloud → App settings → Secrets**. Keep passwords out of GitHub and chat. For local development, you can use the same settings in `.streamlit/secrets.toml`, which is ignored by Git.

```toml
TEACHER_EMAIL = "sahila.nasibova1@gmail.com"
# TEACHER_PASSWORD = set your own strong initial password here
# DATABASE_URL = your Supabase SQLAlchemy connection URL
```

The `DATABASE_URL` format is:

```text
postgresql+psycopg://USER:URL_ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require
```

Use **Supabase → Connect → Session pooler** for IPv4 support. The username is typically `postgres.PROJECT_REF`. Special characters in the password must be URL-encoded. Store connection credentials only in Secrets.

For PostgreSQL, the application creates a separate `quiz_academy` schema instead of using Supabase's default `public` schema. Keep this schema out of the Supabase Data API's exposed schemas and do not grant access to the `anon` or `authenticated` roles. The initial connection role must have permission to create schemas and tables. The application uses a server-side PostgreSQL connection only. The Supabase connection has not yet been validated in this environment; test it against your own project before deployment.

## Features

- Student registration with full name, email, and password. Teacher privileges are restricted to the configured account.
- Sample Oracle SQL and PL/SQL questions, loaded using the **“Nümunə sualları əlavə et” (Add sample questions)** button in the teacher panel.
- A–D answer choices, Markdown SQL code blocks, previous/next navigation, and a timer that refreshes every second.
- Server-enforced deadlines and server-side answer storage. Active quizzes resume after login, and closing the session does not pause the timer.
- Answer keys remain hidden during a quiz. Scores, percentages, and explanations become available after submission.
- A question bank with editing, deletion, topics, and points per question. The shared quiz duration can be set to 1–180 minutes. Each topic quiz includes all active questions in that topic.
- CSV/XLSX question imports, a CSV template, student results, question difficulty statistics, and Excel result exports.
- Question snapshots for active quizzes, so later edits do not change how an existing attempt is graded.

## Deploy to Streamlit Community Cloud

1. Create a free Supabase project and configure the server connection and database access restrictions.
2. Sign in to Streamlit Community Cloud with your GitHub account. Select this repository, the `main` branch, and `app.py` as the entry point. Choose Python 3.12.
3. In **Advanced settings / Secrets**, configure `DATABASE_URL`, `TEACHER_EMAIL`, and the initial `TEACHER_PASSWORD`.
4. Deploy the application, sign in as the teacher, and add the sample questions.
5. Create a separate student account and complete a quiz. Check the navigation, answer choices, and results on a phone as well. Then share the actual `*.streamlit.app` URL provided by Streamlit.

Free plans may include application sleep, database pausing, storage limits, and compute limits. Check the current Streamlit and Supabase limits in your account dashboards. This application provides multiple-choice SQL/PLSQL knowledge assessments; it does not execute SQL against an Oracle server.

## Tests

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

Automated tests cover authentication, teacher authorization, answer-key privacy, server-enforced deadlines, score calculation, repeated quiz submission, and Streamlit login, quiz, and teacher-panel workflows.

## Current limitations

This initial version does not include email verification, password recovery, MFA, shared login rate limiting, or management of separately named quizzes. Start with personal use or a small pilot. Before wider public use, add these capabilities and configure database backups.
