#!/usr/bin/env python3

import requests
import json
from time import sleep
import collections

CLIENT_ID = # [redacted]
CLIENT_SECRET = # [redacted]

AUTH_URL = 'https://accounts.spotify.com/api/token'

BASE_URL = 'https://api.spotify.com/v1/'


def get_albums(artist_id, headers) :
	with open("albums_test.json", 'w') as albums:
		r = requests.get(BASE_URL + 'artists/' + artist_id + '/albums', 
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


def get_songs(a_id, headers):
	with open('song_test.json', 'w') as songs:
		r = requests.get(BASE_URL + 'albums/' + a_id + '/tracks', headers=headers)
		tracks = r.json()['items']
		for track in tracks:
    	    # get audio features (key, liveness, danceability, ...)
			#f = requests.get(BASE_URL + 'audio-features/' + track['id'], headers=headers)
			#f = f.json()
			track_f = collections.defaultdict()
			track_f['id']	  		= track['id'],
			track_f['name'] 		= track['name'],
			track_f['album_id'] 	= a_id,
			track_f['track_number']	= track['track_number'],
			track_f['artist_id']   	= track['artists'][0]['id'],
			track_f['artist_name'] 	= track['artists'][0]['name'],
			track_f['duration']    	= track['duration_ms'],
			track_f['explicit'] 	= track['explicit']
			sleep(.035)
			f = requests.get(BASE_URL + 'audio-features/' + track['id'], headers=headers)
			f = f.json()
		
			if 'error' in list(f.keys()):
				print(f) 
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
			else:
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

def main():
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

	get_albums('04gDigrS5kc9YWfZHwBETP', headers)
	get_songs('4KXLjIEas8MTwwX3xpmAdC', headers)

if __name__ == '__main__':
	main()