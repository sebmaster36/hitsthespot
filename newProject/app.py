#!/usr/bin/env python3
from flask import Flask, render_template, url_for, request, redirect, session, make_response
from config import Config
import requests
import logging
import random as rand
import string
import base64
import time
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine 
from datetime import datetime
import statistics
import mysql.connector

# Initializing name of module with settings in config.py
app = Flask(__name__)
app.config.from_object(Config)

# Connecting to the Database 
app.config['SQLALCHEMY_DATABASE_URI'] = 'path_to_db' # [redacted]
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db = SQLAlchemy(app)

mydb = mysql.connector.connect(
    host    = # [redacted]
    user    = # [redacted]
    passwd  = # [redacted]
)

''' Functions '''

# necessary for authenitcation
def createStateKey(size):
    return ''.join(rand.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(size))

# necessary for making api requests post authorization (called as a consequence of navigating to landing page w/o having been auth'ed)
def getToken(code):
    token_url = 'https://accounts.spotify.com/api/token'
    authorization = app.config['AUTHORIZATION']
    redirect_uri = app.config['REDIRECT_URI']

    headers = {'Authorization': authorization, 'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}
    body = {'code': code, 'redirect_uri': redirect_uri, 'grant_type': 'authorization_code'}
    post_response = requests.post(token_url, headers=headers, data=body)

    # 200 code indicates access token was properly granted
    if post_response.status_code == 200:
        json = post_response.json()
        return json['access_token'], json['refresh_token'], json['expires_in']
    else:
        logging.error('getToken:' + str(post_response.status_code))
        return None

def refreshToken(refresh_token):
    token_url = 'https://accounts.spotify.com/api/token'
    authorization = app.config['AUTHORIZATION']

    headers = {'Authorization': authorization, 'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}
    body = {'refresh_token': refresh_token, 'grant_type': 'refresh_token'}
    post_response = requests.post(token_url, headers=headers, data=body)

    # 200 code indicates access token was properly granted
    if post_response.status_code == 200:
        return post_response.json()['access_token'], post_response.json()['expires_in']
    else:
        logging.error('refreshToken:' + str(post_response.status_code))
        return None

def checkTokenStatus(session):
    if time.time() > session['token_expiration']:
        payload = refreshToken(session['refresh_token'])

        if payload != None:
            session['token'] = payload[0]
            session['token_expiration'] = time.time() + payload[1]
        else:
            logging.error('checkTokenStatus')
            return None

    return "Success"

def parse_flattened(s: str) -> list:
    return [ x.replace("\'", "").strip() for x in s[1:-1].split(',') ]

# Utilities to use in functions 
def makeGetRequest(session, url, params={}):
    headers = {"Authorization": "Bearer {}".format(session['token'])}
    response = requests.get(url, headers=headers, params=params)

    # 200 code indicates request was successful
    if response.status_code == 200:
        return response.json()

    # if a 401 error occurs, update the access token
    elif response.status_code == 401 and checkTokenStatus(session) != None:
        return makeGetRequest(session, url, params)
    else:
        logging.error('makeGetRequest:' + str(response.status_code))
        return None

def makePutRequest(session, url, params={}, data={}):
    headers = {"Authorization": "Bearer {}".format(session['token']), 'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.put(url, headers=headers, params=params, data=data)

    # if request succeeds or specific errors occured, status code is returned
    if response.status_code == 204 or response.status_code == 403 or response.status_code == 404 or response.status_code == 500:
        return response.status_code

    # if a 401 error occurs, update the access token
    elif response.status_code == 401 and checkTokenStatus(session) != None:
        return makePutRequest(session, url, data)
    else:
        logging.error('makePutRequest:' + str(response.status_code))
        return None

def makePostRequest(session, url, data):

    headers = {"Authorization": "Bearer {}".format(session['token']), 'Accept': 'application/json', 'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, data=data)

    # both 201 and 204 indicate success, however only 201 responses have body information
    if response.status_code == 201:
        return response.json()
    if response.status_code == 204:
        return response

    # if a 401 error occurs, update the access token
    elif response.status_code == 401 and checkTokenStatus(session) != None:
        return makePostRequest(session, url, data)
    elif response.status_code == 403 or response.status_code == 404:
        return response.status_code
    else:
        logging.error('makePostRequest:' + str(response.status_code))
        return None

def makeDeleteRequest(session, url, data):
    headers = {"Authorization": "Bearer {}".format(session['token']), 'Accept': 'application/json', 'Content-Type': 'application/json'}
    response = requests.delete(url, headers=headers, data=data)

    # 200 code indicates request was successful
    if response.status_code == 200:
        return response.json()

    # if a 401 error occurs, update the access token
    elif response.status_code == 401 and checkTokenStatus(session) != None:
        return makeDeleteRequest(session, url, data)
    else:
        logging.error('makeDeleteRequest:' + str(response.status_code))
        return None


# used to store session data as well as get necessary information for playlist making
def getUserInformation(session):
    url = 'https://api.spotify.com/v1/me'
    payload = makeGetRequest(session, url)

    print(payload)

    if payload == None:
        return None

    return payload


# get playlists given a user ID
def getUserPlaylists(session, limit=20):
    url = 'https://api.spotify.com/v1/me/playlists'
    offset = 0
    playlist = []

    # iterate through all playlists of a user (Spotify limits amount returned with one call)
    total = 1
    while total > offset:
        params = {'limit': limit, 'offset': offset}
        payload = makeGetRequest(session, url, params)

        if payload == None:
            return None
        
        for item in payload['items']:
            playlist.append([item['name'], item['uri']])

        total = payload['total']
        offset += limit
    # @Germ/Sean maybe check here?
    return playlist

# get tracks from a playlist given ID
def getTracksPlaylist(session, playlist_id, limit=100):
    url = 'https://api.spotify.com/v1/playlists/' + playlist_id + '/tracks'

    offset = 0
    track_uri = []

    # iterate through all tracks in a playlist (Spotify limits number per request)
    total = 1
    while total > offset:
        params = {'limit': limit, 'fields': 'total,items(track(uri))', 'offset': offset}
        payload = makeGetRequest(session, url, params)

        if payload == None:
            return None
        
        for item in payload['items']:
            track_uri.append(item['track']['uri'])

        total = payload['total']
        offset += limit

    return track_uri

#Calculates means and std dev for a playlist
def quantify_vibe(playlist):
    vibe_list = {}
    vibe = {}
    songs_list = []
    for num, song in enumerate(playlist):
        if song['danceability'] == None:
                continue
        elif num:
            vibe_list['danceability'].append(song['danceability'])
            vibe_list['energy'].append(song['energy'])
            vibe_list['speechiness'].append(song['speechiness'])
            vibe_list['acousticness'].append(song['acousticness'])
            vibe_list['instrumentalness'].append(song['instrumentalness'])
            vibe_list['valence'].append(song['valence'])
        else:
            vibe_list['danceability']=[song['danceability']]
            vibe_list['energy']=[song['energy']]
            vibe_list['speechiness']=[song['speechiness']]
            vibe_list['acousticness']=[song['acousticness']]
            vibe_list['instrumentalness']=[song['instrumentalness']]
            vibe_list['valence']=[song['valence']]

        song_dict = {}
        song_dict['id']=song['id']
        song_dict['danceability']=song['danceability']
        song_dict['energy']=song['energy']
        song_dict['speechiness']=song['speechiness']
        song_dict['acousticness']=song['acousticness']
        song_dict['instrumentalness']=song['instrumentalness']
        song_dict['valence']=song['valence']
        songs_list.append(song_dict)

    if 'energy' in vibe_list and len(vibe_list['energy']) >= 2:   
        for attr in vibe_list:
            vibe[attr] = [sum(vibe_list[attr])/len(vibe_list[attr]),statistics.stdev(vibe_list[attr])]
    else:
        for attr in vibe_list:
            vibe[attr] = [sum(vibe_list[attr])/len(vibe_list[attr]), 0]
    
    return vibe, songs_list

# Gets the relevant values for the vibe rater page
def vibe_grader(ids):
    sql = "select * from songs_expanded where"
    sql2 = "select songs.name as name, songs.artist_name as artist, songs.id from songs, songs_expanded where songs.id=songs_expanded.id and ("
    for count, i in enumerate(ids):
        if count:
            sql += f' or id=\'{i}\''
            sql2 += f' or songs.id=\'{i}\''
        else:
            sql += f' id=\'{i}\''
            sql2 += f' songs.id=\'{i}\''
    
    sql2 += ')'
    playlist = db.session.execute(sql)
    playlist2 = db.session.execute(sql2)

    vibe, songs_list = quantify_vibe(playlist)
    song_scores = [0] * len(songs_list)
    for num, song in enumerate(songs_list):
        for attr in vibe:
            if song[attr] != None and attr != 'id':
                song_scores[num] += (100/6 /((1+abs(song[attr]-vibe[attr][0])//(vibe[attr][1]+.00000000001)))**2)
            
    sum_val = 0
    count = 0
    for val in song_scores:
        if val != 0:
            sum_val += val
            count+=1
    
    if count > 1:
        score = sum_val/count
    elif count:
        score = 100
    else:
        score = 0

    songs_list = {}
    for num, song in enumerate(playlist2):
        song_dict = {}
        song_dict['id']=song['id']
        song_dict['name']=song['name']
        song_dict['artist']=song['artist']
        song_dict['score']=round(song_scores[num],2)
        songs_list[song['id']]=song_dict

    return round(score,2), songs_list

def createPlaylist(session, playlist_name):
    url = 'https://api.spotify.com/v1/users/' + session['user_id'] + '/playlists'
    data = "{\"name\":\"" + playlist_name + "\",\"description\":\"Courtesy of Hits the Spot <3\"}"
    payload = makePostRequest(session, url, data)

    if payload == None:
        return None

    return payload['id'], payload['uri']

def addTracksPlaylist(session, playlist_id, uri_list):
    url = 'https://api.spotify.com/v1/playlists/' + playlist_id + '/tracks'

    
    uri_str = ""
    for uri in uri_list:
        uri_str += "\"" + uri + "\","
    
   
    print(uri_str)

    data = "{\"uris\": [" + uri_str[0:-1] + "]}"
    response = makePostRequest(session, url, data)

    print(response)

    return

def generator(name):
    
    # List for Dictionaries 
    songs_list = []
    ids_list = []

    for num, song in enumerate(name):

        # Dictionary to store values 
        dict_values = {}
        
        # Store the values, like song, into the dictionary 
        dict_values['songname'] = song[0]
        ids_list.append(song[1]) 
        dict_values['artistname'] = song[2]
        songs_list.append(dict_values)

    return songs_list, ids_list

''' Views/Routes '''

# pre-auth page
@app.route('/') 
@app.route('/index')
def index():
   #session.clear()
    #[session.pop(key) for key in list(session.keys())]
    #print(session)
    return render_template('index.html')


# intermediate view (formulates auth request)
@app.route("/authorize")
def authorize():
    client_id       = app.config['CLIENT_ID']
    client_secret   = app.config['CLIENT_SECRET']
    redirect_uri    = app.config['REDIRECT_URI']
    scope           = app.config['SCOPE']

    state_key = createStateKey(15)
    session['state_key'] = state_key


    # redirect user to Spotify authorization page
    authorize_url = 'https://accounts.spotify.com/en/authorize?'
    parameters = 'response_type=code&client_id=' + client_id + '&redirect_uri=' + redirect_uri + '&scope=' + scope + '&state=' + state_key
    print(parameters)
    response = make_response(redirect(authorize_url + parameters))

    return response
    
# where spotify api redirects you to after auth
@app.route("/callback")
def callback():
    # make sure the response came from Spotify
    if request.args.get('state') != session['state_key']:
        return render_template('index.html', error='State failed.')
    if request.args.get('error'):
        return render_template('index.html', error='Spotify error.')
    else:
        code = request.args.get('code')
        session.pop('state_key', None)

        # get access token to make requests on behalf of the user
        payload = getToken(code)
        if payload != None:
            session['token'] = payload[0]
            session['refresh_token'] = payload[1]
            session['token_expiration'] = time.time() + payload[2]
        else:
            return render_template('index.html', error='Failed to access token.')

    #print(f'this is the: {session}')
    current_user = getUserInformation(session)
    #print(f'the current user is {current_user}')
    session['user_id'] = current_user['id']
    logging.info('new user:' + session['user_id'])

    # brings you back to where you started auth flow (landing.html)
    return redirect(session['previous_url'])

# post-auth page
@app.route("/landing")
def landing():
    if session.get('token') == None or session.get('token_expiration') == None:
        session['previous_url'] = '/landing'
        return redirect('/authorize')

    if session.get('user_id') == None:
        current_user = getUserInformation(session)
        session['user_id'] = current_user['id']

    return render_template('landing.html')

# top nav link for vibe rate app
@app.route("/vibe-rater")
def vibe_rater():
    # make sure valid token/auth, else get it
    if session.get('token') == None or session.get('token_expiration') == None:
        session['previous_url'] = '/vibe-rater'
        return redirect('/authorize')

    if session.get('user_id') == None:
        current_user = getUserInformation(session)
        session['user_id'] = current_user['id']

    # call function defined above returns -> playlist in playlists: ['pl_name', 'spotify:playlist:{pl_id}']
    playlists = getUserPlaylists(session)

    if playlists is None:
        return render_template('index.html', error='Failed to get playlists.')

    playlists_length = len(playlists)

    # template is loaded with playlist values in select bar (see vibe_rater.html)
    # will create an option in the select menu for each item 
    return render_template('vibe_rater.html', title="Vibe Rater", playlist_names=playlists, playlist_length=playlists_length)

@app.route("/vibe-rater", methods=['POST'])
def vibe_rater_form():
    if session.get('token') == None or session.get('token_expiration') == None:
        session['previous_url'] = '/vibe-rater'
        return redirect('/authorize')

    if session.get('user_id') == None:
        current_user = getUserInformation(session)
        session['user_id'] = current_user['id']

    # extracting uri from form

    req = parse_flattened(request.form['playlist'])
    
    playlist_uri = req[-1].split(':')[-1]

    session['playlist_name'] = req[0]
    # brings to an instance of vibe rated route below
    return redirect(url_for('vibe_rated', pl=playlist_uri, name=req[0]))

# playlist id passed to route via URL and usable in function by name (pl)
@app.route("/vibe-rated/<pl>")
def vibe_rated(pl):
    if session.get('token') == None or session.get('token_expiration') == None:
        session['previous_url'] = '/vibe-rater'
        return redirect('/authorize')

    if session.get('user_id') == None:
        current_user = getUserInformation(session)
        session['user_id'] = current_user['id']

    # extracting id from tag and extracting song ids from playlist
    raw_playlist = getTracksPlaylist(session, pl)
    # stripping tracks to get pure ids
    playlist =  list(map(lambda x: x.split(':')[-1] , raw_playlist))
    # analysis
    score, songs_list = vibe_grader(playlist)

    result = []
    new_playlist = []
    for song_id in playlist:
        song = {}
        if song_id in songs_list:
            song = songs_list[song_id]
            if song['score'] >= 75:
                song['keep'] = 'keep'
                new_playlist.append(song['id'])
            else:
                song['keep'] = 'remove'
            result.append(song)
        else:
            url = 'https://api.spotify.com/v1/tracks/' + song_id
            request = makeGetRequest(session, url)
            if request != None:
                song['id'] = song_id
                song['name'] = request['name']
                song['artist'] = request['artists'][0]['name']
                song['score'] = 'N/A'
                song['keep'] = 'keep'
                new_playlist.append(song['id'])
                result.append(song)

    comms = [
        'this playlist is a war crime', 'brb, googling what an ear doctor is called', 'yikes', 
        'youre uninvited from my bday', 'atrociously mid', 'does not hit the spot', 'okayyy', 'we see you',
        'dj du lac better watch out', 'needs to go on NDH aux asap', 'immaculate vibes (or you cheated)'
        ]

    name = session['playlist_name'] 
    # passing variables template so they are accessible to be displayed ( new is passed and then recollected by form underneath)
    return render_template('vibe_rated.html', title="Your Result", playlist=result, score=score, comment=comms[int(score//10)], new=new_playlist, name=name)
    #return redirect(url_for('vibe_rated', title="Your Result", playlist=result, score=score, comment=comms[int(score//10)]))


# add to library button was clicked 
@app.route("/vibe-rated/<pl>", methods=['POST'])
def vibe_rated_form(pl):
    # making sure signed in
    if session.get('token') == None or session.get('token_expiration') == None:
        session['previous_url'] = '/vibe-rater'
        return redirect('/authorize')

    if session.get('user_id') == None:
        current_user = getUserInformation(session)
        session['user_id'] = current_user['id']

    # stored list of ids as a string from form submission
    id_str = request.form['created']

    # reconverting string to list
    raw_ids = parse_flattened(id_str) 

    # tagging ids to go into api 
    uri_list = list(map(lambda x: "spotify:track:" + x, raw_ids))

    #TODO check for unicode
    name = session['playlist_name'] + " revibed"

    # creating playlist and addings songs to it (API calls)

    playlist_id, playlist_uri = createPlaylist(session, name)
    addTracksPlaylist(session, playlist_id, uri_list)

    # success screen
    return render_template('/playlist_created.html', name=name)

# select a vibe
@app.route("/playlist-maker")
def playlist_maker():
    if session.get('token') == None or session.get('token_expiration') == None:
        session['previous_url'] = '/playlist-maker'
        return redirect('/authorize')

    if session.get('user_id') == None:
        current_user = getUserInformation(session)
        session['user_id'] = current_user['id']

    vibes = db.session.execute('select name from vibes')
    vibe_list = [v['name'] for v in vibes]
    
    # template populated with list of vibes
    return render_template('playlist_maker.html', title="Pick a Vibe", vibes=vibe_list)

# 
@app.route("/playlist-maker", methods=['POST'])
def playlist_maker_form():
    if session.get('token') == None or session.get('token_expiration') == None:
        session['previous_url'] = '/playlist-maker'
        return redirect('/authorize')

    if session.get('user_id') == None:
        current_user = getUserInformation(session)
        session['user_id'] = current_user['id']

    # extracting uri from form found in playlist_maker form 

    in_vibe = request.form['chosenVibe']
    
    # brings me to function and passes vibe
    return redirect(url_for('created_playlist', vibe=in_vibe))

# playlist calculated here, vibe displayed as name
@app.route("/created_playlist/<vibe>")
def created_playlist(vibe):
    if session.get('token') == None or session.get('token_expiration') == None:
        session['previous_url'] = '/playlist-maker'
        return redirect('/authorize')

    if session.get('user_id') == None:
        current_user = getUserInformation(session)
        session['user_id'] = current_user['id']

    # Insert Function calls here
    sql = f"select * from vibes where name = \'{vibe}\'"

    vibe_sql = db.session.execute(sql)

    vibe_dict = {}
    for v in vibe_sql:
        vibe_dict['danceability'] = [v['danceability_mean']-v['danceability_std']]
        vibe_dict['danceability'].append(v['danceability_mean']+v['danceability_std'])
        vibe_dict['energy'] = [v['energy_mean']-v['energy_std']]
        vibe_dict['energy'].append(v['energy_mean']+v['energy_std'])
        vibe_dict['valence'] = [v['valence_mean']-v['valence_std']]
        vibe_dict['valence'].append(v['valence_mean']+v['valence_std'])
        vibe_dict['speechiness'] = [v['speechiness_mean']-v['speechiness_std']]
        vibe_dict['speechiness'].append(v['speechiness_mean']+v['speechiness_std'])
        vibe_dict['acousticness'] = [v['acousticness_mean']-v['acousticness_std']]
        vibe_dict['acousticness'].append(v['acousticness_mean']+v['acousticness_std'])
        vibe_dict['instrumentalness'] = [v['instrumentalness_mean']-v['instrumentalness_std']]
        vibe_dict['instrumentalness'].append(v['instrumentalness_mean']+v['instrumentalness_std'])

    query =  'SELECT songs.name, songs.id, arts.name as artist_name FROM songs, (SELECT * FROM artists WHERE popularity > 60) as arts, '
    songs_exp_query = ''
    for attr in vibe_dict:
        if not songs_exp_query:
            songs_exp_query = f'(SELECT * FROM songs_expanded WHERE {attr} >= {vibe_dict[attr][0]} and {attr} <= {vibe_dict[attr][1]}) as songs_exp'
        else:
            songs_exp_query = f'(SELECT * FROM {songs_exp_query} WHERE {attr} >= {vibe_dict[attr][0]} and {attr} <= {vibe_dict[attr][1]}) as songs_exp'
    query += songs_exp_query
    query += f' WHERE songs.id = songs_exp.id and songs.artist_id = arts.id ORDER BY rand() LIMIT 30'

    name = db.session.execute(query)
    songs, ids = generator(name)

    return render_template('created_playlist.html', title="Your New Playlist", playlist=songs, ids=ids, name=vibe)

@app.route("/created_playlist/<vibe>", methods=['POST'])
def created_playlist_form(vibe):
    if session.get('token') == None or session.get('token_expiration') == None:
        session['previous_url'] = '/playlist-maker'
        return redirect('/authorize')

    if session.get('user_id') == None:
        current_user = getUserInformation(session)
        session['user_id'] = current_user['id']

    # stored list of ids as a string from form submission
    id_str = request.form['saved']

    # reconverting string to list
    raw_ids = parse_flattened(id_str) 

    # tagging ids to go into api 
    uri_list = list(map(lambda x: "spotify:track:" + x, raw_ids))

    #TODO check for unicode
    name = vibe + " vibes playlist"

    # creating playlist and addings songs to it (API calls)

    playlist_id, playlist_uri = createPlaylist(session, name)
    addTracksPlaylist(session, playlist_id, uri_list)

    # success screen
    return render_template('/playlist_created.html', name=name)

@app.route("/create")
def create_playlist():
    return render_template('create.html', name='Create Vibe')

@app.route("/create", methods=['POST'])
def create_playlist_form():

    # get all values from form
    
    name        = request.form['vibe_name']
    acoustic    = request.form['slider_acoustic']
    dance       = request.form['slider_danceability']
    energy      = request.form['slider_energy']
    speech      = request.form['slider_speechiness']
    valence     = request.form['slider_valence']
    inst        = request.form['slider_instrumentalness']

    # Insert Josh Function
    msg = ""
    std_danceability = 0.1
    std_energy = 0.125
    std_valence = 0.2
    std_speechiness = 0.05
    std_acousticness = 0.2 
    std_instrumentalness = 0.05

    temp = name.replace(' ', '')
    temp = 'a' + temp
    if temp.isidentifier():
        names = db.session.execute(f'SELECT name from vibes')
        name_set = set()
        for n in names:
            name_set.add(n[0]) 

        if name in name_set:
            msg = "Name already exists in database! Use a unique name."
        else:   
            insert = f"insert into sbeckerl.vibes (name, danceability_mean, danceability_std, energy_mean, energy_std, valence_mean, valence_std, speechiness_mean, speechiness_std, acousticness_mean, acousticness_std, instrumentalness_mean, instrumentalness_std) values (\'{name}\', {dance}, {std_danceability}, {energy}, {std_energy}, {valence}, {std_valence}, {speech}, {std_speechiness}, {acoustic}, {std_acousticness}, {inst}, {std_instrumentalness})"
            my_cursor = mydb.cursor()
            my_cursor.execute(insert)
            mydb.commit()
            return render_template('/vibe_created.html', title="Vibe Created", name=name)
    else:
        msg = "Name is not a valid playlist name (A-Z, a-z, 0-9, and & only)!"

    return render_template('/vibe_not_created.html', title="Vibe Created", name=name, msg=msg)

# run the app using `python3 app.py`
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5007)
