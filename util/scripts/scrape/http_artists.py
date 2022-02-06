#!/usr/bin/env python3

import requests
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

artist_ids = []

with open('dummyartists.txt') as f:
	ids = [ line.strip() for line in f ]
	
with open("artists_d.json", 'w') as in_json:
	for count, a_id in enumerate(ids):
		r = requests.get(BASE_URL + 'artists/' + a_id, 
						headers=headers, 
						params={'include_groups': 'album', 'limit': 50})
		d = r.json()
		artist_f = {
			'id' : d['id'],
			'name' : d['name'],
			'followers' : d['followers']['total'],
			'popularity' : d['popularity']
		}
		print(json.dumps(artist_f), file=in_json)
		print(count)


