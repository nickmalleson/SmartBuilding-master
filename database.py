# Code to create, add to and retrieve from an sqlite database
# It requires the packages:
#   - 'pyodbc' which contains general functions for connecting to databases
#   - 'sqlite' which has sqlite drivers specifically (SQLite is the database we'll use)
#
# Good docs for sqlite access in python here: https://docs.python.org/3/library/sqlite3.html
#
# If you've not done so already you need to create the database first - e.g. by
# running the following on the command line:
#    sqlite3 database.db < create_database.sql

#%% Conect to the database

import sqlite3
import scraper as scrp

# Declare scraper instance
smart_building = scrp.Scraper()

# Connect to the database (creates a Connection object)
conn = sqlite3.connect("./database.db")

# Create a cursor to operate on the database
c = conn.cursor()


#%% Add some data
#building_info
try:
    for num, i in enumerate(smart_building.building_info, start=1):    
        c.execute('INSERT INTO buildings (building_id, building_number, building_name) VALUES(?,?,?)', [i['id'], num, i['name']])
except Exception as e:
    print("Error: ", e)

#room_info
try:    
    for num, i in enumerate(smart_building.room_info, start=1):    
        c.execute('INSERT INTO rooms (room_id, room_number, room_name, building_id, building_name) '\
                  'VALUES(?,?,?,?,?)', [i['id'], num, i['name'], i['building'], i['buildingname']])
except Exception as e:
    print("Error: ", e)

#sensor_info
try:
    for num, i in enumerate(smart_building.sensor_location_info, start=1):    
        c.execute('INSERT INTO sensors (sensor_id, sensor_number, sensor_name, room_id, room_name) '\
                  'VALUES(?,?,?,?,?)', [i['id'], num, i['name'], i['room'], i['roomname']])
except Exception as e:
    print("Error: ", e)

#sensor_readings
#TODO: condition that it deosnt save if there is already a reading with the same time point, per sensor
sensor_reading_latest_data, all_sensor_numbers = smart_building.sensor_reading_latest()

for i, j in zip(sensor_reading_latest_data, all_sensor_numbers):
    try:
        if not i:
            print('No data returned for sensor {}.'.format(j))
            continue 
        c.execute('INSERT INTO sensor_readings (time, sensor_number, sensor_name, co2, humidity, '\
                  'lux, noise, occupancy, pressure, sensorlocation, temperature, timestamputc, voc) '\
                  'VALUES(strftime(?,?),?,?,?,?,?,?,?,?,?,?,?,?)', \
                  ['%s','now', \
                   j, \
                   smart_building.sensor_location_info[j-1]['name'], \
                   i['co2'], i['humid'], i['lux'], i['noise'], i['occupancy'], i['pressure'], \
                   i['sensorlocation'],\
                   i['temperature'], \
                   i['timestamputc'], \
                   i['voc']])
    except Exception as e:
        print("Error: ", e)

# Lets see whats in each room
c.execute('SELECT * FROM rooms')
print(c.fetchall())

# See what sensor names there are
c.execute('SELECT sensor_name FROM sensors')
print(c.fetchall())

conn.commit()

conn.close()   