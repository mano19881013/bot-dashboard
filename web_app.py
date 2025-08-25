# web_app.py
from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os

try:
    from github import Github, GithubException
    IS_GITHUB_AVAILABLE = True
except ImportError:
    IS_GITHUB_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret_key_for_local_dev")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "999999")

def update_github_file(repo_full_name, file_path, token, data, commit_message):
    """Creates or updates a file in a GitHub repository."""
    if not IS_GITHUB_AVAILABLE:
        raise ConnectionError("PyGithub library not installed on server.")
    
    g = Github(token)
    repo = g.get_repo(repo_full_name)
    content_str = json.dumps(data, indent=2, ensure_ascii=False)
    
    try:
        contents = repo.get_contents(file_path, ref="main")
        repo.update_file(contents.path, commit_message, content_str, contents.sha, branch="main")
        return "File updated successfully."
    except GithubException as e:
        if e.status == 404:
            repo.create_file(file_path, commit_message, content_str, branch="main")
            return "File created successfully."
        else:
            raise e

@app.route('/', methods=['GET', 'POST'])
def home():
    # For GET request, we try to fetch current settings to display them
    current_settings = {}
    if request.method == 'GET':
        # This part is for display only and has a limitation: it needs a token to read.
        # We will pre-fill from request args if available, or just show empty boxes.
        pass

    if request.method == 'POST':
        password = request.form.get('password')
        if password != ADMIN_PASSWORD:
            flash("Admin password incorrect!", "error")
            return redirect(url_for('home'))

        # All settings are taken from the form
        settings = {
            "github_token": request.form.get('github_token'),
            "github_user": request.form.get('github_user'),
            "github_repo": request.form.get('github_repo'),
            "github_timers_file": request.form.get('github_timers_file'),
            "github_events_file": request.form.get('github_events_file'),
            "send_discord": 'send_discord' in request.form,
            "discord_token": request.form.get('discord_token'),
            "discord_high_level_channels": request.form.get('discord_high_level_channels'),
            "discord_all_channels": request.form.get('discord_all_channels'),
        }

        try:
            repo_full_name = f"{settings['github_user']}/{settings['github_repo']}"
            commit_message = "Update settings from web dashboard"
            # We use the token from the form to authorize the update
            update_github_file(repo_full_name, "settings.json", settings['github_token'], settings, commit_message)
            flash("Settings successfully saved to GitHub! The bot will apply them within 5 minutes.", "success")
        except Exception as e:
            flash(f"Failed to save settings to GitHub: {e}", "error")

        return redirect(url_for('home'))
    
    return render_template('index.html', settings=current_settings)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)