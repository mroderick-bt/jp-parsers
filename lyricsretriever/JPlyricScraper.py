import requests
import tempfile
import re
import os
import time
import threading
import time
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from shared.JMRParser import create_docx_with_eq_fields, generate_obsidian_lyric_file

from bs4 import BeautifulSoup

import tkinter as tk
from tkinter import ttk, filedialog

BASE_URL = "https://www.uta-net.com"
REQUEST_DELAY = 1.0

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://www.uta-net.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

def set_buttons_state(self, state="normal"):
    for child in self.winfo_children():
        for btn in child.winfo_children():
            if isinstance(btn, ttk.Button):
                btn.config(state=state)

def create_docx_from_lyrics(lyrics_text, output_path):
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False, suffix=".txt") as tmp:
        tmp.write(lyrics_text)
        tmp.flush()
        create_docx_with_eq_fields(tmp.name, output_path)

def sanitize_filename(text):
    return re.sub(r'[\\/:\*\?"<>|]', '_', text)

def fetch_lyrics(song_url):
    time.sleep(REQUEST_DELAY)
    res = requests.get(song_url, headers=headers)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    div = soup.find('div', itemprop='lyrics')
    if not div:
        return ""
    for br in div.find_all("br"):
        br.replace_with("\n")
    text = div.get_text().strip()

    # Remove promotional lines
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        if line.startswith("この歌詞をマイ歌ネットに登録") or line.startswith("このアーティストをマイ歌ネットに登録"):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)

def search_artist(japanese_name):
    url = f"{BASE_URL}/search/?Aselect=1&Bselect=1&Keyword={requests.utils.quote(japanese_name)}"
    res = requests.get(url, headers=headers)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    results = []
    for row in soup.select("tbody.songlist-table-body tr.border-bottom"):
        a_tag = row.select_one("a.d-block")
        if not a_tag:
            continue
        href = a_tag.get("href")
        match = re.search(r"/artist/(\d+)/", href)
        if not match:
            continue
        artist_id = match.group(1)
        artist_name_tag = a_tag.select_one("span.fw-bold")
        artist_name = artist_name_tag.text.strip() if artist_name_tag else a_tag.text.strip()
        results.append((artist_id, artist_name))
        if len(results) >= 5:
            break
    return results

def fetch_artist_album_page(artist_id):
    url = f"{BASE_URL}/user/search_index/artist.html?AID={artist_id}"
    res = requests.get(url, headers=headers)
    res.encoding = 'utf-8'
    return BeautifulSoup(res.text, 'html.parser')

def get_albums_and_tracks(soup):
    albums = []
    tables = soup.find_all("table", class_="album_table")
    print(f"Found {len(tables)} album tables")
    for tbl in tables:
        title_elem = tbl.select_one("div.album_title a")
        if not title_elem:
            continue
        album_title = title_elem.text.strip()

        release_date = get_release_date(tbl)

        track_links = []
        for li in tbl.select("li a"):
            href = li.get("href")
            track_links.append((li.text.strip(), BASE_URL + href))
        albums.append((album_title, release_date, track_links))
        albums.sort(key=lambda x: (x[1] or "9999"))
    return albums

def get_release_date(album_table):
    dl = album_table.find("dl", class_="clearfix")
    if not dl:
        return None
    dt_tags = dl.find_all("dt")
    for dt in dt_tags:
        if dt.text.strip() == "発売日：":
            dd = dt.find_next_sibling("dd")
            if dd:
                return dd.text.strip().split("/")[0]
    return None

def search_songs(song_title):
    url = f"{BASE_URL}/search/?Aselect=2&Bselect=3&Keyword={requests.utils.quote(song_title)}"
    res = requests.get(url, headers=headers)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    results = []
    for row in soup.select("tbody.songlist-table-body tr.border-bottom"):
        a_tag = row.select_one("td.sp-w-100 a")  # selects the <a> inside the first td cell
        if not a_tag:
            continue
        href = a_tag.get("href")
        full_url = BASE_URL + href
        title_span = a_tag.select_one("span.songlist-title")
        title = title_span.text.strip() if title_span else a_tag.text.strip()
        tds = row.find_all("td")
        artist_name = tds[1].text.strip() if len(tds) > 1 else "Unknown"
        results.append((title, artist_name, full_url))
        if len(results) >= 10:
            break
    # print(str(soup.select_one("tbody.songlist-table-body tr.border-bottom")))
    # print(f"Title: {title}, Artist: {artist_name}, URL: {full_url}")
    return results

class UtaNetScraperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Uta-net Lyrics Scraper")
        self.geometry("700x500")

        self.save_path = tk.StringVar(value=os.path.abspath("lyrics"))
        self.save_path = tk.StringVar(value="C:/Sync")

        # UI setup (same as before)...
        search_frame = ttk.LabelFrame(self, text="Search")
        search_frame.pack(fill="x", padx=10, pady=10)

        self.search_var = tk.StringVar()
        ttk.Label(search_frame, text="Search term (Artist ID/Name or Song Title):").pack(side="left", padx=5)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side="left", padx=5)

        ttk.Button(search_frame, text="Search Artist", command=self.threaded_search_artist).pack(side="left", padx=5)
        ttk.Button(search_frame, text="Search Song", command=self.threaded_search_song).pack(side="left", padx=5)

        path_frame = ttk.Frame(self)
        path_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(path_frame, text="Save folder:").pack(side="left")
        ttk.Entry(path_frame, textvariable=self.save_path, width=50).pack(side="left", padx=5)
        ttk.Button(path_frame, text="Browse", command=self.browse_folder).pack(side="left")

        results_frame = ttk.LabelFrame(self, text="Results")
        results_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.results_list = tk.Listbox(results_frame, selectmode=tk.EXTENDED)
        self.results_list.pack(fill="both", expand=True, side="left", padx=5, pady=5)
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_list.yview)
        scrollbar.pack(side="right", fill="y")
        self.results_list.config(yscrollcommand=scrollbar.set)

        actions_frame = ttk.Frame(self)
        actions_frame.pack(fill="x", padx=10, pady=5)
        self.fetch_lyrics_button = ttk.Button(actions_frame, text="Select", command=self.threaded_fetch_lyrics)
        self.fetch_lyrics_button.pack(side="left", padx=5)

        self.create_docx_button = ttk.Button(actions_frame, text="Create DOCX for Selected", state='disabled', command=self.threaded_create_docx)
        self.create_docx_button.pack(side="left", padx=5)

        self.clear_button = ttk.Button(actions_frame, text="Clear Results", command=self.clear_results)
        self.clear_button.pack(side="left", padx=5)

        # Internal state
        self.current_mode = None  # "artist" or "song"
        self.current_artist_data = []  # Can be list of artist candidates or albums
        self.current_song_data = []    # List of songs

        # Save artist name for album downloads
        self.current_artist_name = None
    
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_path.set(folder)

    # Threaded wrappers to keep UI responsive
    def threaded_create_docx(self):
        def task():
            self.clear_button.config(state='disabled')
            self.create_docx_button.config(state='disabled')
            self.fetch_lyrics_button.config(state='disabled')
            try:
                self.create_docx_action()
            finally:
                self.clear_button.config(state='normal')
                self.create_docx_button.config(state='normal')
                self.fetch_lyrics_button.config(state='normal')
        threading.Thread(target=task, daemon=True).start()

    def threaded_search_artist(self):
        def task():
            self.clear_button.config(state='disabled')
            self.create_docx_button.config(state='disabled')
            self.fetch_lyrics_button.config(state='disabled')
            try:
                self.search_artist_action()
            finally:
                self.clear_button.config(state='normal')
                self.fetch_lyrics_button.config(state='normal')
        threading.Thread(target=task, daemon=True).start()

    def threaded_search_song(self):
        def task():
            self.clear_button.config(state='disabled')
            self.create_docx_button.config(state='disabled')
            self.fetch_lyrics_button.config(state='disabled')
            try:
                self.search_song_action()
            finally:
                self.clear_button.config(state='normal')
                self.create_docx_button.config(state='normal')
                self.fetch_lyrics_button.config(state='normal', text='Create Vault For Selected')
        threading.Thread(target=task, daemon=True).start()

    def threaded_fetch_lyrics(self):
        def task():
            self.clear_button.config(state='disabled')
            self.create_docx_button.config(state='disabled')
            self.fetch_lyrics_button.config(state='disabled')
            try:
                self.fetch_lyrics_action()
            finally:
                self.clear_button.config(state='normal')
                self.create_docx_button.config(state='normal')
                self.fetch_lyrics_button.config(state='normal')
        threading.Thread(target=task, daemon=True).start()
        

    def search_artist_action(self):
        term = self.search_var.get().strip()
        if not term:
            self.safe_insert_results("error", "Error", "Enter an artist name or ID")
            return
        self.current_mode = "artist"
        self.safe_clear_results()
        self.current_artist_data.clear()
        self.current_song_data.clear()

        if term.isdigit():
            artist_id = term
            artist_name = f"Artist {artist_id}"
            self.load_albums_for_artist_threadsafe(artist_id, artist_name)
        else:
            candidates = search_artist(term)
            if not candidates:
                self.safe_insert_results("info", "No Results", "No artist matches found.")
                return
            if len(candidates) == 1:
                artist_id, artist_name = candidates[0]
                self.load_albums_for_artist_threadsafe(artist_id, artist_name)
            else:
                self.current_artist_data = candidates
                self.safe_insert_results("Multiple artist matches found:")
                for i, (aid, name) in enumerate(candidates, 1):
                    self.safe_insert_results(f"{i}. {name} (ID: {aid})")
                self.safe_insert_results("Select an artist number and click 'Fetch Lyrics for Selected'")

    def load_albums_for_artist_threadsafe(self, artist_id, artist_name):
        self.current_artist_name = artist_name
        self.safe_clear_results()
        self.safe_insert_results(f"Loading albums for {artist_name}...")
        soup = fetch_artist_album_page(artist_id)
        albums = get_albums_and_tracks(soup)
        # albums = fetch_all_albums_for_artist(artist_id)
        if not albums:
            self.safe_insert_results("info", "No albums", "No albums found for this artist.")
            self.safe_clear_results()
            return
        self.current_artist_data = albums
        self.safe_clear_results()
        for i, (album_title, release_date, tracks) in enumerate(albums, 1):
            self.safe_insert_results(f"{i}. {release_date} — {album_title} ({len(tracks)} tracks)")
        self.safe_insert_results("Select albums by number and click 'Fetch Lyrics for Selected'")

    def search_song_action(self):
        term = self.search_var.get().strip()
        if not term:
            self.safe_insert_results("error", "Error", "Enter a song title")
            return
        self.current_mode = "song"
        self.safe_clear_results()
        self.current_artist_data.clear()
        self.current_song_data.clear()

        results = search_songs(term)
        if not results:
            self.safe_insert_results("info", "No Results", "No songs found.")
            return
        self.current_song_data = results
        for i, (title, artist, url) in enumerate(results, 1):
            self.safe_insert_results(f"{i}. {title}  —  {artist}")
        self.safe_insert_results("Select songs by number and click 'Fetch Lyrics for Selected'")

    def fetch_lyrics_action(self):
        selections = self.results_list.curselection()
        self.fetch_lyrics_button.config(state='normal', text='Create Vault for Selected')
        if not selections:
            self.safe_insert_results("error", "Error", "No items selected.")
            self.fetch_lyrics_button.config(state='normal', text='Select')
            return

        save_folder = self.save_path.get()
        os.makedirs(save_folder, exist_ok=True)

        if self.current_mode == "artist":
            # If multiple artists shown, user picks one first
            if (self.current_artist_data and
                isinstance(self.current_artist_data[0], tuple) and
                len(self.current_artist_data[0]) == 2 and
                all(isinstance(i, str) for i in self.current_artist_data[0])):
                # Artist candidates selection
                chosen_indices = [i for i in selections if i > 0]  # skip info line
                if not chosen_indices:
                    self.safe_insert_results("error", "Error", "Select an artist number.")
                    return
                idx = chosen_indices[0] - 1
                artist_id, artist_name = self.current_artist_data[idx]
                self.load_albums_for_artist_threadsafe(artist_id, artist_name)
                return

            # Albums selection
            selected_albums = [self.current_artist_data[i] for i in selections if i < len(self.current_artist_data)]
            if not selected_albums:
                self.safe_insert_results("error", "Error", "Select at least one album.")
                return

            for album_title, release_date, tracks in selected_albums:
                self.save_album_lyrics(artist_name=self.current_artist_name,
                                       album=album_title,
                                       tracks=tracks,
                                       save_folder=save_folder)

        elif self.current_mode == "song":
            selected_songs = [self.current_song_data[i] for i in selections if i < len(self.current_song_data)]
            if not selected_songs:
                self.safe_insert_results("error", "Error", "Select at least one song.")
                return
            for title, artist, url in selected_songs:
                lyrics = fetch_lyrics(url)
                if not lyrics:
                    self.safe_insert_results("warning", "Warning", f"Missing lyrics for {title}")
                    continue
                filename = sanitize_filename(f"{artist}_{title}.txt")
                filepath = os.path.join(save_folder, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"Title: {title}\nArtist: {artist}\n\n{lyrics}")
                print(f"Saved: {filepath}")
            self.safe_insert_results("info", "Done", "Lyrics saved for selected songs.")

    def save_album_lyrics(self, artist_name, album, tracks, save_folder):
        #out_dir = os.path.join(save_folder, sanitize_filename(artist_name))
        #os.makedirs(out_dir, exist_ok=True)

        total_tracks = len(tracks)

        for i, (title, url) in enumerate(tracks):
            time.sleep(REQUEST_DELAY)
            lyrics = fetch_lyrics(url)
            if not lyrics:
                print(f"[⚠️] Missing lyrics for {title}")
                continue

            track_num = i + 1
            lyrics_lines = lyrics.strip().splitlines()

            generate_obsidian_lyric_file(
                lyrics_lines=lyrics_lines,
                song_title=re.sub(r"^\d+\s*[\.．]?\s*", "", title).strip(),
                artist=artist_name,
                album=album,
                track_number=track_num,
                total_tracks=total_tracks,
                track_titles = [title for title, _ in tracks],
                output_root=self.save_path.get()
            )
            self.safe_insert_results(f"✔️ Exported Obsidian MD: {track_num:02d}. {title}")
        print(f"✔️ Saved all lyrics to vault")

    def create_docx_action(self):
        selections = self.results_list.curselection()
        if not selections:
            self.safe_insert_results("error", "Error", "No items selected.")
            return

        save_folder = self.save_path.get()

        if self.current_mode == "song":
            selected_songs = [self.current_song_data[i] for i in selections if i < len(self.current_song_data)]
            if not selected_songs:
                self.safe_insert_results("⚠️ No songs selected.")
                return

            for title, artist, url in selected_songs:
                lyrics = fetch_lyrics(url)
                if not lyrics:
                    self.safe_insert_results(f"[⚠️] Missing lyrics for: {title}")
                    continue

                song_title = re.sub(r"^(\d+)\s+", r"\1. ", title)
                docx_name = sanitize_filename(f"{artist}_{song_title}.docx")
                save_path = os.path.join(save_folder, docx_name)
                clean_title = re.sub(r"^(\d+)\s+", r"\1. ", title)
                song_text = f"{clean_title}\n\n{lyrics}\n\n{'='*40}\n\n"

                create_docx_from_lyrics(song_text, save_path)
                self.safe_insert_results(f"✔️ Created DOCX for: {song_title}")
            return

        if self.current_mode != "artist":
            self.safe_insert_results("error", "Error", "DOCX generation only works for albums (artist mode).")
            return

        for album_title, release_date, tracks in [self.current_artist_data[i] for i in selections]:
            artist_dir = os.path.join(save_folder, sanitize_filename(self.current_artist_name))
            os.makedirs(artist_dir, exist_ok=True)
            album_docx_path = os.path.join(artist_dir, sanitize_filename(album_title) + ".docx")

            all_lyrics = []
            for title, url in tracks:
                lyrics = fetch_lyrics(url)
                if not lyrics:
                    print(f"[⚠️] Missing lyrics for {title}")
                    continue
                clean_title = re.sub(r"^(\d+)\s+", r"\1. ", title)
                song_text = f"{clean_title}\n\n{lyrics}\n\n{'='*40}\n\n"
                all_lyrics.append(song_text)
                self.safe_insert_results(f"✔️ Fetched lyrics for: {title}")

            lyrics_text = "".join(all_lyrics)
            delimiter = "\n\n" + "=" * 40 + "\n\n"
            lyrics_text = "".join(all_lyrics)
            if lyrics_text.endswith(delimiter):
                lyrics_text = lyrics_text[:lyrics_text.rfind(delimiter)]
            if not lyrics_text.strip():
                self.safe_insert_results("warning", "No Lyrics", f"No lyrics found for album '{album_title}'.")
                continue

            create_docx_from_lyrics(lyrics_text, album_docx_path)
            self.safe_insert_results(f"✔️ Created DOCX: {album_docx_path}")

    def clear_results(self):
        self.results_list.delete(0, tk.END)
        self.current_artist_data.clear()
        self.current_song_data.clear()
        self.current_mode = None
        self.current_artist_name = None
        self.clear_button.config(state='normal')
        self.create_docx_button.config(state='normal')
        self.fetch_lyrics_button.config(state='normal', text='Select')

    # Thread-safe UI helpers
    def safe_insert_results(self, text):
        self.after(0, lambda: self.results_list.insert(tk.END, text))

    def safe_clear_results(self):
        self.after(0, self.results_list.delete, 0, tk.END)

if __name__ == "__main__":
    app = UtaNetScraperApp()
    app.mainloop()
