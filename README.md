# EMOJI in messages handler by Slack

- Required get Slack OAuth Token
- Required add bot to channel and get id channel to configure environments

## RUN
```bash
python3 -m venv .venv
source .venv/bin/activate
# Configure .env
pip install -r requirements.txt
python main.py
```

TODO:
- Control ratelimit and duplicate events
- Control threads emoji including in messages
- Normalize server and code
- Manage max EMOJI by day sender
- Reports by user_id
- unit tests
