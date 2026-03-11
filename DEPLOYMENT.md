## Streamlit Community Cloud

This project is ready to deploy on Streamlit Community Cloud.

Repository settings:
- Repository: `ashish9312/Reconsphere`
- Branch: `main`
- App file: `app.py`

Recommended advanced setting:
- Python version: `3.11`

Why `3.11`:
- This is a compatibility recommendation for the `torch`, `torchvision`, and `facenet-pytorch` stack.

Deployment steps:
1. Open `https://share.streamlit.io/`
2. Sign in with GitHub.
3. Click `Create app`.
4. Select repo `ashish9312/Reconsphere`.
5. Select branch `main`.
6. Set the main file path to `app.py`.
7. In advanced settings, choose Python `3.11`.
8. Click `Deploy`.

Notes:
- The currently deployable modules are the face match, email leak, and phone leak tools.
- The dark web scanner is intentionally not loaded by `app.py` for cloud deployment stability.
