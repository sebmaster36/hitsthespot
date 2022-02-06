#!/usr/bin/env python3
import os
import sys
import json
import spotipy
import pprint
import spotipy.util as util
from json.decoder import JSONDecodeError

try: 
    token = util.prompt_for_user_token(show_dialog=True)
except:
    os.remove(f".cache-{username}")
    token = util.prompt_for_user_token(username) #24932

spotifyObject = spotipy.Spotify(auth=token)

with open("dummyartists.txt") as f:
    ids = [ line.strip() for line in f ]

with open("artists_d.json", 'w') as in_json:
    for id in ids:
        d = spotifyObject.artist(f'{id.strip()}')
        artist_f = {
            'id' : d['id'],
            'name' : d['name'],
            'followers' : d['followers']['total'],
            'popularity' : d['popularity']
        }
        print(json.dumps(artist_f), file=in_json)
        print(count)
        count += 1

#pprint.pprint(artist_f)


#pprint.pprint(spotifyObject.artist('7ymgfUyJFViyg1qFo4M2nH'))
