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


class Database():
    '''Obtains login details and stores data associated with the account in co-
    stant variables.
    '''

    def __init__(self):
            self.sensor_location_info = self.get_table_info('sensors', 'sensor_number')
            print("Sensor locations retrieved successfully.")
            self.room_info = self.get_table_info('rooms', 'room_number')
            print("Room information retrieved successfully.")

    def get_table_info(self,table, index_col):
        dataframe = pd.read_sql('select * from {};'.format(table), conn)
        dataframe = dataframe.set_index(index_col)
        return(dataframe)


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


def build_param_string(parameters):

    param_string = parameters[0]    
    for i in range(1,len(parameters)):
        param_string = param_string + ', ' + parameters[i] 

    return(param_string)


def build_values_string(values):

    values_string = 'WHERE timestampms BETWEEN ? AND ? AND sensor_number = ? '

    if isinstance(values, int):
       return(values_string)
    else:
        for i in range(1,len(values)):
            values_string = values_string + 'OR timestampms BETWEEN ? AND ? AND sensor_number = ? ' 

        return(values_string)


def retrieve_data(sensor_numbers, time_from=1580920305102, time_to=time_now(), parameters=None):
    ''' Retrieve data from the database based on sensor number and timeframe using pd.read_sql.
    https://stackoverflow.com/questions/24408557/pandas-read-sql-with-parameters/24418294 
    '''

    value_string = build_values_string(sensor_numbers)


    param_list = ['occupancy', 'voc', 'co2', 'temperature', 'pressure', \
                  'humidity', 'lux', 'noise']

    if parameters is None:
        parameters = param_list
    
    if isinstance(parameters, list):
        param_string = build_param_string(parameters)
    elif isinstance(parameters, str):
        param_string = parameters
    else:
        ('Format of input variable "paramaters" not recognised.')

    if isinstance(sensor_numbers, int):
        sql_params=[time_from, time_to, sensor_numbers]
    elif isinstance(sensor_numbers, list):
        sql_params = []
        for i in sensor_numbers:
            sql_params = sql_params + [time_from, time_to, i]


    data_to_plot = pd.read_sql('SELECT time, timestampms, timestamputc, sensor_number, '\
                               'sensorlocation, {} '\
                               'FROM sensor_readings '\
                               '{}'\
                               'ORDER BY timestamputc;' .format(param_string, value_string), \
                             conn, params=sql_params  )

    if data_to_plot.empty:
        print('No data for this time range for sensor number {}.'.format(sensor_numbers))

    return(data_to_plot)


def plot_from_dataframe(data_to_plot=None, room_number=None, overlay=0, aggregated=0):
    ''' Plot sensor data retrieved from database with retrieve_data(). 
    Plots all types of data from one sensor number. No upper limit on how many 
    datapoints.
    
    data_to_plot = dataframe from retrieve_data()
    sensor_number = int which corresponds to index in scraper.sensor_location_info.
    '''
    
    if len(data_to_plot.sensor_number.unique()) != 1:
        # aggregated = 1
        if room_number:
            print('Plotting aggregated data for room_number {}: {}.'\
                  .format(room_number, smart_building.room_info['name'].loc[room_number]))
            # print('Error: "plot_from_dataframe" function can only take one sensor at a time.')
    else:
        aggregated = 0
        sensor_number = data_to_plot.sensor_number.unique()[0]
    
    # get parameters from columns headings 
    column_headings = list(data_to_plot.columns)
    
    # the labels to look for in the dataframe.
    all_param_labels = ['occupancy', 'voc', 'co2', 'temperature', \
                   'pressure', 'humidity', 'lux', 'noise']

    # the labels to plot on the graph
    all_plot_labels = ['Occupancy\n(n)', 'VOC\n(ppm?)', 'CO2\n(ppm?)',
                  'Temperature\n(°C)', 'Pressure\n(mBar)',
                  'Humidity\n(RH)', 'Light Intensity\n(lux)',
                  'Noise Levels\n(dB)']

    # if parameters == None:
    #     paramlabels = all_param_labels
    #     plotlabels = all_plot_labels
    # else:
    paramlabels = []
    plotlabels= []
    
    for parameter in column_headings:
        if parameter in all_param_labels:
            paramlabels.append(all_param_labels[all_param_labels.index(parameter)])
            plotlabels.append(all_plot_labels[all_param_labels.index(parameter)])

    

    # Convert dates to datetime format
    data_to_plot['timestamputc'] =\
        pd.to_datetime(data_to_plot['timestamputc'])
    # set as index
    data_to_plot = data_to_plot.set_index('timestamputc')
    
    
    
    if aggregated == 0:
        axtitle = str('Sensor readings')
            # str('Sensor readings from sensor number {}: {}.'
                      # .format(sensor_number,
                          # smart_building.sensor_location_info['name'].loc[sensor_number]))
    else:
        axtitle = str('Aggregated sensor readings for room {}: {}.' 
                      .format(room_number, 
                          smart_building.room_info['name'].loc[room_number]))


    #%% THIS WORKS AND ARE PROBABLY FOR BEST ONES
    sensor_numbers = list(set(data_to_plot['sensor_number']))
    sensor_names = list(smart_building.sensor_location_info['name'])
    fontsizeL = 18
    fontszieS = 16
    
    pause = 1

    fig, axes = plt.subplots(len(paramlabels),  figsize=(15, 15), sharex=True)

    if len(paramlabels)== 1:
        axes = [axes]
        
    for j in range(0,len(paramlabels)):
        for i, sensor_number in enumerate(sensor_numbers, start=0):
            axes[j].plot(data_to_plot[paramlabels[j]].loc[\
                            data_to_plot['sensor_number']==sensor_number],\
                                                marker='.', alpha=0.5,
                                                linewidth=1.5,
                                                markersize=6)
            axes[j].set_ylabel(plotlabels[j], rotation='horizontal',
                       ha='right', va='baseline', fontsize=fontsizeL, wrap=True)


    # axes = [plt.gca()]
    pos1 = axes[0].get_position() # get the original position 
    # pos2 = [pos1.x0, pos1.y0,  pos1.width*0.5, pos1] 
    # # axes = plt.gca()
    
    # defaults: left = 0.125  ight = 0.9
    plt.subplots_adjust(left=0.125, right=0.75)
    # working ones: plt.subplots_adjust(left=0.125, right=0.8)
    # axes.set_position(pos2) # set a new position

    # box = axes[0].get_position()
    # axes.set_position([box.x0, box.y0, box.width * 0.8, box.height])

    leg = axes[0].legend(sensor_names, frameon=False, fontsize=fontsizeL, markerscale = 3,\
                     bbox_to_anchor=(1, 1))
        # , loc='upper left')
        
                     # , borderaxespad=0., loc='upper left', bbox_to_anchor=(1, plt.y1), loc=2, borderaxespad=0.)
                    #was 9.5
                    
    for line in leg.get_lines():
        line.set_linewidth(3)

    plt.xlabel('Time', fontsize=fontsizeL)
    plt.rcParams.update({'font.size': fontszieS})

    locator = mdates.AutoDateLocator(minticks=4, maxticks=8)
    formatter = mdates.ConciseDateFormatter(locator)
    axes[-1].xaxis.set_major_locator(locator)
    axes[-1].xaxis.set_major_formatter(formatter)

    # fig.savefig('../Plots/aaa.png', aspect='auto', dpi=fig.dpi)
    fig.savefig('../Plots/aaa.png', dpi=500)

    plt.show()


# def get_lists_from_number(numbers, dataframe):    
#     ''' Returns lists of values from coloumn_name in dataframe corresponding to certain index numbers.'''
#     value_strings = list(dataframe[column_name].index.isin(numbers))
#     return(numbers, value_strings)


def aggregate_data(data_to_aggregate):

    data_copy = data_to_aggregate.copy()
    # round times in data_to_pot to nearest minute
    data_to_aggregate['timestamputc'] = pd.to_datetime(data_to_aggregate['timestampms'], unit='ms')    
    data_to_aggregate['timestamputc'] = data_to_aggregate['timestamputc'].dt.floor('Min')
    # data_to_aggregate['timestamputc'] = data_to_aggregate['timestamputc'].dt.floor('ms')
    
    # data_to_aggregate['timestamputc'] = data_to_aggregate['timestamputc'].astype(str).apply(parse)
    
    data_to_aggregate['timestampms'] = data_to_aggregate[['timestamputc']].apply( \
         lambda x: x[0].timestamp(), axis=1).astype('int64')*1000


    # PERFORM THE AGGREGATION
    aggregated_data = data_to_aggregate.groupby( \
             ['timestampms', 'sensor_number'], as_index=False)['occupancy'].mean()
    
    aggregated_data = aggregated_data.groupby(['timestampms']).sum()
        
    
    
    
    # ['timestampms', 'sensor_number'])
    # aggregated_data = data_to_aggregate.groupby(['timestampms']).sum()

    aggregated_data['timestampms'] = aggregated_data.index
    # 1 NANOSECOND ADDDED TO THE TIME TO PRESERVE TIME FORMAT. ESSENTIAL TO RUN.
    aggregated_data['timestamputc'] = aggregated_data['timestampms'] \
        .apply(lambda t: dt.datetime.utcfromtimestamp(int(t/1000)).isoformat()+'.000001+00:00')
    # aggregated_data['timestamputc'] = aggregated_data['timestamputc'].apply(parse)

    
    ### THESE WERE PRETTY GOOD
    # aggregated_data['timestamputc'] = pd.to_datetime(aggregated_data.index, unit='ms', infer_datetime_format=True)
    # aggregated_data['timestamputc'] = pd.DatetimeIndex(aggregated_data['timestamputc'], tz='utc')
    # aggregated_data['timestamputc'] = aggregated_data['timestamputc'].astype(str).apply(parse)
    ### THESE WERE PRETTY GOOD



    whats = 1
    # aggregated_data['timestamputc'] =\
    #     aggregated_data.index.dt.datetime.utcfromtimestamp().isoformat()
    
    # Series(s.values,index=pd.to_datetime(s,unit='s'))
    # pd.DatetimeIndex(aggregated_data['timestamputc'], tz='utc')
    
    
    return(aggregated_data)
            
    
            
    
    
    
        # data_to_aggregate['new'] = pd.Timestamp(data_to_aggregate['timestamputc'])
        
        # int(data_to_aggregate['timestamputc'][0].timestamp())*1000


        
        # data_to_aggregate['timestamputc'] = data_to_aggregate['timestamputc'].To_timestamp() * 1000
        
        # # .dt.timestamp()
        # datetime.values.astype(np.int64) // 10 ** 9

        # data_to_aggregate['timestampms'] = pd.DataFrame.to_timestamp(data_to_aggregate['timestamputc'])
        # data_to_aggregate['timestamputc'].datetime.astype('int64')
        
            
            # groupby(['Team', 'Position']) 
                # sensor_reading_latest['timestampms'] = sensor_reading_latest[['timestamputc']].apply(lambda x: x[0].timestamp(), axis=1).astype('int64')*1000

        
                # input_time = dt.datetime.utcfromtimestamp(int(timestamp_epoch_millisec/1000)).isoformat()

        
        
        
#         apply(replace(second=0, microsecond=0))
        
        
#         data_to_plot['timestampms'].replace(second=0, microsecond=0)

        
#         test_time = 1584920729069
#         test_time_utc= pd.to_datetime(test_time , unit='ms')        
#         newdatetime = test_time_utc.replace(second=0, microsecond=0)
        
        
#         data_to_plot['timestampms']
#         data_to_plot['timestamputc'] = pd.to_datetime(aggregated_data['timestampms'], unit='ms')

        
        
        
#         aggregated_data['timestampms'] = aggregated_data.index
#         aggregated_data['timestamputc'] = pd.to_datetime(aggregated_data['timestampms'], unit='ms')

        
        
#         aggregated_data = data_to_plot.groupby('timestampms').sum()
        
        
#         aggregated_data['timestampms'].timestamp.dt.round('1m')
        
#         datetime.datetime.strptime(when, '%Y-%m-%d').date()

#         test_time = 1584920729069
#         test_time_utc= pd.to_datetime(test_time , unit='ms')        
#         newdatetime = test_time_utc.replace(second=0, microsecond=0)

        
#         datetime.datetime.strptime(test_time_utc, '%Y-%m-%d').date()
        
        
#         data_to_plot['timestamputc'] = pd.to_datetime(aggregated_data['timestampms'], unit='ms')

        
        
#         .timestamp.dt.round('1m')
        
        
#         aggregated_data['timestampms'] = aggregated_data.index
#         aggregated_data['timestamputc'] = pd.to_datetime(aggregated_data['timestampms'], unit='ms')

            
#             aggregated_data['timestampms'].apply(parse)
#             dt.datetime.utcfromtimestamp(int(aggregated_data['timestampms']/1000)).isoformat()

# aggregated_data[['timestampms']].apply(
    
#     dt.datetime.utcfromtimestamp(aggregated_data['timestampms'].astype(int)).isoformat()
    
#     .astype('int64')/1000
    
#     lambda x: x[0].utcfromtimestamp(), axis=1).astype('int64')/1000

 
# sensor_reading_latest['timestamputc'] = sensor_reading_latest['timestamputc'].apply(parse)
# sensor_reading_latest['timestampms'] = sensor_reading_latest[['timestamputc']].apply(lambda x: x[0].timestamp(), axis=1).astype('int64')*1000

#     dt.datetime.utcfromtimestamp((aggregated_data['timestampms']/1000).astype(int)).isoformat()


 
#         sensor_reading_latest['timestamputc'] = sensor_reading_latest['timestamputc'].apply(parse)
#         sensor_reading_latest['timestampms'] = 
        
        
# sensor_reading_latest[['timestamputc']].apply(lambda x: x[0].timestamp(), axis=1).astype('int64')*1000



# (aggregated_data['timestampms']/1000).astype(int)


# df['datetime'] = pd.to_datetime(df['date'])


# int(aggregated_data.index/1000)


def plot_from_database(room_numbers=None, sensor_numbers=None, time_from=1580920305102,\
                       time_to=time_now(), parameters=None, overlay=0, aggregate=0):

    # choose rooms to plot from
    if(room_numbers == None and sensor_numbers == None):
        room_numbers, room_names = scrp.choose_by_number(smart_building.room_info)

        if aggregate == 0:
            # choose from the sensors in those rooms
            sensors_in_chosen_rooms = smart_building.sensor_location_info.loc[ \
                              smart_building.sensor_location_info['roomname'].isin(room_names)]
            sensor_numbers, sensor_names = scrp.choose_by_number(sensors_in_chosen_rooms)
        elif aggregate == 1:
            # get the sensors in those rooms
            sensors_in_chosen_rooms = smart_building.sensor_location_info.loc[ \
                              smart_building.sensor_location_info['roomname'].isin(room_names)]
            sensor_numbers, senor_names = scrp.get_values_and_indexes(sensors_in_chosen_rooms)

    elif(room_numbers == None and sensor_numbers and aggregate == 0):
        if isinstance(sensor_numbers, int):
            sensor_numbers = [sensor_numbers]

        # get corresponding sensor names
        _, sensor_names = scrp.get_values_and_indexes( \
                                           smart_building.sensor_location_info.loc[sensor_numbers])
        
        # get the names of the rooms containing these sensors as a list with no duplicates
        _, room_names = scrp.get_values_and_indexes( \
                           smart_building.sensor_location_info.loc[sensor_numbers], 'roomname')

        # remove duplicates
        room_names = list(set(room_names))

        # get dataframe only containing those rooms        
        rooms_containing_chosen_sensors = \
            smart_building.room_info.loc[ \
                          smart_building.room_info['name'].isin(room_names)]
        
        # finally, get the corresponding room numbers
        room_numbers, _ = scrp.get_values_and_indexes(rooms_containing_chosen_sensors)

    elif(sensor_numbers == None and room_numbers):
      
        if isinstance(room_numbers, int):
            room_numbers = [room_numbers]

        # get room names
        room_names = list(smart_building.room_info['name'].loc[room_numbers])

        if aggregate == 0:
            # choose from the sensors in those rooms
            sensors_in_chosen_rooms = smart_building.sensor_location_info.loc[ \
                              smart_building.sensor_location_info['roomname'].isin(room_names)]
            sensor_numbers, sensor_names = scrp.choose_by_number(sensors_in_chosen_rooms)

        # if isinstance(room_numbers, int):    
        #     room_names = smart_building.sensor_location_info['name'].loc[room_numbers]           
        # else:
        #     room_names = list(smart_building.sensor_location_info['name'].loc[room_numbers])

            
            all_sensor_numbers, all_sensor_names = scrp.get_values_and_indexes(sensors_in_chosen_rooms)

        elif aggregate == 0:
            # choose from the sensors in those rooms
            sensors_in_chosen_rooms = smart_building.sensor_location_info.loc[ \
                              smart_building.sensor_location_info['roomname'].isin(room_names)]
            sensor_numbers, sensor_names = scrp.choose_by_number(sensors_in_chosen_rooms)

    #Choose the time range. E.g. 1st to 2nd March: [1583020800000, 1583107200000]
    if time == None:
        time_from, time_to = choose_time()

    if parameters == None and aggregate == 0:
        # the labels to look for in the dataframe.
        parameters = ['occupancy', 'voc', 'co2', 'temperature', \
                       'pressure', 'humidity', 'lux', 'noise']
    if aggregate ==1:

        parameters = 'occupancy'

        if isinstance(room_numbers, int):
            room_numbers = [room_numbers]

        sensors_in_chosen_rooms = smart_building.sensor_location_info.loc[ \
          smart_building.sensor_location_info['roomname'].isin(room_names)]
            
        # THIS IS TEMPORARY
        all_sensor_numbers, all_sensor_names = scrp.get_values_and_indexes(sensors_in_chosen_rooms)
        
        overlay = 1
        for room_number, room_name in zip(room_numbers, room_names):
            
            if room_number == room_numbers[-1]:
                overlay = 2
            print('Overlay: {}'.format(overlay))            
            print('Aggregating occupancy data for room {}: {}...'.format(room_number, room_name))

            sensors_in_chosen_rooms = smart_building.sensor_location_info.loc[ \
                  smart_building.sensor_location_info['roomname'].isin([room_name])]
    
            sensor_numbers, sensor_names = scrp.get_values_and_indexes(sensors_in_chosen_rooms)

            try:
                data_to_plot = retrieve_data(sensor_numbers, time_from, time_to, parameters)
                aggregated_data = aggregate_data(data_to_plot)        
                plot_from_dataframe(aggregated_data, int(room_number), overlay)
            except Exception as e:
                print("Error aggregating data for room number {}: {}.".format(room_number, e) )   
           
            overlay = 0
            
        return()

    if overlay==1:
         data_to_plot = retrieve_data(sensor_numbers, time_from, time_to, parameters=parameters)
         sorted_data = data_to_plot.sort_values(by=['sensor_number', 'timestampms'])
         plot_from_dataframe(sorted_data)




    for sensor_number in all_sensor_numbers:
            try:
                if aggregate == 1:
                    data_to_plot = retrieve_data(sensor_number, time_from, time_to, parameters='occupancy')
                else:
                    # retrieve the data
                    data_to_plot = retrieve_data(sensor_number, time_from, time_to, parameters)
    
                plot_from_dataframe(data_to_plot)
            except Exception as e:
                print("Error with sensor number {}: {}.".format(sensor_number, e) )   


#%% Program starts here

# Declare scraper instance
smart_building = scrp.Scraper()

# Connect to the database (creates a Connection object)
conn = sqlite3.connect("../database/database.db")

# Create a cursor to operate on the database
c = conn.cursor()

# Create class instance to get info so scraper does not have to be called
database = Database()

# plot_from_database(sensor_numbers=6, time_from=1583020800000, \
                   # time_to = 1583107200000, parameters='occupancy')

# plot_from_database(parameters='occupancy')

    
plot_from_database(overlay=1, time_from=1583280000000, \
                   time_to = 1583366400000, parameters=['occupancy', 'noise'])

# plot_from_database()

# data = retrieve_data(5, ['occupancy','voc','co2'])

# plot_from_dataframe(data)



# # this is the time of the earliest sensor reading in the database
# earliest_time = 1580920300000

# plot_from_data
# # run programbase()

#close the connection
conn.close()