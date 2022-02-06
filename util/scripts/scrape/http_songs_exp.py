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

album_ids = []
with open('seb_albums.txt') as f:
	for line in f:
		album_ids.append(line.strip())

count = 41
with open('song_json/songs_ext04.json', 'w') as songs:
	for a_id in album_ids[41:]:
		# pull all tracks from this album
		sleep(.5)
		r = requests.get(BASE_URL + 'albums/' + a_id + '/tracks', headers=headers)
		tracks = r.json()['items']
		for track in tracks: #track in tracks:
    	    # get audio features (key, liveness, danceability, ...)
			t_id = track['id']
			f = requests.get(BASE_URL + 'audio-features/' + t_id, headers=headers)
			f = f.json()
			track_f = {
				'id' 		  : t_id,
				'danceability': f['danceability'],
				'energy' 	  : f['energy'],
				'loudness'    : f['loudness'],
				'speechiness' : f['speechiness'],
				'acousticness': f['acousticness'],
				'instrumentalness': f['instrumentalness'],
				'liveness'	  : f['liveness'],
				'valence'	  : f['valence'],
				'tempo'		  : f['tempo'],
				'time_signature' : f['time_signature']
			}
			print(json.dumps(track_f), file=songs)
		print(count)
		count += 1
