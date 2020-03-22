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

import sqlite3
import scraper as scrp
import os

# What the script is going to do
# 0 (default) just get latest data from AIP
# 1 get all data available
# 2 get all data from a particular time point (specified on command line)
STATUS = 0


#%% Some functions
def insert_sensor_readings_latest(sensor_reading_latest_data):
    ''' Tries to insert data from the API in to the database using output from
    scraper.sensor_reading_latest() '''

    print('\nTrying to insert "sensor_reading_latest_data"...')
    
    # For checking whether there is already a reading with same time index
    duplicates = 0
    
    # loop through the rows (sensor readings)
    for sensor_number, row in sensor_reading_latest_data.iterrows():    
        #%% check whether there is already a sensor reading for this sensor at this time and pass continue if there is
        if check_for_duplicates(row) == 1:
            print('Sensor {}: {} already has reading for time {}.'
                  .format(sensor_number, 
                          smart_building.sensor_location_info['name'].loc[sensor_number], 
                          row['timestamputc']))
            duplicates +=1 
            continue
    
        insert_row(row)
        
    print('{} row(s) were skipped as sensor reading(s) already existed for that time.'
          .format(duplicates))


def insert_sensor_readings_after(sensor_reading_after):
    ''' Tries to insert data from the API in to the database using output from
    scraper.sensor_reading_after() '''
    
    print('\nTrying to insert "sensor_reading_after_data"...')

    # Loop through each index (sensor) in sensor_reading_after
    for sensor_dataframe in sensor_reading_after:
        print('Trying to insert readings from sensor {}, starting with most recent in current list...'\
              .format(sensor_dataframe['sensornumber'].loc[1]))
        # For checking whether there is already a reading with same time index
        duplicates = 0
        
        
        ##TODO: this loops through the dataframe backwards so because it is quicket. Best way?? Check 5 rows not 1
        # Loop through (sensor reading) for sensor dataframe by index in reverse i.e. from last row to row at 0th index.
        for row_num in range(sensor_dataframe.shape[0] - 1, -1, -1):
            # get row contents as series using iloc{] and index position of row
            # rowSeries = sensor_dataframe.iloc[i]
            row = sensor_dataframe.iloc[row_num]
            # print row contents
            # print('Trying to insert sensor {}, row {}'.format(row['sensornumber'], row_num))

            # # Loop through each row (sensor reading) for sensor 
            # for reading_no, row in sensor_dataframe.iterrows():
            
            #%% continue if already a sensor reading in database with same time index
            if check_for_duplicates(row) == 1:
               duplicates +=1
               n_rows_skipped = row_num+1
               print('The first {} row(s) were skipped for sensor {}, as sensor reading(s) '\
                     'already existed for that time.'
                     .format(n_rows_skipped,row['sensornumber']))
               break
        
            insert_row(row)


def insert_row(row):
    try:
        check = c.execute('INSERT INTO sensor_readings (time, timestampms, timestamputc, '\
            'sensor_number, sensor_name, co2, humidity, lux, noise, occupancy, '\
            'pressure, sensorlocation, temperature, voc) '\
            'VALUES(strftime(?,?),?,?,?,?,?,?,?,?,?,?,?,?,?)', \
            ['%s','now', row['timestampms'], str(row['timestamputc']), 
             row['sensornumber'], \
             row['name'], \
             row['co2'], row['humid'], row['lux'], row['noise'], \
             row['occupancy'], row['pressure'], row['sensorlocation'], \
             row['temperature'], row['voc']])
    except Exception as e:        
        print("Error: ", e)


def check_for_duplicates(row):
    ''''Check whether sensor reading exists in database for this sensor and time (ms).'''
    
    try:
        check = c.execute("SELECT EXISTS(SELECT sensor_name FROM sensor_readings "\
                      "WHERE timestamputc = ? AND sensorlocation = ?);", \
                      [str(row['timestamputc']), row['sensorlocation']])
    except Exception as e:
        print("Error: ", e)
    
    result = check.fetchone()[0]
 
    return(result)


def find_earliest_time():
    '''' Checks earliest reading for each sensor by calling scraper.sensor_reading_after() 
    with an input time before the sensors were installed. The first point returned 
    for each sensor will therefore be the earliest reading.'''

    sensor_reading_after_data, _ = smart_building.sensor_reading_after(timestamp_epoch_millisec=1546300800000)
    
    earliest_time_list = []
    for i in sensor_reading_after_data:
        earliest_time_list.append(i['timestampms'][1])
    earliest_time = min(earliest_time_list)

    return(earliest_time, sensor_reading_after_data)


def populate_database():
    ''' Calls API and returns readings from the earliest process, then in steps 
    of 1000 minutes until the current time. Note: runs based on earliest from 
    API, not from what exists in database.'''
    
    # check when to start collecting data from
    earliest_time, sensor_reading_after_data = find_earliest_time()

    # put current time into variable
    time_now = scrp.time_now()
    
    # insert the first time
    insert_sensor_readings_after(sensor_reading_after_data)

    # in steps of 1000 minutes, call API to retrieve data and insert into database.
    # Note: typical interval between sensor reading is 1 minute, API call returns max 1000 rows.
    for input_time in range(earliest_time, time_now, 60000000):
        sensor_reading_after_data, all_sensor_numbers = \
            smart_building.sensor_reading_after(timestamp_epoch_millisec=input_time)
        insert_sensor_readings_after(sensor_reading_after_data)


def populate_from(time_from):
    ''' Populates database with calls API from 'time_from' until now. time_now
    is an integer ms time epoch. API calls are made in steps of 1000 minutes. '''

    # get current time
    time_now = scrp.time_now()   
    
    # in steps of 1000 minutes, call API to retrieve data and insert into database.
    # Note: typical interval between sensor reading is 1 minute, API call returns max 1000 rows.
    for input_time in range(time_from, time_now, 60000000):
        sensor_reading_after_data, all_sensor_numbers = \
            smart_building.sensor_reading_after(timestamp_epoch_millisec=input_time)
        insert_sensor_readings_after(sensor_reading_after_data)


def restart():
    print("Connection error, restarting kernel...")
    os._exit(00)
    connect_to_database()    


def connect_to_database():
    ##TODO: DODGY USE OF GLOBAL VARIABLES WHILST TESTING. NEEDS SORTING OUT
    # Connect to the database (creates a Connection object)
    global conn, c

    try:
        global conn, c

        # connect to database
        conn = sqlite3.connect("./database.db")
    
        # Create a cursor to operate on the database
        c = conn.cursor()
    except Exception as e:
            print('Error: ', e)
    return()


#%% Program starts here

# Connect to the database
# os._exit(00)
connect_to_database()   
# Declare scraper instance
smart_building = scrp.Scraper()


#%% 
'''Try to add data for building, room, and sesnor info. Will skip if same data 
already exists in database. '''


#building_info
try:
    for i, row in smart_building.building_info.iterrows():
        c.execute('INSERT INTO buildings (building_id, building_number, '\
                  'building_name) VALUES(?,?,?)', 
                  [row['id'], i, row['name']])
except Exception as e:
    if str(e) == 'database is locked':
        print('Database is locked. Trying to reconnect to database... ')
        restart()             
    else:  
        print('Error: ', e)


#room_info
try:    
    for i, row in smart_building.room_info.iterrows():    
        c.execute('INSERT INTO rooms (room_id, room_number, room_name, '\
                  'building_id, building_name) '\
                  'VALUES(?,?,?,?,?)', [row['id'], i, row['name'], \
                                        row['building'], row['buildingname']])
except Exception as e:
    print("Error: ", e)


#sensor_info
try:
    for i, row in smart_building.sensor_location_info.iterrows():    
        c.execute('INSERT INTO sensors (sensor_id, sensor_number, sensor_name, '\
                  'room_id, room_name) '\
                  'VALUES(?,?,?,?,?)', [row['id'], i, row['name'], row['room'], \
                                        row['roomname']])
except Exception as e:
    print("Error: ", e)


#%% Collect sensor readings and put them into database
    
# get 1000 rows of data after a certain time for each sensor. Put in database
# 1546300800000 = Tue Jan 01 2019 00:00:00
# sensor_reading_after_data, all_sensor_numbers = \
#      smart_building.sensor_reading_after(timestamp_epoch_millisec=1546300800000)
# insert_sensor_readings_after(sensor_reading_after_data)

# get the latest 1 row of data from each sensor. Put in database
sensor_reading_latest_data, all_sensor_numbers = smart_building.sensor_reading_latest()
insert_sensor_readings_latest(sensor_reading_latest_data)

# populate from certain time 1546300800000. Input in ISO format: 2020-02-18T04:31:45
populate_from(1584760305102)
#

if STATUS==1:
    populate_database()
elif STATUS==2:
    pass






#%% Commit data to database and close up
conn.commit()
conn.close()