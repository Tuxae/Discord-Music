import json

class Playlist():

    def __init__(self, filename="playlist.json"):
        with open(filename, 'r') as json_file:
            self.songs = json.load(json_file)

    def get_songs(self):
        s = ""
        for song in self.songs.values():
            s += f"{ song['title'] }\n"
        return s
    
    def get_urls(self):
        return [song['url'] for song in self.songs.values()]
