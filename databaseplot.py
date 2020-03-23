# -*- coding: utf-8 -*-
"""
Created on Thu Mar 12 18:04:38 2020

@author: medtcri
"""
import sqlite3
import scraper as scrp
from dateutil.parser import parse
import getpass  # required to keep password invisible
from matplotlib.ticker import MaxNLocator
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import requests as r  # required to acesss API
import sys
import time
import datetime as dt


def time_now():
    ''' Get the current time as ms time epoch'''
    return(int(round(time.time() * 1000)))


def choose_time():
    ''' Get user input to choose a time in ms time epoch. 
    Times are equivalent to those at https://currentmillis.com/ '''
    
    ##TODO: why /1000??
    # get time before earliest sensor reading.
    earliest_time_ms = 1580920305102
    earliest_time_utc = dt.datetime.utcfromtimestamp(int(earliest_time_ms/1000)).isoformat()

    # get time now
    time_now_ms = time_now()
    time_now_utc = dt.datetime.utcfromtimestamp(int(time_now_ms/1000)).isoformat() 

    chosen_times = input('Choose start and end time to plot in ms epochs in format '\
                         '"[start, end]". or press enter full time range. For '\
                         'example for 1st to 2nd March, enter: [1583020800000, 1583107200000].'\
                         '\nEarliest:\n    ms:  {}\n    UTC: {}'\
                         '\nLatest:\n    ms:  {}\n    UTC: {}\n>>' 
                         .format(earliest_time_ms, earliest_time_utc,
                                 time_now_ms, time_now_utc))

    # By default, choose from earilest time to now
    if not chosen_times:        
        time_from_ms = earliest_time_ms
        time_from_utc = earliest_time_utc
        time_to_ms = time_now_ms
        time_to_utc = time_now_utc
    
    # otherwise, evalute the times inputted.
    else:
        chosen_times = eval(chosen_times)
        time_from_ms = chosen_times[0]
        time_to_ms = chosen_times[1]
        time_from_utc = dt.datetime.utcfromtimestamp(int(time_from_ms/1000)).isoformat()
        time_to_utc = dt.datetime.utcfromtimestamp(int(time_to_ms/1000)).isoformat() 
    
    # print what the chosen time range.
    print('Chosen time range from {} to {}.'.format(time_from_utc, time_to_utc))
    return(time_from_ms, time_to_ms)

  
def retrieve_data(sensor_number, time_from=1580920305102, time_to=time_now()):
    ''' Retrieve data from the database based on sensor number and timeframe using pd.read_sql.
    https://stackoverflow.com/questions/24408557/pandas-read-sql-with-parameters/24418294 
    '''
  
    data_to_plot = pd.read_sql('SELECT time, timestampms,timestamputc, occupancy, voc, co2, '\
                               'temperature, pressure, humidity, lux, noise, sensorlocation '\
                               'FROM sensor_readings WHERE timestampms '\
                               'BETWEEN ? AND ? AND sensor_number = ? '\
                               'ORDER BY timestamputc;',     
                               conn, params=[time_from, time_to, sensor_number])

    if data_to_plot.empty:
        print('No data for this time range for sensor number {}.'.format(sensor_number))

    return(data_to_plot)


def plot_from_dataframe(sensor_number=None, data_to_plot=None):
    ''' Plot sensor data retrieved from database with retrieve_data(). 
    Plots all types of data from one sensor number. No upper limit on how many 
    datapoints.
    
    data_to_plot = dataframe from retrieve_data()
    sensor_number = int which corresponds to index in scraper.sensor_location_info.
    '''

    # the labels to look for in the dataframe.
    paramlabels = ['occupancy', 'voc', 'co2', 'temperature', \
                   'pressure', 'humidity', 'lux', 'noise']

    # the labels to plot on the graph
    plotlabels = ['Occupancy\n(n)', 'VOC\n(ppm?)', 'CO2\n(ppm?)',
                  'Temperature\n(°C)', 'Pressure\n(mBar)',
                  'Humidity\n(RH)', 'Light Intensity\n(lux)',
                      'Noise Levels\n(dB)']
    
    # Convert dates to datetime format
    data_to_plot['timestamputc'] =\
        pd.to_datetime(data_to_plot['timestamputc'])
    # set as index
    data_to_plot = data_to_plot.set_index(
        'timestamputc')
    
    axtitle = str('Sensor readings (after) from sensor number {}: {}.'
                  .format(sensor_number,
                          smart_building.sensor_location_info['name'].loc[sensor_number]))
    axes = data_to_plot[paramlabels].plot(marker='.', alpha=0.5,
                                               figsize=(12, 26),
                                               subplots=True,
                                               linewidth=1,
                                               markersize=2.5,
                                               title=axtitle)
    
    for i, ax in enumerate(axes, start=0):
        ax.set_ylabel(plotlabels[i], rotation='horizontal',
                      fontsize=10, ha='right', va='baseline')
    
    plt.xlabel('Time')
    locator = mdates.AutoDateLocator(minticks=8, maxticks=14)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    plt.show()


def plot_from_database(time=None, room_numbers=None):
    #Choose the time range. E.g. 1st to 2nd March: [1583020800000, 1583107200000]
    if time == None:
        time_from, time_to = choose_time()
    
    if room_numbers == None:
        scrp.choose_by_number(smart_building.room_info)
    
    # choose the sensors to plot
    chosen_numbers, chosen_names = scrp.choose_by_number(smart_building.sensor_location_info)    
        
    for sensor_number in chosen_numbers:
        try:
            # retrieve the data
            data_to_plot = retrieve_data(sensor_number, time_from, time_to)
            plot_from_dataframe(sensor_number, data_to_plot)
        except Exception as e:
            print("Error with sensor number {}: {}.".format(sensor_number, e) )   


#%% Program starts here

# Declare scraper instance
smart_building = scrp.Scraper()

# Connect to the database (creates a Connection object)
conn = sqlite3.connect("../database/database.db")

# Create a cursor to operate on the database
c = conn.cursor()

# this is the time of the earliest sensor reading in the database
earliest_time = 1580920300000

# run program
plot_from_database()

#close the connection
conn.close()