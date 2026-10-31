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

## Login persistence and performance

Successful login creates a seven-day browser cookie containing a random session token. The database stores only its SHA-256 hash and expiry; identity and teacher privileges are looked up on the server. Refreshing the page or opening another tab in the same browser restores login. Clicking **Çıxış (Log out)** revokes that session and removes the cookie. The browser must allow cookies or local storage. In a shared browser, log out when finished.

The component reads the session token directly from browser storage on each new connection, including deployments whose proxy omits cookie headers. Local storage provides a fallback when cookies are unavailable. The dashboard is shown only after the browser acknowledges saving the login.

The same-origin cookie component is bundled locally and needs no third-party script or additional secret. Cookies use `SameSite=Lax` and `Secure` on HTTPS. This JavaScript-managed cookie cannot be `HttpOnly`; a deployment with a dedicated authentication backend can provide that additional protection. With Supabase, sessions survive application restarts; local SQLite storage remains subject to the persistence limitations above.

The quiz timer updates only its own display and makes no database requests while counting down. The server still enforces the deadline when accepting answers or grading. Teacher provisioning runs during cached resource initialization, existing teacher accounts skip password rehashing, dashboard queries omit question snapshots and reuse the duration value, and closed teacher tabs do not compute statistics or generate spreadsheets. The first request after a free hosting service wakes up can still take longer.

## Features

- Student registration with full name, email, and password. Teacher privileges are restricted to the configured account.
- Sample Oracle SQL and PL/SQL questions, loaded using the **“Nümunə sualları əlavə et” (Add sample questions)** button in the teacher panel.
- A–D answer choices, Markdown SQL code blocks, previous/next navigation, and a timer that refreshes every second.
- Server-enforced deadlines and server-side answer storage. Active quizzes resume after login, and closing the session does not pause the timer.
- Answer keys remain hidden during a quiz. Scores, percentages, and explanations become available after submission.
- A question bank with editing, deletion, topics, and points per question. The shared quiz duration can be set to 1–180 minutes. Each topic quiz includes all active questions in that topic.
- CSV/XLSX question imports, a CSV template, student results, question difficulty statistics, and Excel result exports.
- Question snapshots for active quizzes, so later edits do not change how an existing attempt is graded.

## Automatic Excel and CSV imports

In **Teacher panel → Excel / CSV**, choose a file. The app validates and imports it automatically; no separate submit button is needed. The `Oracle_SQL_15_Test_Suallari.xlsx` layout is supported directly:

| Workbook column | Application field |
| --- | --- |
| Sual | Question text |
| Variant A, Variant B, Variant C, Variant D | Answer choices |
| Düzgün cavab | Correct answer, A–D |
| Qısa izah | Explanation |
| Mövzu (optional) | Topic |
| Bal (optional) | Points |

The number column is ignored. If topic or points are missing, the defaults selected before upload apply: **Oracle SQL**, **1 point**. English template headers are also supported. The app preserves SQL text and line breaks, accepts up to 500 questions and 5 MB per file, and shows a row-specific message when validation fails. A file is validated before any questions are written, and the import is committed in one transaction. Identical active questions are skipped, including repeated rows in the same file or a subsequent upload. Deleted questions can be deliberately reimported as new questions.

After a successful import, the questions are immediately available in the question bank and topic quizzes. The teacher sees the added/skipped counts and a preview. The uploaded workbook and its answer key are not committed to the GitHub repository.

## Navigation and question management

Click the **SQL Quiz Academy** logo at the top of the sidebar to return to the overview. Topic search on the overview and text/topic filters in the question bank make it easier to find content. The overview offers a **resume quiz** action when an unfinished attempt exists. During a quiz, the question selector shows answered questions, progress tracks saved answers, and an unanswered-question count appears before submission.

Deleting a question now removes it from the question bank, topic cards, active quiz snapshots, completed answer reviews, and question statistics. Completed scores and spreadsheet exports are recalculated using the remaining questions. Attempts with no questions left are removed. Remaining answers are remapped by question identity so deletion cannot assign an answer to a different question. The teacher panel explains these effects before confirmation. Other open browser tabs reflect the change on their next interaction or refresh.

On first startup after this update, a one-time migration also removes previously deactivated questions from existing attempt snapshots. Editing a question still preserves the original version in existing attempts; deletion explicitly removes that version everywhere. These changes take effect when the updated app starts against your database.

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

Automated tests cover authentication, teacher authorization, answer-key privacy, server-enforced deadlines, score calculation, repeated quiz submission, session expiry and revocation, and Streamlit login, quiz, and teacher-panel workflows.

Optional real-browser checks use Playwright and Chromium:

```bash
.venv/bin/python -m pip install playwright==1.62.0
.venv/bin/python -m playwright install chromium
.venv/bin/python tests/browser_smoke.py
```

The browser check starts a temporary application and database, checks teacher/student login across refreshes and new tabs, verifies logout and rejection of a revoked cookie, exercises teacher tabs, and confirms that idle timer ticks make no database calls. Set `CHROMIUM_PATH` to use an existing Chromium executable instead of a Playwright-managed browser.

## Current limitations

This initial version does not include email verification, password recovery, MFA, shared login rate limiting, or management of separately named quizzes. Start with personal use or a small pilot. Before wider public use, add these capabilities and configure database backups.
