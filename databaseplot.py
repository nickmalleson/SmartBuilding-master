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


from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
# warnings.warn(msg, FutureWarning)




class Database():
    '''Obtains login details and stores data associated with the account in co-
    stant variables.
    '''

    def __init__(self):
            self.sensor_location_info = self.get_table_info('sensors', 'sensor_number')
            print("Sensor locations retrieved successfully.")
            self.room_info = self.get_table_info('rooms', 'room_number')
            print("Room information retrieved successfully.")
            self.param_list = ['occupancy', 'voc', 'co2', 'temperature', 'pressure', \
                               'humidity', 'lux', 'noise']

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


    data_to_plot = pd.read_sql('SELECT time, timestampms, timestamputc, sensor_name, sensor_number, '\
                               'sensorlocation, {} '\
                               'FROM sensor_readings '\
                               '{}'\
                               'ORDER BY timestamputc;' .format(param_string, value_string), \
                             conn, params=sql_params  )
    
    ##TODO: add room_number and room_name to data here to simplify later code


    if data_to_plot.empty:
        print('No data for this time range for sensor number {}.'.format(sensor_numbers))

    return(data_to_plot)


def plot_from_dataframe(data_to_plot=None, aggregate=0):
    ''' Plot sensor data retrieved from database with retrieve_data(). 
    Plots all types of data from one sensor number. No upper limit on how many 
    datapoints.
    
    data_to_plot = dataframe from retrieve_data()
    sensor_number = int which corresponds to index in scraper.sensor_location_info.
    '''
    
    # if len(data_to_plot.sensor_number.unique()) != 1:
        # aggregated = 1
        # if room_number:
            # print('Plotting aggregated data for room_number {}: {}.'\
                  # .format(room_number, smart_building.room_info['name'].loc[room_number]))
            # print('Error: "plot_from_dataframe" function can only take one sensor at a time.')
    # else:
        # aggregated = 0
        # sensor_number = data_to_plot.sensor_number.unique()[0]
    
    # get parameters from columns headings 
    column_headings = list(data_to_plot.columns)
    
    # all paramters to look for in the dataframe.
    all_param_labels = ['occupancy', 'voc', 'co2', 'temperature', \
                   'pressure', 'humidity', 'lux', 'noise']

    # all labels     
    all_plot_labels = ['Occupancy\n(n)', 'VOC\n(ppm?)', 'CO2\n(ppm?)',
                  'Temperature\n(°C)', 'Pressure\n(mBar)',
                  'Humidity\n(RH)', 'Light Intensity\n(lux)',
                  'Noise Levels\n(dB)']

    # list for the ones to plot on the graph    
    paramlabels = []
    plotlabels= []
    
    # find which parameters are included in dataframe and make lists
    for parameter in column_headings:
        if parameter in all_param_labels:
            paramlabels.append(all_param_labels[all_param_labels.index(parameter)])
            plotlabels.append(all_plot_labels[all_param_labels.index(parameter)])


    # Convert times to datetime format
    data_to_plot['timestamputc'] =\
        pd.to_datetime(data_to_plot['timestamputc'])
    # set as index
    data_to_plot = data_to_plot.set_index('timestamputc')


    # get sensor_numbers and sensor names from dataframe    
    sensor_numbers = data_to_plot['sensor_number'].unique().tolist()
    ##TODO: list(set()) does not preserve order. Use below function instead
    sensor_names = data_to_plot['sensor_name'].unique().tolist()

    # make plot title
    if aggregate == 0:
        axtitle = str('Sensor readings')
            # str('Sensor readings from sensor number {}: {}.'
                      # .format(sensor_number,
                          # smart_building.sensor_location_info['name'].loc[sensor_number]))
        legend_series = sensor_names
    elif aggregate == 1:
        
        ##TODO: this is used in plot_from_database so could be made into a function
        # Would also be better if room name and number were contained in data_to_plot:
        # need to change dataframe for this

        # find which rooms sensors are in from 'Database' class
        honestlywhythefuckwontitstopatbreakpoints = 1
        room_names = data_to_plot['room_name'].unique().tolist()
        ##TODO: may need this when not plotting overlay =1 aggregate = 1        
            # database.sensor_location_info['room_name']\
                              # .loc[sensor_numbers]
        room_numbers = list(database.room_info.loc[ \
                        database.room_info['room_name'].isin(room_names)].index)

        
        axtitle = str('Aggregated sensor readings')
        legend_series = []
        # sensor_names_str = []
        for room_number, room_name in zip(room_numbers, room_names):       
            # sensor_names_str = str(', '.join(sensor_names))
            legend_str = str('Room number {}: {}' .format(room_number, room_name))
            legend_series.append(legend_str)
        # legend_series = room_names

        # str('Aggregated sensor readings for room {}: {}.' 
                      # .format(room_number, 
                          # smart_building.room_info['name'].loc[room_number]))


    #%% THIS WORKS AND ARE PROBABLY FOR BEST ONES

    fontsizeL = 18
    fontszieS = 16
    
    pause = 1

    fig, axes = plt.subplots(len(paramlabels),  figsize=(15, 15), sharex=True)

    if len(paramlabels)== 1:
        axes = [axes]
        
    for j in range(0,len(paramlabels)):
        for i, sensor_number in enumerate(sensor_numbers, start=0):
            
            current_data = data_to_plot[paramlabels[j]].loc[\
                            data_to_plot['sensor_number']==sensor_number]
                
                
            axes[j].plot(current_data, label = legend_series[i],
                                                marker='.', alpha=0.5,
                                                linewidth=1.5,
                                                markersize=6)
            axes[j].set_ylabel(plotlabels[j], rotation='horizontal',
                       ha='right', va='baseline', fontsize=fontsizeL, wrap=True)
            
            

    handles, labels = axes[-1].get_legend_handles_labels()

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

    leg = axes[0].legend(handles, labels, frameon=False, fontsize=fontsizeL, markerscale = 3,\
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


    figtime = str(data_to_plot.index.min().floor('Min').replace(tzinfo=None))
    if aggregate == 1:
        numstr = str('_'.join(str(x) for x in room_numbers))
        fig_name = str(figtime+'_rooms_'+numstr+'_AG')
    else:
        numstr = str('_'.join(str(x) for x in sensor_numbers))
        fig_name = str(figtime+'_sensors_'+numstr)
    
    if len(sensor_numbers) > 1:
        fig_name = str(fig_name + '_OL')

    fig_name = fig_name.replace(" ", "_")
    fig_name = fig_name.replace(":", "-")

    full_fig_name =  str('../Plots/{}.png'.format(fig_name))
    # full_fig_name =  'short'
   
    
    fig.savefig('../Plots/aaaa.png', dpi=500)

    fig.savefig(full_fig_name, dpi=500)

    plt.show()


def aggregate_data(data_to_aggregate):

    # get sensor_numbers and sensor names from dataframe    
    sensor_numbers = list(set(data_to_aggregate['sensor_number']))
    sensor_names = list(set(data_to_aggregate['sensor_name']))    
    sensor_names_str = str(', '.join(sensor_names))
    sensor_numbers_str = str(', '.join(str(x) for x in sensor_numbers))

    ##TODO: this is used in plot_from_database so could be made into a function
    # Would also be better if room name and number were contained in data_to_plot:
    # need to change dataframe for this

    # find which rooms are sensors are in from 'Database' class
    room_name = list(set(database.sensor_location_info['room_name']\
                          .loc[sensor_numbers]))[0]
    room_number = list(set(database.room_info.loc[ \
             database.room_info['room_name']==room_name].index))[0]

    # round times in data_to_aggregate to the nearest minute
    data_to_aggregate['timestamputc'] = \
        pd.to_datetime(data_to_aggregate['timestampms'], unit='ms')    
    data_to_aggregate['timestamputc'] = \
        data_to_aggregate['timestamputc'].dt.floor('Min')        
    data_to_aggregate['timestampms'] = \
        data_to_aggregate[['timestamputc']].apply( \
        lambda x: x[0].timestamp(), axis=1).astype('int64')*1000

    # Aggregate to get mean reading per sensor per minute
    ##TODO:  remove ['occupancy'] to get mean per minute per sensor for each parameter
    aggregated_data = data_to_aggregate.groupby( \
             ['timestampms', 'sensor_number'], as_index=False)['occupancy'].mean()     
    # Get sum of occupcany
    aggregated_data = aggregated_data.groupby(['timestampms']).sum()
    
    # set the index to timestamp
    aggregated_data['timestampms'] = aggregated_data.index
    
    # ADD 1 NANOSECOND TO PRESERVE TIME FORMAT. ESSENTIAL TO RUN.
    aggregated_data['timestamputc'] = aggregated_data['timestampms'] \
        .apply(lambda t: dt.datetime.utcfromtimestamp(int(t/1000)).isoformat()+'.000001+00:00')
    # aggregated_data['timestamputc'] = aggregated_data['timestamputc'].apply(parse)
    
    fuckingstopheretooplase = 1
    
    aggregated_data['room_name'] = room_name
    aggregated_data['room_number'] = room_number
    aggregated_data['sensor_name'] = sensor_names_str
    aggregated_data['sensor_number'] = sensor_numbers_str


    stop = 1
    
    return(aggregated_data)


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
            ##TODO: this may already exist in code above
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


    #%% AGGREGATE = 0 OVERLAY = 0
    if aggregate == 0 and overlay == 0:
        for sensor_number in sensor_numbers:
                try:
                    # retrieve the data
                    data_to_plot = retrieve_data(sensor_number, time_from, time_to, parameters)        
                    if not data_to_plot.empty:
                        print('Plotting data from sensor {}: {}.'\
                              .format(sensor_number, \
                              database.sensor_location_info['sensor_name'].\
                              loc[sensor_number]))
                        plot_from_dataframe(data_to_plot)
                    else:
                        # print('No data for sensor {}: {}.'\
                          # .format(sensor_number, \
                          # database.sensor_location_info['sensor_name'].\
                              # loc[sensor_number]))
                        continue
                except Exception as e:
                    print("Error with sensor number {}: {}.".format(sensor_number, e))
        return()
                    
    #%% AGGREGATE = 1 OVERLAY = 0                    
    elif aggregate ==1 and overlay ==0:

        parameters = 'occupancy'

        if isinstance(room_numbers, int):
            room_numbers = [room_numbers]

        sensors_in_chosen_rooms = smart_building.sensor_location_info.loc[ \
          smart_building.sensor_location_info['roomname'].isin(room_names)]
        
        for room_number, room_name in zip(room_numbers, room_names):
            
            # if room_number == room_numbers[-1]:
                # overlay = 2
            # print('Overlay: {}'.format(overlay))            
            print('Aggregating occupancy data for room {}: {}...'.format(room_number, room_name))

            sensors_in_chosen_rooms = smart_building.sensor_location_info.loc[ \
                  smart_building.sensor_location_info['roomname'].isin([room_name])]
    
            sensor_numbers, sensor_names = scrp.get_values_and_indexes(sensors_in_chosen_rooms)

            try:
                data_to_plot = retrieve_data(sensor_numbers, time_from, time_to, parameters)
                aggregated_data = aggregate_data(data_to_plot)        
                plot_from_dataframe(aggregated_data, aggregate=1)
            except Exception as e:
                print("Error aggregating data for room number {}: {}.".format(room_number, e) )   

            # overlay = 0

        return()

    #%% AGGREGATE = 0 OVERLAY = 1                    
    elif aggregate == 0 and overlay ==1:
         data_to_plot = retrieve_data(sensor_numbers, time_from, time_to, parameters=parameters)
         sorted_data = data_to_plot.sort_values(by=['sensor_number', 'timestampms'])
         plot_from_dataframe(sorted_data)
         return()

    #%% AGGREGATE = 1 OVERLAY = 1                      
    elif aggregate == 1 and overlay==1:

        ##TODO: aggregate currently only runs with occupancy
        parameters = 'occupancy'

        if isinstance(room_numbers, int):
            room_numbers = [room_numbers]

        sensors_in_chosen_rooms = smart_building.sensor_location_info.loc[ \
          smart_building.sensor_location_info['roomname'].isin(room_names)]
        
        
        for room_number, room_name in zip(room_numbers, room_names):
            
            # if room_number == room_numbers[-1]:
                # overlay = 2
            # print('Overlay: {}'.format(overlay))            
            print('Aggregating occupancy data for room {}: {}...'.format(room_number, room_name))

            sensors_in_chosen_rooms = smart_building.sensor_location_info.loc[ \
                  smart_building.sensor_location_info['roomname'].isin([room_name])]
    
            sensor_numbers, sensor_names = scrp.get_values_and_indexes(sensors_in_chosen_rooms)
            
            
            data_to_plot = retrieve_data(sensor_numbers, time_from, time_to, parameters)
            if data_to_plot.empty:
                print('No data or something for room {}: {}...'.format(room_number, room_name))

                continue
            else:
                
                aggregated_data = aggregate_data(data_to_plot)
                # aggregated_data = aggregated_data.rename_axis(None)

                # https://towardsdatascience.com/why-and-how-to-use-merge-with-pandas-in-python-548600f7e738
                ##TODO: THIS METHOD OF MERGING MAY REPEAT VALUES AND MAY NOT WORK IF NOT AGGREGATED_DATA FOR FIRST ROOM
                if room_number == room_numbers[0]:
                    aggregated_dfs = aggregated_data
                else:    
                    # aggregated_data = aggregated_data.rename_axis(None)
                    # aggregated_data.index = aggregated_data.reindex(index=range(0,len(aggregated_data)))
                    aggregated_dfs = pd.concat([aggregated_dfs, aggregated_data], axis=0)
                    # pd.merge(aggregated_dfs, aggregated_data, how='right')


        whythefuckwhontyoufuckingstop =1 
                            

        fuckingstopherenow = 1
        try:
            aggregated_dfs = aggregated_dfs.rename_axis(None)
            sorted_data = aggregated_dfs.sort_values(by=['room_number', 'timestampms'])
            plot_from_dataframe(sorted_data, aggregate=1)
        except Exception as e:
            print("Error aggregating data for room number {}: {}.".format(room_number, e) )   

            # overlay = 0

        return()
       
        
       


#%% Program starts here

# Declare scraper instance
smart_building = scrp.Scraper()

# Connect to the database (creates a Connection object)
conn = sqlite3.connect("../database/database.db")

# Create a cursor to operate on the database
c = conn.cursor()

# Create class instance to get info so scraper does not have to be called
database = Database()

# Try plotting 24 hours with different combinations of overlay and aggregate
plot_from_database(room_numbers=[1,2,3], overlay=1, aggregate=1, time_from=1583280000000, \
                    time_to = 1583366400000)

plot_from_database(room_numbers=[1,2,3], overlay=1, aggregate=0, time_from=1583280000000, \
                    time_to = 1583366400000)

plot_from_database(room_numbers=[1,2,3], overlay=0, aggregate=1, time_from=1583280000000, \
                    time_to = 1583366400000)
    
plot_from_database(room_numbers=[1,2,3], overlay=0, aggregate=0, time_from=1583280000000, \
                    time_to = 1583366400000)
    
# # this is the time of the earliest sensor reading in the database
# earliest_time = 1580920300000

# plot_from_data
# # run programbase()

#close the connection
conn.close()