#!/usr/bin/env python3

import requests
import json
from time import sleep

CLIENT_ID = # [redacted]
CLIENT_SECRET = # [redacted]

AUTH_URL = 'https://accounts.spotify.com/api/token'

# POST
auth_response = requests.post(AUTH_URL, {
    'grant_type': 'client_credentials',
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
})

# convert the response to JSON
auth_response_data = auth_response.json()

# save the access token
access_token = auth_response_data['access_token']

headers = {
	'Authorization': 'Bearer {token}'.format(token=access_token)
}

BASE_URL = 'https://api.spotify.com/v1/'

with open('dummyalbums.txt') as f:
	albums = [ line.strip() for line in f ]

with open('d_songs.json', 'w') as songs:
	for count, a_id in enumerate(albums):
		# pull all tracks from this album
		sleep(.07)
		r = requests.get(BASE_URL + 'albums/' + a_id + '/tracks', headers=headers)
		tracks = r.json()['items']
		for track in tracks:
    	    # get audio features (key, liveness, danceability, ...)
			#f = requests.get(BASE_URL + 'audio-features/' + track['id'], headers=headers)
			#f = f.json()
			track_f = {
				'id' 		  : track['id'],
				'name' 		  : track['name'],
				'album_id' 	  : a_id,
				'track_number': track['track_number'],
				'artist_id'   : track['artists'][0]['id'],
				'artist_name' : track['artists'][0]['name'],
				'duration'    : track['duration_ms'],
				'explicit' 	  : track['explicit']
			}
			print(json.dumps(track_f), file=songs)
		print(count)
