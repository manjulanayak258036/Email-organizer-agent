# Email Organizer Agent

An agentic AI project that triages Gmail threads, extracts action items, drafts responses, and presents results through a human-review dashboard.

## Features

- Classifies email senders and urgency using grounded evidence
- Extracts deadlines, commitments, and follow-up tasks
- Builds review-ready draft replies
- Maintains an auditable execution trail
- Supports a 14-lab modular agent-development progression
- Provides a Streamlit dashboard for mailbox-owner review and approval

## Project Structure

- `core/` — shared email, authentication, classification, and model components
- `dashboard/` — human review dashboard
- `lab01_agent_loop/` through `lab14_capstone/` — progressive agent architecture labs
- `auth_login.py` — Gmail OAuth login helper
- `requirements.txt` — Python dependencies
- `SUBMISSION.md` — academic submission and acceptance matrix
- `walkthrough.md` — project walkthrough

## Requirements

- Python 3.10 or newer
- A Google Cloud project with Gmail API access
- Internet access for Gmail OAuth authentication

## Setup

1. Create and activate a Python virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Configure Google OAuth credentials:
   - Create OAuth credentials in Google Cloud Console.
   - Place the downloaded `credentials.json` file in the repository root.
   - The file is ignored by Git and must not be committed.

4. Sign in to Google:

   ```powershell
   python auth_login.py
   ```

5. Start the dashboard:

   ```powershell
   streamlit run dashboard/app.py
   ```

## Run the Labs

Run each lab from the repository root:

```powershell
python lab01_agent_loop/demo_lab01.py
python lab02_tools/demo_lab02.py
python lab03_skills/demo_lab03.py
python lab04_memory/demo_lab04.py
python lab05_connector/demo_lab05.py
python lab06_runtime/demo_lab06.py
python lab07_node_graph/demo_lab07.py
python lab08_parallel_swarm/demo_lab08.py
python lab09_grounding/demo_lab09.py
python lab10_self_healing/demo_lab10.py
python lab11_sdlc_factory/demo_lab11.py
python lab12_governance/demo_lab12.py
python lab13_specialists/demo_lab13.py
python lab14_capstone/demo_lab14.py
```

## Security

Sensitive files are excluded from Git by `.gitignore`, including:

- `credentials.json`
- `token.json`
- `.env`
- private keys and PEM files
- local logs and checkpoints

Do not commit credentials, access tokens, Gmail data, or personal mailbox content.

## License

This project is provided for educational and demonstration purposes. Review the repository owner’s applicable license before commercial use or redistribution.
