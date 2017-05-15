from flask_cors import CORS
from shapely import geos
from geopy.geocoders import Nominatim
from flask import Flask, abort, Blueprint
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import time
import os
import requests
import json
import psycopg2

APP_PORT = 80
if 'APP_PORT' in os.environ:
    APP_PORT = os.environ['APP_PORT']

APP_URL_PREFIX = ''
if 'APP_URL_PREFIX' in os.environ:
    APP_URL_PREFIX = os.environ['APP_URL_PREFIX']

POSTGRES_HOST = 'localhost'
if 'POSTGRES_HOST' in os.environ:
    POSTGRES_HOST = os.environ['POSTGRES_HOST']

POSTGRES_USER = 'postgres'
if 'POSTGRES_USER' in os.environ:
    POSTGRES_USER = os.environ['POSTGRES_USER']

POSTGRES_PW = 'password'
if 'POSTGRES_PW' in os.environ:
    POSTGRES_PW = os.environ['POSTGRES_PW']

POSTGRES_DB = 'teleport'
if 'POSTGRES_DB' in os.environ:
    POSTGRES_DB = os.environ['POSTGRES_DB']

QUERY_RADIUS = '300'
if 'QUERY_RADIUS' in os.environ:
    QUERY_RADIUS = os.environ['QUERY_RADIUS']

CLIENT_ID = 'UMZ5JVTFVF5TBPY5GYFIJV2VGPF3VBHWZWVYHMGNDVEWN5RE'
if 'CLIENT_ID' in os.environ:
    CLIENT_ID = os.environ['CLIENT_ID']

CLIENT_SECRET = 'ALSIDWNM53IILXJXHGGKFKTPLSA2C1TBMJYGED2NWAZ35IFX'
if 'CLIENT_SECRET' in os.environ:
    CLIENT_SECRET = os.environ['CLIENT_SECRET']


FITNESS_CENTER_ID = '4bf58dd8d48988d175941735'
CAFE_ID = '4bf58dd8d48988d16d941735'
FITNESS_AND_CAFE_ID = "%s,%s" % (FITNESS_CENTER_ID, CAFE_ID)

DATE = time.strftime("%Y%m%d")

geolocator = Nominatim()

geos.WKBWriter.defaults['include_srid'] = True

bp = Blueprint('teleport', __name__)


# Initializes the creation of the database and its table
def init_db(db):

    cnx = cnx_to_psql(db=db, user=POSTGRES_USER, host=POSTGRES_HOST)
    cnx.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    cur = cnx.cursor()

    # Creates database
    try:
        cur.execute("CREATE DATABASE " + POSTGRES_DB)
    except psycopg2.ProgrammingError as e:
        print(e)

    cnx = cnx_to_psql(db=POSTGRES_DB,user=POSTGRES_USER, host=POSTGRES_HOST)
    cur = cnx.cursor()

    # Creates the postgis extension into the database
    try:
        cur.execute("""CREATE EXTENSION postgis""")
    except psycopg2.ProgrammingError as e:
        print(e)

    # Creates the table
    try:
        cur.execute("CREATE TABLE IF NOT EXISTS public.venues ("
                    " id serial,"
                    " zip_code integer,"
                    " po_name varchar,"
                    " geom geometry,"
                    " category_name varchar,"
                    " address varchar,"
                    " latitude integer,"
                    " longitude integer,"
                    " venue_name varchar, "
                    " url varchar);")
    except psycopg2.InternalError as e:
        print(e)

    try:
        cur.execute("CREATE TABLE IF NOT EXISTS public.bayareadata ("
                    " id serial,"
                    " zip_code integer,"
                    " po_name varchar(40),"
                    " geom geometry);")
    except psycopg2.InternalError as e:
        print(e)

    cnx.commit()

    cur.close()
    cnx.close()


# Using this method instead of jsonify (encoding is better)
def dumpjson(array):
    return json.dumps(array, ensure_ascii=False).encode('utf-8')


# Method to make a connection to postgres
def cnx_to_psql(db, user, host):
    try:
        cnx = psycopg2.connect("dbname=%s user=%s host=%s" % (db, user, host))
    except Exception as e:
        print(e)
        print("Unable to connect")

    return cnx


def get_from_db(zip_code):
    cnx = cnx_to_psql(db=POSTGRES_DB, user=POSTGRES_USER, host=POSTGRES_HOST)
    cur = cnx.cursor()
    cur.execute("SELECT * from bayareadata where zip_code=%(zip_code)s" % {'zip_code': zip_code})
    rows = cur.fetchone()
    return rows


# Method to return the foursquare IDs for categories
def get_category_id(category):
    if category == 'cafe':
        category_id = CAFE_ID
    elif category == 'gym':
        category_id = FITNESS_CENTER_ID
    elif category == 'cafe,gym':
        category_id = FITNESS_AND_CAFE_ID
    else:
        return abort(400)

    return category_id


# Method to create a list with all possible data from foursquare
def create_venues_array(venues_list, zip_code, po_name, geom):
    venues = []
    for x in venues_list:
        venue_data = {}

        venue_data['zip_code'] = zip_code
        venue_data['po_name'] = po_name
        venue_data['geom'] = geom

        try:
            venue_data['name'] = x['name']
        except KeyError:
            venue_data['name'] = 'No data provided'

        try:
            venue_data['url'] = x['url']
        except KeyError:
            venue_data['url'] = 'No data provided'

        try:
            venue_data['category_name'] = x['categories'][0]['name']
        except KeyError:
            venue_data['category_name'] = 'No data provided'

        try:
            venue_data['address'] = x['location']['formattedAddress']
        except KeyError:
            venue_data['address'] = 'No data provided'

        try:
            venue_data['latitude'] = x['location']['lat']
        except KeyError:
            venue_data['latitude'] = 'No data provided'

        try:
            venue_data['longitude'] = x['location']['lng']
        except KeyError:
            venue_data['longitude'] = 'No data provided'

        venues.append(venue_data)

    return venues


# Method to query the foursquare API with different parameters
def foursquare_query(category_id, zip_code=None, coordinates=None, radius=None):
    if radius is None:
        radius = ''
    elif radius is not None:
        radius = 'radius=%s&' % radius
    if coordinates is None:
        coordinates = ''
    elif coordinates is not None:
        coordinates = 'll=%s&' % coordinates
    if zip_code is None:
        zip_code = ''
    elif zip_code is not None:
        zip_code = 'near=%s&' % zip_code
    elif coordinates is None and zip_code is None:
        abort(400)

    url = 'https://api.foursquare.com/v2/venues/search?%(COORDINATES)s%(ZIP_CODE)s%(RADIUS)scategoryId=%(CATEGORY_ID)s&intent=intent&client_id=' \
                     '%(CLIENT_ID)s&client_secret=%(CLIENT_SECRET)s&v=%(DATE)s&limit=50' % {'CATEGORY_ID': category_id,
                                                                                            'COORDINATES': coordinates,
                                                                                            'ZIP_CODE': zip_code,
                                                                                            'RADIUS': radius,
                                                                                            'CLIENT_ID': CLIENT_ID,
                                                                                            'CLIENT_SECRET': CLIENT_SECRET,
                                                                                            'DATE': DATE}
    data = json.loads(requests.get(url).text)
    return data


# Method for decoding the WKB geometry data
def get_ewkt(array, init=None):
    cnx = cnx_to_psql(db='teleport', user=POSTGRES_USER, host=POSTGRES_HOST)
    cur = cnx.cursor()
    if init is True:
        geom = array[2]
    else:
        geom = array[3]
    cur.execute("SELECT ST_AsEWKT(%(geom)s::geometry);", {'geom': geom})
    cnx.commit()
    ewkt = cur.fetchall()
    return ewkt


# Method to insert data into the postgres table
def insert_to_table(array, cnx, table=None):
    cur = cnx.cursor()

    if table == 'bayareadata':
        zip_code = array[0]
        po_name = array[1]
        geom = array[2]

        add_data = ("INSERT INTO " + table +
                    "(zip_code, po_name, geom) "
                    "VALUES (%s, %s, %s)")
        data = (zip_code, po_name, geom)
        cur.execute(add_data, data)
        cnx.commit()

    elif table == 'venues':
        for venue in array:
            try:
                zip_code = venue['zip_code']
            except KeyError:
                zip_code = None

            try:
                po_name = venue['po_name']
            except KeyError:
                po_name = 'No data provided'

            try:
                geom = venue['geom']
            except KeyError:
                geom = 'No data provided'

            try:
                venue_name = venue['name']
            except KeyError:
                venue_name = 'No data provided'

            try:
                url = venue['url']
            except KeyError:
                url = 'No data provided'

            try:
                category_name = venue['category_name']
            except KeyError:
                category_name = 'No data provided'

            try:
                address = venue['address']
            except KeyError:
                address = 'No data provided'

            try:
                latitude = venue['latitude']
            except KeyError:
                latitude = 'No data provided'

            try:
                longitude = venue['longitude']
            except KeyError:
                longitude = 'No data provided'

            add_data = ("INSERT INTO " + table +
                        "(zip_code, po_name, geom, category_name, address, latitude, longitude, venue_name, url) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)")
            data = (zip_code, po_name, geom, category_name, address, latitude, longitude, venue_name, url)

            cur.execute(add_data, data)
            cnx.commit()


# Method to parse the txt file into a postgres+postgis table
def txt_to_psql():
    cnx = cnx_to_psql(db='teleport', user=POSTGRES_USER, host=POSTGRES_HOST)

    entries = []

    script_dir = os.path.dirname(__file__)
    real_path = "static/bayareadata.txt"
    abs_file_path = os.path.join(script_dir, real_path)

    data = open(abs_file_path, 'r')

    # Header is separate
    header = data.readline()
    clean_header = (header.strip().split(sep='|'))
    rows = data.readlines()

    # Text file has unnecessary whitespace and flawed rows
    stripped_entry = [x.strip() for x in rows]

    for i in range(len(rows)):
        entry = stripped_entry[i].split(sep='|')
        if len(entry) < len(clean_header) or len(entry) > len(clean_header):
            continue

        entry[0] = int(entry[0])
        entry[2] = ("" + entry[2].replace(" ", "") + "")
        entry[2] = (get_ewkt(entry, True))[0]
        insert_to_table(entry, cnx, table='bayareadata')

        entries.append(entry)


def input_data(category):
    category_id = get_category_id(category=category)
    venues = []

    cnx = cnx_to_psql(db=POSTGRES_DB, user=POSTGRES_USER, host=POSTGRES_HOST)
    cur = cnx.cursor()
    cur.execute("SELECT * from bayareadata")
    rows = cur.fetchall()

    for row in rows:
        zip_code = str(row[1]).replace(' ', '')
        po_name = str(row[2])
        #geom = get_ewkt(row)
        geom = row[3]
        foursquare_response = foursquare_query(zip_code=zip_code, category_id=category_id)
        venues_list = foursquare_response['response']['venues']
        entry = create_venues_array(venues_list=venues_list, zip_code=zip_code, po_name=po_name, geom=geom)
        insert_to_table(entry, cnx, table='venues')
        venues.append(entry)
    response = {'venues': venues,
                'category': category}

    cur.close()
    output = dumpjson(response)
    return output


@bp.route('/')
def hello_tp():
    return 'Hello Teleport. This is me, Oskar!'


@bp.route('/single_zip/<zip_code>/<category>')
def single_zip(zip_code, category):
    category_id = get_category_id(category=category)
    rows = get_from_db(zip_code=zip_code)

    try:
        po_name = rows[2]
    except TypeError:
        abort(400)

    geom = rows[3]
    foursquare_response = foursquare_query(zip_code=zip_code, category_id=category_id, radius=QUERY_RADIUS)
    venues_list = foursquare_response['response']['venues']

    venues = create_venues_array(venues_list=venues_list, zip_code=zip_code, po_name=po_name, geom=geom)
    response = {'venues': venues,
                'category': category}

    output = dumpjson(response)
    return output


@bp.route('/multiple_zip/<zip_codes>/<category>')
def multiple_zip(zip_codes, category):
    zip_array = zip_codes.split(sep=',')
    category_id = get_category_id(category=category)
    venues = []

    for zip_code in zip_array:
        rows = get_from_db(zip_code=zip_code)

        try:
            po_name = rows[2]
        except TypeError:
            abort(400)

        geom = rows[3]
        foursquare_response = foursquare_query(zip_code=zip_code, category_id=category_id)
        venues_list = foursquare_response['response']['venues']
        venues.append(create_venues_array(venues_list=venues_list, zip_code=zip_code, po_name=po_name, geom=geom))

    response = {'venues': venues,
                'category': category}

    output = dumpjson(response)
    return output


@bp.route('/coord_radius/<lat_long>/<category>')
def coord_radius(lat_long, category):
    category_id = get_category_id(category=category)

    location = geolocator.reverse(lat_long)
    raw_location = location.raw
    zip_code = raw_location['address']['postcode']

    rows = get_from_db(zip_code=zip_code)
    try:
        po_name = rows[2]
    except TypeError:
        abort(400)
    geom = rows[3]
    foursquare_response = foursquare_query(coordinates=lat_long, category_id=category_id, radius=QUERY_RADIUS)
    venues_list = foursquare_response['response']['venues']

    venues = create_venues_array(venues_list=venues_list, zip_code=zip_code, po_name=po_name, geom=geom)

    response = {'venues': venues,
                'category': category}

    output = dumpjson(response)
    return output


init_db(db='postgres')
txt_to_psql()
input_data('cafe,gym')

app = Flask(__name__)
app.register_blueprint(bp, url_prefix=APP_URL_PREFIX)
CORS(app, resources=r'/*')

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=int(APP_PORT))
    app.run(use_reloader=False)
