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
import pandas as pd

# What the script is going to do
# 0 (default) just get latest data from AIP
# 1 get all data available
# 2 get all data from a particular time point (specified on command line)
STATUS = 0

#%%
class Database():
    '''Obtains details of existing database entries.
    '''

    def __init__(self):
            
        self.conn, self.c = Database._connect_to_database(self)        
        self.existing_readings = Database._retrieve_existing_readings(self)
        self.smart_building = scrp.Scraper()


    @staticmethod
    def _connect_to_database(self):
        ##TODO: DODGY USE OF GLOBAL VARIABLES WHILST TESTING. NEEDS SORTING OUT
        # Connect to the database (creates a Connection object)
        # global conn, c
    
        try:
            # global conn, c
    
            # connect to database
            conn = sqlite3.connect("../database/database.db")
        
            # Create a cursor to operate on the database
            c = conn.cursor()
        except Exception as e:
                print('Error: ', e)
        return(conn, c)
 
    
    @staticmethod
    def _retrieve_existing_readings(self):
        '''Obtains details of existing database entries to check against.
        Returns a dataframe containing a list of existing time readings and
        corresponding sensor numbers
        '''

        try:
            existing_readings = pd.read_sql('SELECT timestampms, sensorlocation ' \
                                            'FROM sensor_readings '\
                                            'ORDER BY timestamputc;',     
                                            self.conn)
            ##TODO: This check does not currently function properly or check the right thing
            if any(existing_readings.applymap(type)==bytes):
                print("Database contains timestamps in 'bytes' format when they "\
                        "should be int64.")
            return(existing_readings)
        except Exception as e:        
            print("Error: ", e)       


    def restart(self):
        print("Connection error, restarting kernel...")
        os._exit(00)
        self.connect_to_database()    


    def insert_row(self, row):
        try:
            check = self.c.execute('INSERT INTO sensor_readings (time, timestampms, timestamputc, '\
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


    def check_for_duplicates(self, row):
        ''''Check whether sensor reading exists in database for this sensor and time (ms).'''
        if self.existing_readings is None:
            return(0)
        else:
            test = self.existing_readings.loc[ \
                      (self.existing_readings['timestampms'] == row['timestampms']) & \
                      (self.existing_readings['sensorlocation'] == row['sensorlocation'])]

        if len(test) > 0:
            return(1)
        else:
            return(0)


    #%% Some functions
    def insert_sensor_readings_latest(self, sensor_reading_latest_data):
        ''' Tries to insert data from the API in to the database using output from
        scraper.sensor_reading_latest() '''
    
        print('\nTrying to insert "sensor_reading_latest_data"...')
        
        # For checking whether there is already a reading with same time index
        duplicates = 0
        
        # loop through the rows (sensor readings)
        for sensor_number, row in sensor_reading_latest_data.iterrows():    
            #%% check whether there is already a sensor reading for this sensor at this time and pass continue if there is
            if self.check_for_duplicates(row) == 1:
                print('Sensor {}: {} already has reading for time {}.'
                      .format(sensor_number, 
                              self.smart_building.sensor_location_info['name'].loc[sensor_number], 
                              row['timestamputc']))
                duplicates +=1 
                continue
        
            self.insert_row(row)
            
        print('Readings from {} sensor(s) skipped as sensor reading(s) already existed for that time.'
              .format(duplicates))
    
    
    def insert_sensor_readings_after(self, sensor_reading_after):
        ''' Tries to insert data from the API in to the database using output from
        scraper.sensor_reading_after() '''
        
        print('\nTrying to insert "sensor_reading_after_data"...')
    
        # Loop through each index (sensor) in sensor_reading_after
        for sensor_dataframe in sensor_reading_after:
            print('Trying to insert readings from sensor {}...'\
                  .format(sensor_dataframe['sensornumber'].loc[1]))
            # For checking whether there is already a reading with same time index
            duplicates = 0

            for sensor_number, row in sensor_dataframe.iterrows():  
                #%% continue if already a sensor reading in database with same time index
                if self.check_for_duplicates(row) == 1:
                   duplicates +=1
                   continue

                self.insert_row(row)

            print('{} duplicate readings sensor readings not inserted for sensor {}.'
                  .format(duplicates,row['sensornumber']))



    def find_earliest_time(self):
        '''' Checks earliest reading for each sensor by calling scraper.sensor_reading_after() 
        with an input time before the sensors were installed. The first point returned 
        for each sensor will therefore be the earliest reading.'''
    
        sensor_reading_after_data, _ = \
            self.smart_building.sensor_reading_after(timestamp_epoch_millisec=1546300800000)
        
        earliest_time_list = []
        for i in sensor_reading_after_data:
            earliest_time_list.append(i['timestampms'][1])
        earliest_time = min(earliest_time_list)
    
        return(earliest_time, sensor_reading_after_data)
    
    
    def populate_database(self):
        ''' Calls API and returns readings from the earliest process, then in steps 
        of 1000 minutes until the current time. Note: runs based on earliest from 
        API, not from what exists in database.'''
        
        # check when to start collecting data from
        earliest_time, sensor_reading_after_data = self.find_earliest_time()
    
        # put current time into variable
        time_now = scrp.time_now()
        
        # insert the first time
        self.insert_sensor_readings_after(sensor_reading_after_data)
    
        # in steps of 1000 minutes, call API to retrieve data and insert into database.
        # Note: typical interval between sensor reading is 1 minute, API call returns max 1000 rows.
        for input_time in range(earliest_time, time_now, 60000000):
            sensor_reading_after_data, all_sensor_numbers = \
                self.smart_building.sensor_reading_after(timestamp_epoch_millisec=input_time)
            self.insert_sensor_readings_after(sensor_reading_after_data)


    def populate_from(self, time_from):
        ''' Populates database with calls API from 'time_from' until now. time_now
        is an integer ms time epoch. API calls are made in steps of 1000 minutes. '''
    
        # get current time
        time_now = scrp.time_now()   
        
        # in steps of 1000 minutes, call API to retrieve data and insert into database.
        # Note: typical interval between sensor reading is 1 minute, API call returns max 1000 rows.
        for input_time in range(time_from, time_now, 60000000):
            sensor_reading_after_data, all_sensor_numbers = \
                database.smart_building.sensor_reading_after(timestamp_epoch_millisec=input_time)
            self.insert_sensor_readings_after(sensor_reading_after_data)


#%% Program starts here

# Connect to the database
# os._exit(00)
database = Database()

# sensor_reading_latest_data, all_sensor_numbers = database.smart_building.sensor_reading_latest()
# database.insert_sensor_readings_latest(sensor_reading_latest_data)



# get 1000 rows of data after a certain time for each sensor. Put in database
# 1584835200000 = Sun Mar 22 2020 00:00:00
# sensor_reading_after_data, all_sensor_numbers = \
#       database.smart_building.sensor_reading_after(timestamp_epoch_millisec=1584835200000)
# database.insert_sensor_readings_after(sensor_reading_after_data)


#%% 
'''Try to add data for building, room, and sesnor info. Will skip if same data 
already exists in database. '''


#building_info
try:
    for i, row in database.smart_building.building_info.iterrows():
        database.c.execute('INSERT INTO buildings (building_id, building_number, '\
                  'building_name) VALUES(?,?,?)', 
                  [row['id'], i, row['name']])
except Exception as e:
    if str(e) == 'database is locked':
        print('Database is locked. Trying to reconnect to database... ')
        database.restart()             
    else:  
        print('Error: ', e)


#room_info
try:    
    for i, row in database.smart_building.room_info.iterrows():    
        database.c.execute('INSERT INTO rooms (room_id, room_number, room_name, '\
                  'building_id, building_name) '\
                  'VALUES(?,?,?,?,?)', [row['id'], i, row['name'], \
                                        row['building'], row['buildingname']])
except Exception as e:
    print("Error: ", e)


#sensor_info
try:
    for i, row in database.smart_building.sensor_location_info.iterrows():    
        database.c.execute('INSERT INTO sensors (sensor_id, sensor_number, sensor_name, '\
                  'room_id, room_name) '\
                  'VALUES(?,?,?,?,?)', [row['id'], i, row['name'], row['room'], \
                                        row['roomname']])
except Exception as e:
    print("Error: ", e)


#%% Collect sensor readings and put them into database
    

# get the latest 1 row of data from each sensor. Put in database
# sensor_reading_latest_data, all_sensor_numbers = database.smart_building.sensor_reading_latest()
# database.insert_sensor_readings_latest(sensor_reading_latest_data)

# # populate from certain time 1584662400000. Input in ISO format: Fri Mar 20 2020 00:00:00
database.populate_from(1584316800000)
#

if STATUS==1:
    database.populate_database()
elif STATUS==2:
    pass


#%% Commit data to database and close up
database.conn.commit()
database.conn.close()