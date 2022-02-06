#!/usr/bin/env python3

import requests
import json
from time import sleep
import collections

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

song_ids = []
with open('dummysids.txt') as f:
	for line in f:
		song_ids.append(line.strip())

#count = 30425
with open('d_song_ext.json', 'w') as songs:
	for count, s_id in enumerate(song_ids):
		if count%25 == 0:
			print(count)
		# pull song data based on id
		sleep(.03)
		f = requests.get(BASE_URL + 'audio-features/' + s_id, headers=headers)
		f = f.json()
		track_f = collections.defaultdict()
		if 'error' in list(f.keys()):
			print(f)
			track_f['id'] 		       = s_id
			track_f['danceability']    = None
			track_f['energy'] 	  	   = None
			track_f['loudness']    	   = None
			track_f['speechiness'] 	   = None
			track_f['acousticness']	   = None
			track_f['instrumentalness']= None
			track_f['liveness']	  	   = None
			track_f['valence']	  	   = None
			track_f['tempo']		   = None
			track_f['time_signature']  = None
			print(count)
		else:
			track_f['id'] 		       = s_id
			track_f['danceability']    = f['danceability']
			track_f['energy'] 	       = f['energy']
			track_f['loudness']        = f['loudness']
			track_f['speechiness'] 	   = f['speechiness']
			track_f['acousticness']	   = f['acousticness']
			track_f['instrumentalness']= f['instrumentalness']
			track_f['liveness']	  	   = f['liveness']
			track_f['valence']	 	   = f['valence']
			track_f['tempo']		   = f['tempo']
			track_f['time_signature']  = f['time_signature']

		print(json.dumps(track_f), file=songs)
print(count)

	