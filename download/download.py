# connect to the API
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from datetime import date

print("Start")

api = SentinelAPI('user', 'pass', 'https://apihub.copernicus.eu/apihub')

print("Logged")

# search by polygon, time, and SciHub query keywords
footprint = geojson_to_wkt(read_geojson('map_centralhighlands.geojson'))
#footprint = geojson_to_wkt(read_geojson('map_centralbresil_z6.geojson'))
#products = api.query(footprint, date=('20200101', date(2021, 12, 31)), platformname='Sentinel-1', filename = 'S1A_IW*', relativeorbitnumber = '18', slicenumber = '3', producttype ='GRD', orbitdirection='DESCENDING', sensoroperationalmode='IW')

#print("footprint")
#print(footprint)

products = api.query(footprint, date=('20210101', date(2021, 12, 31)), platformname='Sentinel-1', filename = 'S1A_IW*', relativeorbitnumber = '120', producttype ='GRD', orbitdirection='DESCENDING', sensoroperationalmode='IW', limit=10)

#products = api.query(footprint, date=('20210101', date(2021, 12, 31)), platformname='Sentinel-1', filename = 'S1A_IW*', producttype ='GRD', orbitdirection='DESCENDING', sensoroperationalmode='IW', limit=10)

print("start download")
#print(products)

# download all results from the search
api.download_all(products, "H:\\TM\\data\\Highlands")
# duong dan luu anh	
