# Teleport. SF Bay Area Cafe/Fitness scraper/API  

**What did I use and why?**  
Flask for the API framework. It is simple and lightweight.  
psycopg2 for the Postgres connector. Since I've worked with MySQL before, pyscopg2's connector syntax was most similar to that of MySQL's.  
Used flask's CORS to avoid any frontend hiccups.  
Shapely's geos for EWKB and EWKT handling.  
Geopy to get as much data as possible (some Foursquare respones lacked address related fields).  
Added a tornado multithreader library when to use it production with Docker.      


**How it works?**  
1) It starts by connecting to a local postgres server (default database name postgres) and creates a database named **'teleport'**  
2) Adds the postgis extension to the newly created database and creates two tables: **'venues'** and **'bayareadata'**  
3) Starts the method txt_to_psql(), which takes the given bayareadata.txt file and parses it into the bayareadata table.  
4) Then the longest process starts: input_data():  
    Takes every zip code from the bayareadata table and queries the foursquare API. Returns a filled venues table with every column from the bayareadata table and selected fields from the foursquare API's response.      


**API**  
Three endpoints, all result a **JSON** response. Each query is backed by the bayareadata table as it will result with additional data from there.   


**endpoints:**  
Possible category slugs: 'cafe', 'gym' and 'cafe/gym'  
**/single_zip/\<zip_code\>/\<category\>**  
Searches the Foursquare API for venues matching the zip code.  


**/multiple_zip/\<zip_codes\>/\<category\>**  
Similar to single_zip, except you can insert an unlimited amount of zip codes, separated by a comma.


**/coord_radius/\<lat_long\>/\<category\>**  
Instead of a zip code, this method returns venues based on given coordinates.
  
  
**Environment variables (and presets):**  
'APP_PORT' = 80  
'APP_URL_PREFIX' = ''  
'POSTGRES_HOST' = 'localhost'  
'POSTGRES_USER' = 'postgres'  
'POSTGRES_PW' = 'password'  
'POSTGRES_DB' = 'teleport'  
'QUERY_RADIUS' = '300'    
  
  
**Foursquare API auth:**  
'CLIENT_ID' = 'UMZ5JVTFVF5TBPY5GYFIJV2VGPF3VBHWZWVYHMGNDVEWN5RE'  
'CLIENT_SECRET' = 'ALSIDWNM53IILXJXHGGKFKTPLSA2C1TBMJYGED2NWAZ35IFX'      


**Set up the env**  
I've included the Dockerfile and requirements file, I could not get it connect to my local Postgres server, maybe it will work for you (image takes a while to build though).  
Discarding the previous: run 'python3 teleport.py', connect on 'http://127.0.0.1:5000/'  


**What to improve?**  
Make it a full RESTful service, right now it only has GET methods, which as I understand is suitable for basic requests.  
Secondly, I would add addtional data to the venues: ratings, type (e.g. vegetarian), is it child friendly etc.  
Additionally, I would improve the postgres handling, right now if the service would go down, it would start adding the data on top of the old one.  
Lastly, with more time I could write the code to be faster and smaller.  Needs a lot of error handling done as well.  


**Additional info**  
It was my first time working with PostgreSQL, more complex than MySQL, which I have used before. Building the docker images and trying to make them communicate took a long time which resulted in a failure (hopefully just an issue with my local machine).  
Since I did this project from my free time, I calculated an estimate of how many hours this took:  
24 hours. About 8 of that went into the Docker + PostgreSQL bit.  