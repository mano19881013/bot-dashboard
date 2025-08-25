# bot_worker.py
import datetime
import os
import json
import time
import threading
import requests
import asyncio
import websockets
from collections import deque

try:
    from github import Github, GithubException
    IS_GITHUB_AVAILABLE = True
except ImportError:
    IS_GITHUB_AVAILABLE = False
    print("WARNING: PyGithub is not installed. Cloud sync functionality will be limited.")

class CloudBot:
    def __init__(self):
        self.log_entries = deque()
        self.log_lock = threading.Lock()
        
        self.settings = {}
        self.game_profile = {}
        self.timers_config = []
        self.floating_timers_data = []
        self.fixed_timers_data = []
        self.fixed_timers_with_date = []
        self.sorted_timers_data = []
        self.custom_events = {}
        self.respawn_intervals = {}
        self.sent_notifications = set()
        
        self.github_client = None
        self.is_first_discord_connection = True
        self.last_sequence = None
        
        self.add_log("Cloud Bot Initializing...")

    def add_log(self, message):
        with self.log_lock:
            log_message = f"[{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] {message}"
            self.log_entries.append(log_message)
            if len(self.log_entries) > 200: self.log_entries.popleft()
            print(log_message)
            
    def get_utc_timestamp_str(self):
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def connect_to_github(self):
        if not IS_GITHUB_AVAILABLE: return False
        # The bot now uses the same token as the web UI for reading settings
        token = self.settings.get("github_token")
        if not token:
            self.add_log("GitHub Token not found in settings. Cannot connect.")
            return False
        try:
            if not self.github_client:
                self.github_client = Github(token)
                self.github_client.get_user().login
                self.add_log("GitHub connection successful.")
            return True
        except Exception as e:
            self.add_log(f"Failed to connect to GitHub: {e}")
            self.github_client = None
            return False

    def _get_repo(self):
        if not self.connect_to_github(): return None
        github_user = self.settings.get("github_user")
        github_repo_name = self.settings.get("github_repo")
        if not github_user or not github_repo_name: return None
        return self.github_client.get_repo(f"{github_user}/{github_repo_name}")

    def fetch_from_github(self, file_path, default_value={}):
        """A generic function to fetch and decode a JSON file from GitHub."""
        try:
            repo = self._get_repo()
            if not repo:
                self.add_log(f"Cannot fetch {file_path}, repo not available.")
                return default_value
            
            content_obj = repo.get_contents(file_path)
            content = content_obj.decoded_content.decode("utf-8")
            return json.loads(content)
        except GithubException as e:
            if e.status == 404:
                self.add_log(f"File not found on GitHub: {file_path}. Using default.")
            else:
                self.add_log(f"GitHub error fetching {file_path}: {e}")
            return default_value
        except Exception as e:
            self.add_log(f"Error fetching {file_path}: {e}")
            return default_value

    def load_all_data_from_cloud(self):
        self.add_log("Starting full data sync from GitHub...")
        
        # 1. Fetch settings first, as they are needed for other calls
        self.settings = self.fetch_from_github("settings.json")
        if not self.settings:
            self.add_log("CRITICAL: settings.json could not be loaded. Bot may not function correctly.")
            # Re-initialize github client with potentially new token
            self.github_client = None 

        # 2. Fetch game profile
        # This file should be in your repo root alongside the python scripts
        try:
            with open("game_profile.json", "r", encoding="utf-8") as f:
                self.game_profile = json.load(f)
                self.timers_config = self.game_profile.get("timers", [])
                self.add_log(f"Successfully loaded local game_profile.json: {self.game_profile.get('game_name', 'N/A')}")
        except Exception as e:
            self.add_log(f"CRITICAL: Could not read game_profile.json: {e}")

        # 3. Fetch timers and events data
        timers_data = self.fetch_from_github(self.settings.get("github_timers_file", "timers_data.json"))
        self.update_timers_data_from_remote(timers_data)

        events_data = self.fetch_from_github(self.settings.get("github_events_file", "custom_events.json"))
        self.update_events_data_from_remote(events_data)
        
        self.add_log("Full data sync from GitHub finished.")

    def update_timers_data_from_remote(self, remote_data):
        new_floating_data = []
        for timer_config in self.timers_config:
            if timer_config["type"] == "floating":
                timer_id = timer_config["id"]
                remote_info = remote_data.get(timer_id, {})
                new_floating_data.append({**timer_config, **remote_info})
        self.floating_timers_data = new_floating_data
        self.add_log("Timer data has been updated from remote source.")

    def update_events_data_from_remote(self, remote_data):
        if isinstance(remote_data, dict) and self.custom_events != remote_data:
             self.custom_events = remote_data
             self.add_log("Event data has been updated from remote source.")
    
    def refresh_timers(self):
        # This function and its dependencies remain the same as your original logic
        # For brevity, I'm keeping the stubs.
        # Make sure to copy the full logic from your V445.py file here.
        self.update_and_predict_timers()
        self.fixed_timers_with_date = self.set_fixed_timers_dates()
        confirmed, unconfirmed = [], []
        for t in self.floating_timers_data:
            if t.get("time") != "待確認" and t.get("date"):
                try: confirmed.append({**t, "spawn_dt": datetime.datetime.strptime(f"{t['date']} {t['time']}", "%Y-%m-%d %H:%M")})
                except (ValueError, TypeError): unconfirmed.append(t)
            else: unconfirmed.append(t)
        for t in self.fixed_timers_with_date:
            try: confirmed.append({**t, 'spawn_dt': datetime.datetime.strptime(f"{t['date']} {t['time']}", "%Y-%m-%d %H:%M")})
            except (ValueError, TypeError): unconfirmed.append(t)
        self.sorted_timers_data = sorted(confirmed, key=lambda x: x["spawn_dt"])

    def update_and_predict_timers(self):
        # PASTE FULL FUNCTION LOGIC FROM V445.py HERE
        pass

    def set_fixed_timers_dates(self):
        # PASTE FULL FUNCTION LOGIC FROM V445.py HERE
        # Make sure it returns a list of timers.
        now, today, tomorrow = datetime.datetime.now(), datetime.date.today(), datetime.date.today() + datetime.timedelta(days=1)
        timers = []
        fixed_data = [t for t in self.timers_config if t.get("type") == "fixed"]
        for timer in fixed_data:
            try:
                h, m = map(int, timer["time"].split(':'))
                timer_date = tomorrow if now.time() > datetime.time(h, m) else today
                timers.append({**timer, "date": timer_date.strftime("%Y-%m-%d")})
            except Exception as e: self.add_log(f"Error processing fixed timer {timer.get('name')}: {e}")
        return timers

    def check_all_notifications(self):
        self.refresh_timers()
        self._cleanup_sent_notifications()
        self.check_timer_notifications()
        self.check_custom_event_notifications()
        self.add_log("Notification check cycle complete.")

    def _cleanup_sent_notifications(self):
        # PASTE FULL FUNCTION LOGIC FROM V445.py HERE
        pass

    def check_timer_notifications(self):
        # PASTE FULL FUNCTION LOGIC FROM V445.py HERE
        # IMPORTANT: Change variables like `notify_level` to read from self.game_profile
        # Example: notify_level = self.game_profile.get("cloud_settings", {}).get("discord_high_level_boss_threshold", 62)
        pass

    def check_custom_event_notifications(self):
        # PASTE FULL FUNCTION LOGIC FROM V445.py HERE
        pass

    def send_discord_message(self, message, channel_list_str):
        if not self.settings.get("send_discord", False): return
        bot_token = self.settings.get("discord_token")
        if not bot_token or not channel_list_str: return
        channel_list = [cid.strip() for cid in channel_list_str.strip().split('\n') if cid.strip()]
        for cid in channel_list:
            url = f"https://discord.com/api/v10/channels/{cid}/messages"
            headers = {"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"}
            payload = {"content": message}
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                if response.status_code == 200: self.add_log(f"Successfully sent Discord message to channel {cid[:5]}...")
                else: self.add_log(f"Failed to send Discord message. Status: {response.status_code}, Response: {response.text}")
            except requests.RequestException as e: self.add_log(f"Network error sending Discord message: {e}")

    def run(self):
        self.add_log("Starting main loop...")
        
        schedule_interval_seconds = 60
        download_interval_seconds = 300 # 5 minutes
        last_download_time = 0

        while True:
            current_time = time.time()
            
            # Check if it's time to re-download all data from GitHub
            if current_time - last_download_time >= download_interval_seconds:
                self.load_all_data_from_cloud()
                last_download_time = current_time
            
            # Check for notifications based on current data
            if self.settings: # Only run checks if settings have been loaded
                self.check_all_notifications()
            else:
                self.add_log("Settings not loaded, skipping notification check.")

            time.sleep(schedule_interval_seconds)

if __name__ == "__main__":
    bot = CloudBot()
    # It's critical to paste your full functions here before running
    # bot.update_and_predict_timers = ... (from V445.py)
    # bot.check_timer_notifications = ... (from V445.py, remember to adapt variables)
    # ... etc.
    bot.run()