# Setup and deployment guide

This guide is for the ChatOps QA Automation Bot in `S:\USE\Summer Training`. It is a Python/FastAPI backend: Slack slash commands trigger a fixed Playwright/Pytest suite against SauceDemo, and SQLite stores run history. There is no separate frontend to install. Follow the numbered steps in order; tell me the step number and copy any error text if you get stuck.

## Part 1 — Prerequisites & Installation

### What you need

- Windows 10 or 11 and PowerShell for the local commands in this guide.
- 64-bit Python 3.10 or newer. This guide uses Python 3.12.10. Your Python 3.14 launcher entry currently points to a missing executable, so install a working runtime before proceeding.
- Git for Windows and a GitHub account for deployment.
- A Render account for hosting.
- Internet access to install packages, download Chromium, reach SauceDemo, and receive Slack requests.
- A Slack workspace only if you want to demonstrate the slash commands. Slack is optional for running the app and browser suite locally.
- Optional: VS Code or another text editor. Docker Desktop, Node.js, and Java are not required.

The project dependencies below are listed in `requirements.txt`; Step 10 installs them into the project's `.venv`, rather than globally:

| Package | Version range in `requirements.txt` | Purpose |
| --- | --- | --- |
| `fastapi` | `>=0.115,<1.0` | Web API and Slack webhook endpoint |
| `uvicorn` | `>=0.30,<1.0` | Local and hosted ASGI server |
| `httpx` | `>=0.27,<1.0` | Send completion messages to Slack |
| `python-dotenv` | `>=1.0,<2.0` | Load local `.env` settings |
| `pytest` | `>=8.0,<9.0` | Run the test suites |
| `pytest-playwright` | `>=0.5,<1.0` | Playwright's Pytest integration |
| `playwright` | `>=1.48,<2.0` | Browser automation library; Step 11 installs its matching Chromium build |

### Installation steps

**1. Confirm the project folder.** Open File Explorer and make sure `S:\USE\Summer Training` contains `requirements.txt`, `.env.example`, `chatops_qa`, and `tests`. If you saved the project somewhere else, use that folder in place of `S:\USE\Summer Training` in the commands below.

**2. Install a working Python runtime.** Download the [Python 3.12.10 Windows 64-bit installer](https://www.python.org/downloads/release/python-31210/) and run it. On the release page, choose **Windows installer (64-bit)**, not the embeddable package. In the installer, enable **Add python.exe to PATH** and complete installation. Then close and reopen PowerShell. This version is chosen because your listed Python 3.14 entry points to a file that is missing; Python 3.12 is not otherwise mandatory for the project.

**3. Check the Python installation.** Open a new PowerShell window and run:

```powershell
py -3.12 --version
```

The output should start with `Python 3.12`. If it still reports that a file cannot be found, rerun the Python 3.12.10 installer and choose **Repair** or **Modify** if offered, then retry. The project supports Python 3.10 or newer; Step 35 has recovery details.

**4. Install Git for Windows.** Download and install it from [git-scm.com/download/win](https://git-scm.com/download/win). The installer defaults are suitable. Reopen PowerShell and verify it with:

```powershell
git --version
```

**5. Prepare the online accounts.** Sign in to or create a GitHub account and a Render account. You will create an empty GitHub repository in Part 3. If using Slack, make sure you can create and install an app in your workspace. Do not put passwords or signing secrets in project source files or GitHub.

**6. Install an editor if you want one.** VS Code is optional; it is useful for editing `.env` and reading the source. You can use Notepad instead, so no editor installation is required.

## Part 2 — Local Setup

**7. Open PowerShell in the project folder.** Run:

```powershell
Set-Location "S:\USE\Summer Training"
```

**8. Create a project-specific Python environment.** This keeps the project's packages separate from other Python projects:

```powershell
py -3.12 -m venv .venv
```

**9. Update pip inside that environment.**

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

**10. Install the packages listed by the project.** This installs FastAPI, Uvicorn, HTTPX, dotenv, Pytest, and Playwright packages into `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**11. Download the Playwright Chromium browser.** Playwright requires the browser build that matches its installed package:

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
```

The same version-matching requirement and browser installation command are documented by [Playwright](https://playwright.dev/python/docs/browsers).

**12. Create the local environment file.** `.env.example` is a template; `.env` is the private configuration file the app reads at startup. The command below preserves an existing `.env` instead of overwriting it:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

**13. Set the local configuration in Notepad.** Make sure the lines in `.env` are as follows. Leave the Slack secret empty for local use without Slack; if you already have a Slack app, replace it with that app's Signing Secret. Do not include quote marks or spaces around `=`.

```dotenv
SLACK_SIGNING_SECRET=
DATABASE_PATH=data/chatops.sqlite3
SAUCEDEMO_BASE_URL=https://www.saucedemo.com/
SAUCEDEMO_USERNAME=standard_user
SAUCEDEMO_PASSWORD=secret_sauce
TEST_RUN_TIMEOUT_SECONDS=900
```

Save and close Notepad. The username and password are SauceDemo's example practice credentials. Never commit `.env` or share the Slack Signing Secret. The provided `.gitignore` excludes `.env` from Git.

**14. Start the local web service.** In the same PowerShell window, run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn chatops_qa.app:app --host 127.0.0.1 --port 8000
```

Keep this window open while demonstrating the app. To stop it later, press **Ctrl+C** in this window.

**15. Check that the service started.** Open a second PowerShell window and run:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

You should see `status: ok`. With `SLACK_SIGNING_SECRET=` empty, `slack_configured` should be `False`; that is expected when Slack is not configured.

**16. Optionally demonstrate the browser suite locally.** In the second PowerShell window, change to the project folder if needed, then run:

```powershell
Set-Location "S:\USE\Summer Training"
.\.venv\Scripts\python.exe -m pytest tests/saucedemo -q
```

This opens Chromium in headless mode and needs internet access to SauceDemo. The suite can take time, and failures can occur if the external SauceDemo site is unavailable.

**17. Optionally check the unit tests.** These check command parsing and Slack request-signature behavior:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit -q
```

This step is optional for a basic local demonstration.

## Part 3 — Deployment

### Push the project to GitHub

**18. Create an empty GitHub repository.** In GitHub, choose **New repository**, give it a name such as `chatops-qa-bot`, and create it without adding a README, license, or `.gitignore`. Keep the repository private if it is only for your class. Copy its HTTPS URL.

**19. Initialize Git and review the files to be uploaded.** In PowerShell, make sure you are at the project root, then run:

```powershell
Set-Location "S:\USE\Summer Training"
git init
git add .
git status
```

Before continuing, check the status output: `.env`, `.venv`, the local database, reports, temporary files, and ZIP archives should not be staged. `.env.example` is safe to upload because it contains only sample settings.

**20. Commit the source code.**

```powershell
git commit -m "Prepare ChatOps QA bot for deployment"
git branch -M main
```

If Git asks who you are, set your own GitHub name and email, then repeat the commit:

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git commit -m "Prepare ChatOps QA bot for deployment"
```

**21. Connect the local project to GitHub and upload it.** Replace the sample URL with the HTTPS URL copied in Step 18:

```powershell
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

If GitHub asks you to sign in, complete its browser-based sign-in prompt and retry the push if necessary.

### Create and configure the live Render service

**22. Create a Render web service from your GitHub repository.** In Render, choose **New + → Web Service**, connect GitHub if asked, and select the repository and `main` branch. Render can build a service directly from the repository's Dockerfile; see [Render's Docker deployment instructions](https://render.com/docs/docker).

**23. Set the Docker build options.** Choose **Docker** for the runtime/language. Set Dockerfile path to `./Dockerfile` and build context/root directory to `.` (the repository root). Leave the Docker command/start command empty so Render uses the `CMD` already in the Dockerfile. The Docker build installs the Python packages, Chromium, and its Linux dependencies; a first build may take several minutes.

**24. Choose the service plan and decide whether history must persist.** For persistent SQLite run history, select a paid web-service plan that supports a persistent disk. Add a disk mounted at `/var/data`. A free service can be used for a temporary demonstration if Render offers it for your setup, but it cannot attach a persistent disk, may sleep while idle, and loses its local SQLite data on restart or spin-down. See [Render's free-service limits](https://render.com/docs/free).

**25. Add the Render environment variables.** In the new service's **Environment** settings, add:

| Name | Value |
| --- | --- |
| `DATABASE_PATH` | `/var/data/chatops.sqlite3` |
| `SAUCEDEMO_BASE_URL` | `https://www.saucedemo.com/` |
| `SAUCEDEMO_USERNAME` | `standard_user` |
| `SAUCEDEMO_PASSWORD` | `secret_sauce` |
| `TEST_RUN_TIMEOUT_SECONDS` | `900` |

Add `SLACK_SIGNING_SECRET` in Step 29 if you will connect Slack. Store secrets only in Render's Environment settings. Render supplies `PORT`; the Dockerfile reads that value and binds Uvicorn to `0.0.0.0`, which Render requires. See [Render web-service port settings](https://render.com/docs/web-services).

**26. Set the health check and deploy.** In the service's advanced/settings options, set health check path to `/healthz`, then create the service. Wait for the Docker build and deployment to complete. If deployment fails, open the service's **Events** or **Logs** and read the first reported build/runtime error.

**27. Verify the public service.** Copy the public service URL shown in Render and open this URL in a browser, replacing `<service-name>` with the actual service name:

```text
https://<service-name>.onrender.com/healthz
```

The response should include `"status":"ok"`. If you have not configured Slack, `slack_configured` will be `false` until you do so.

### Optional: connect Slack slash commands

**28. Create a Slack app and copy its Signing Secret.** Open [Slack API: Your Apps](https://api.slack.com/apps), create an app for your workspace, then open **Basic Information → App Credentials** and copy **Signing Secret**. Slack slash commands send requests to their configured Request URL and can use a temporary `response_url` to send a later reply; see [Slack's slash-command documentation](https://docs.slack.dev/interactivity/implementing-slash-commands/).

**29. Save the Signing Secret in Render.** In the Render service's **Environment** settings, add `SLACK_SIGNING_SECRET` with the copied value, save, and wait for Render to restart/redeploy. Do not use a Slack verification token; the project validates Slack's signed request using the Signing Secret.

**30. Create the `/run-tests` command in Slack.** In the Slack app's **Slash Commands** section, create `/run-tests`. Set its Request URL to:

```text
https://<service-name>.onrender.com/slack/commands
```

Use `ui` as its usage hint, then save it.

**31. Create the `/test-history` command in Slack.** Add another slash command named `/test-history`, set the same Request URL, use `[count 1-20]` as the usage hint, and save it.

**32. Install the Slack app into your workspace.** Use the app's **Install to Workspace** or **Reinstall to Workspace** action and complete Slack's authorization prompt. The app replies using the command's `response_url`, so this project does not require a bot OAuth token for these two commands.

**33. Verify Slack is connected.** Open the Render health URL from Step 27 again. It should now include `"slack_configured":true`.

**34. Demonstrate the live commands to your teacher.** In a Slack channel where the app is available, run:

```text
/test-history
/run-tests ui
```

The history command should show recent runs. The run command should acknowledge first, then post a result after the SauceDemo browser suite completes. Keep the Render service healthy while the test runs.

### If something goes wrong

**35. If Step 3 still points to a missing Python executable,** install or repair Python 3.12.10 using the official [Windows 64-bit installer](https://www.python.org/downloads/release/python-31210/), then close and reopen PowerShell. Run `py --list` to check that 3.12 appears, and retry `py -3.12 --version`. A stale 3.14 entry can remain in the list; use the working 3.12 entry.

**36. If package installation fails while building `PyYAML`,** check which interpreter the virtual environment uses:

```powershell
Set-Location "S:\USE\Summer Training"
.\.venv\Scripts\python.exe --version
py -0p
py -3.12 --version
```

Your pasted error includes `cp315` and `Python315`, which means that environment is using Python 3.15. If the virtual environment prints Python 3.15 (or another version) while `py -3.12` prints Python 3.12, recreate only the generated `.venv` folder with Python 3.12, then reinstall the packages:

```powershell
Remove-Item -LiteralPath .venv -Recurse -Force
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Before continuing, verify the version command prints `Python 3.12.x`. If `py -3.12 --version` says that version is not installed, install Python 3.12 as described in Steps 2–3, reopen PowerShell, and repeat. You should not need Microsoft C++ Build Tools for this project when using Python 3.12. Playwright's Chromium download is separate; after pip succeeds, continue with Step 11.

**37. If `/healthz` does not return `ok`,** keep the local server terminal open and read its error. On Render, check **Events/Logs**, confirm the health path is `/healthz`, and confirm the container uses the supplied Dockerfile.

**38. If Slack reports an invalid signature,** re-copy the Slack app's Signing Secret into Render's `SLACK_SIGNING_SECRET` variable and wait for the service to restart. Do not use a verification token.

**39. If Slack cannot verify its Request URL,** make sure the service is deployed and healthy, and both slash commands use the exact public HTTPS URL ending in `/slack/commands`.

**40. If test history disappears after a restart,** confirm the persistent disk is mounted at `/var/data` and `DATABASE_PATH` is exactly `/var/data/chatops.sqlite3`. Only files stored beneath the mounted directory persist. A Render disk is attached to one service instance and disables zero-downtime deploys; see [disk behavior and limits](https://render.com/docs/disks).

**41. If a running test is interrupted during deployment,** restart the command after deployment finishes. This training app runs jobs in the web service process; it does not have a durable queue to resume interrupted jobs. For a production service, move jobs to a durable queue/worker and history to a managed database.

The included deployment is suitable for a class demonstration or small training project. It is a single-instance FastAPI service with SQLite and in-process background tasks, not a production-grade distributed job system.
