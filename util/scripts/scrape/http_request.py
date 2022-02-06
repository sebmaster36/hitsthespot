#!/usr/bin/env python3

import requests
import csv
import json

CLIENT_ID = # [redacted]
CLIENT_SECRET = # [redacted]
AUTH_URL = 'https://accounts.spotify.com/api/token'

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

with open('dummyartists.txt') as f:
	artists = [ line.strip() for line in f ]


with open("d_albums.json", 'w') as albums:
	for count, a_id in enumerate(artists):
		r = requests.get(BASE_URL + 'artists/' + a_id + '/albums', 
						headers=headers, 
						params={'include_groups': 'album', 'limit': 50})
		d = r.json()
		if 'items' in d.keys():
			for album in d['items']:
				alb = {
					'id' 		   : album['id'],
					'name' 		   : album['name'],
					'release_date' : album['release_date'],
					'total_tracks' : album['total_tracks'],
					'artist_id'    : album['artists'][0]['id'],
					'artist_name'  : album['artists'][0]['name'],	
				}
				print(json.dumps(alb), file=albums)
		print(count)


