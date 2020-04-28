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
from scraper import Scraper

# To convert time stamps for plotting x axes
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
# warnings.warn(msg, FutureWarning)


class Database():
    '''Obtains login details and stores data associated with the account in co-
    stant variables.
    '''

    def __init__(self):
            self.sensor_location_info = \
                self.get_table_info('sensors', 'sensor_number')
            self.sensor_numbers = self.sensor_location_info.index.tolist()
            self.sensor_names = \
                self.sensor_location_info['sensor_name'].tolist()
            print("Sensor locations retrieved successfully.")

            self.room_info = self.get_table_info('rooms', 'room_number')
            self.room_numbers = self.room_info.index.tolist()
            self.room_names = self.room_info['room_name'].tolist()
            print("Room information retrieved successfully.")
            
            self.param_list = ['occupancy', 'voc', 'co2', 'temperature', \
                               'pressure', 'humidity', 'lux', 'noise']


            self.plot_labels = ['Occupancy\n(n)', 'VOC\n(ppm)', 'CO2\n(ppm)',
                                    'Temperature\n(°C)', 'Pressure\n(mBar)',
                                    'Humidity\n(RH)', 'Light Intensity\n(lux)',
                                    'Noise Levels\n(dB)']
            
            self.plot_labels_aggregated = ['Occupancy\n(n, sum)', 'VOC\n(ppm, mean)', 'CO2\n(ppm, mean)',
                                            'Temperature\n(°C, mean)', 'Pressure\n(mBar, mean)',
                                            'Humidity\n(RH, mean)', 'Light Intensity\n(lux, mean)',
                                            'Noise Levels\n(dB, mean)']

    def get_table_info(self,table, index_col):
        dataframe = pd.read_sql('select * from {};'.format(table), conn)
        dataframe = dataframe.set_index(index_col)
        return(dataframe)


def choose_time():
    ''' Take user input to choose a time in ms time epoch. 
    Times are equivalent to those at https://currentmillis.com/ '''

    # time before the earliest sensor reading in ms format
    earliest_time_ms = 1580920305102
    # same time in utc format (/1000 as utcfromtimestamp takes input in s)
    earliest_time_utc = dt.datetime.utcfromtimestamp(int(earliest_time_ms/1000)).isoformat()

    # get time now
    time_now_ms = Scraper._time_now()
    time_now_utc = dt.datetime.utcfromtimestamp(int(time_now_ms/1000)).isoformat() 

    chosen_times = input('Choose start and end time to plot in ms epochs in format '\
                         '"[start, end]". or press enter full time range. For '\
                         'example for 1st to 2nd March, enter: [1583020800000, 1583107200000].'\
                         '\nEarliest:\n    ms:  {}\n    UTC: {}'\
                         '\nLatest:\n    ms:  {}\n    UTC: {}\n>>' 
                         .format(earliest_time_ms, earliest_time_utc,
                                 time_now_ms, time_now_utc))

    # by default, choose from earilest time to now
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
    ''' Builds string of parameters for use in pd.read_sql. '''

    param_string = parameters[0]    
    for i in range(1,len(parameters)):
        param_string = param_string + ', ' + parameters[i] 

    return(param_string)


def build_values_string(values):
    ''' Builds string of sensor numbers for use in pd.read_sql. '''

    values_string = 'WHERE timestampms BETWEEN ? AND ? AND sensor_number = ? '

    if isinstance(values, int):
       return(values_string)
    else:
        for i in range(1,len(values)):
            values_string = values_string + 'OR timestampms BETWEEN ? AND ? AND sensor_number = ? ' 

        return(values_string)


def retrieve_data(sensor_numbers=None, time_from=None, time_to=None, parameters=None):
    ''' Retrieve data from the database based on sensor number and timeframe using pd.read_sql.
    https://stackoverflow.com/questions/24408557/pandas-read-sql-with-parameters/24418294 

    Parameters
    ----------
    sensor_numbers : int or list of ints, optional
        Default will use all sensor numbers
    time_from : time from in ms format, optional
        Default will use earliest sensor reading
    time_to : time to in ms format, optional
        Default will use current time
    parameters : str or list of str, optional
        Default will use all parameters

    Returns
    -------
    Dataframe of data to plot.

    '''

    # Use defaults for unset parameters
    sensor_numbers, _, _, _, time_from, time_to, parameters, _, _, _ = \
        set_defaults(sensor_numbers=sensor_numbers, time_from=time_from, 
                     time_to=time_to, parameters=parameters)

    # build string for paramteres to input into pd.read_sql
    if isinstance(parameters, list):
        param_string = build_param_string(parameters)
    elif isinstance(parameters, str): 
        param_string = parameters
    else: print('Format of input variable "parameters" not recognised.')
    
    # string for parameter input to pd.read_sql
    if isinstance(sensor_numbers, int): 
        sql_params = [time_from, time_to, sensor_numbers]
    elif isinstance(sensor_numbers, list):
        sql_params = []
        for i in sensor_numbers:
            sql_params = sql_params + [time_from, time_to, i]

    # build string for input 
    value_string = build_values_string(sensor_numbers)

    # retrieve from database
    data_to_plot = pd.read_sql('SELECT time, timestampms, timestamputc, '\
                               'sensor_name, sensor_number, sensorlocation, {} '\
                               'FROM sensor_readings '\
                               '{}'\
                               'ORDER BY timestamputc;' 
                               .format(param_string, value_string), \
                               conn, params=sql_params)

    # error message if no data returned
    if data_to_plot.empty:
        _, _, room_number, room_name = get_names_and_numbers(sensors=sensor_numbers)
        if isinstance(sensor_numbers, list):
            sensor_numbers_str = str(', '.join(str(x) for x in sensor_numbers))
        else:
            sensor_numbers_str = sensor_numbers
        print('No data for the following sensor(s) from room {}, {}: {}.'\
              .format(room_number[0], room_name[0], sensor_numbers_str))
    return(data_to_plot)


def plot_from_dataframe(data_to_plot=None, aggregate=0):
    ''' Plot sensor data retrieved from database with retrieve_data(). 
    Plots all types of data from one sensor number. No upper limit on how many 
    datapoints.
    
    data_to_plot = dataframe from retrieve_data()
    sensor_number = int which corresponds to index in scraper.sensor_location_info.
    '''

    ##TODO: first thing to do should be to sort data by sensor_number/room_number to make sure legends are accurate
    
    # get parameters from columns headings 
    column_headings = list(data_to_plot.columns)
    
    # get labels and sort data
    data_to_plot.index.name = None
    if aggregate == 0:     
        all_plot_labels = database.plot_labels
        data_to_plot = data_to_plot.sort_values(by=['sensor_number', 'timestampms'])
    else:
        all_plot_labels = database.plot_labels_aggregated
        data_to_plot = data_to_plot.sort_values(by=['room_number', 'timestampms'])

    # list for the ones to plot on the graph    
    paramlabels = []
    plotlabels = []
    
    # find which parameters are included in dataframe and make lists
    for parameter in column_headings:
        if parameter in database.param_list:
            paramlabels.append(database.param_list[database.param_list.index(parameter)])
            plotlabels.append(all_plot_labels[database.param_list.index(parameter)])


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
            legend_str = str('Room number {}:\n        {}' .format(room_number, room_name))
            legend_series.append(legend_str)
        # legend_series = room_names

        # str('Aggregated sensor readings for room {}: {}.' 
                      # .format(room_number, 
                          # smart_building.room_info['name'].loc[room_number]))


    #%% THIS WORKS AND ARE PROBABLY FOR BEST ONES

    fontsizeL = 18
    fontszieS = 16
    
    fig, axes = plt.subplots(len(paramlabels),  figsize=(20, 15), sharex=True)

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
    ##TODO: UserWarning: Creating legend with loc="best" can be slow with large amounts of data.
    # fig.savefig(full_fig_name, dpi=500)   
    leg = axes[0].legend(handles, labels, frameon=False, fontsize=fontsizeL, markerscale = 3,\
                     bbox_to_anchor=(1, 1))
        # , loc='upper left')
        
                     # , borderaxespad=0., loc='upper left', bbox_to_anchor=(1, plt.y1), loc=2, borderaxespad=0.)
                    #was 9.5

    fig.suptitle(axtitle, y=.95, fontsize=fontsizeL*2)

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

    full_fig_name =  str('./Plots/{}.png'.format(fig_name))
    # full_fig_name =  'short'
   
    
    # fig.savefig('../Plots/aaaa.png', dpi=500)

    fig.savefig(full_fig_name, dpi=500)

    plt.show()


def aggregate_data(data_to_aggregate, parameters):
    ''' Aggregates the data from all sensors in the dataframe providing they 
    are from the same room. Can aggregate data from any number of sensors in a room,
    but not sensors in different rooms. 
    Process:
    - Sorts dataframes and creates strings for the fields in output dataframe
    - Ensures that there is only one reading per minute for each sensor
        (takes average for each minute).
    - Calculates sum of occupancy and mean of every other paramter
    - Outputs the data a new dataframe.
    
    Parameters
    ----------
    data_to_aggregate : panda dataframe
        Sensors must be in the same room.
    parameters : list of str
        List of parameter strs

    Returns
    -------
    New dataframe of aggregated data. '''

    # sort dataframe by sensor number then time
    data_to_aggregate = data_to_aggregate.sort_values(by=['sensor_number', 'timestampms'])
    
    # get lists of sensor_numbers and sensor names from dataframe    
    sensor_numbers = data_to_aggregate['sensor_number'].unique().tolist()
    sensor_names = data_to_aggregate['sensor_name'].unique().tolist()

    # convert list to str for use in field in output dataframe
    sensor_numbers_str = str(', '.join(str(x) for x in sensor_numbers))
    sensor_names_str = str(', '.join(sensor_names))

    # find the room name and number from the sensor numbers
    _, _, room_number, room_name = get_names_and_numbers(sensors=sensor_numbers)

    # round times in data_to_aggregate to the nearest minute
    data_to_aggregate['timestamputc'] = \
        pd.to_datetime(data_to_aggregate['timestampms'], unit='ms')    
    data_to_aggregate['timestamputc'] = \
        data_to_aggregate['timestamputc'].dt.floor('Min')        
    data_to_aggregate['timestampms'] = \
        data_to_aggregate[['timestamputc']].apply( \
        lambda x: x[0].timestamp(), axis=1).astype('int64')*1000

    # aggregate to get mean reading per sensor per minute
    mean_per_minute_per_sensor = data_to_aggregate.groupby( \
             ['timestampms', 'sensor_number'], as_index=False)[parameters].mean()

    # generate mean of mean (all parameters)
    mean_per_minute_total = mean_per_minute_per_sensor.groupby(['timestampms']).mean()

    # Get sum of occupcany
    occupancy_sum = mean_per_minute_per_sensor.groupby(['timestampms']).sum()

    # get data for output and replace mean occupancy with sum
    aggregated_data = mean_per_minute_total
    aggregated_data['occupancy'] = occupancy_sum['occupancy']

    # set the index to timestampms
    aggregated_data['timestampms'] = aggregated_data.index
    
    # add 1 ns to preserve time format. (could be better way to do this).
    aggregated_data['timestamputc'] = aggregated_data['timestampms'] \
        .apply(lambda t: dt.datetime.utcfromtimestamp(int(t/1000)).isoformat()+'.000001+00:00')

    #  set columns for the ouput dataframe from strings made earlier.      
    aggregated_data['room_name'] = room_name[0]
    aggregated_data['room_number'] = room_number[0]
    aggregated_data['sensor_name'] = sensor_names_str
    aggregated_data['sensor_number'] = sensor_numbers_str
 
    return(aggregated_data)


def set_defaults(sensor_numbers=None, sensor_names=None, room_numbers=None, room_names=None, 
                 time_from=None, time_to=None, parameters=None, overlay=None, aggregate=None, seperate=None):

    if sensor_numbers == None:
        sensor_numbers = database.sensor_numbers
    if sensor_names == None:
        sensor_names = database.sensor_names
    if room_numbers == None:
        room_numbers = database.room_numbers
    if room_names == None:
        room_names = database.room_names
    if time_from == None:
        time_from = 1580920305102
    if time_to == None:
        time_to=Scraper._time_now()
    if parameters == None:
        parameters = database.param_list        
    if overlay == None and len(sensor_numbers) > 1:
        overlay = 1
    elif overlay == None:
        overlay = 0    
    if aggregate == None:
        aggregate = 0
    if seperate == None:
        seperate = 1

    return(sensor_numbers, sensor_names, room_numbers, room_names, time_from, 
           time_to, parameters, overlay, aggregate, seperate)


def choose_from_command_line(input_choice, sensors=None, rooms=None, time_from=None, 
                             time_to=None, parameters=None, overlay=None, aggregate=None, seperate=None):
    '''
    Takes user input to generate plot from command line. Minimum requirement is entering 
    either 'sensors' or 'rooms' to choose from. All other parameters are provided as 
    they can be set in command line so that the user is only prompted to change unset parameters.

    Parameters
    ----------
    input_choice : STR
        Enter either 'sensors' or 'rooms'. Prompts will adjust accordingly.
    sensors : single/LIST of INT or STR, optional
        If ints: [1, 2, 3] 
        If str: ['0-Café-1', '0-Café-2', '0-Cafe-3']
        Can also read individual values not in lists. Default collects all available.
    rooms : single/LIST of INT or STR, optional
        If ints: [1, 2, 3] 
        If str: ['0-Café', '0-Exhibition-Area', '2-Open-Office']
        Can also read individual values not in lists. Default collects all available.
    time_from : INT, optional
        First time to plot in ms timestamp format. Default is first available.
    time_to : INT, optional
        Last time to plot in ms timestamp format. Default is most recent available.
    parameters : LIST of STR, optional
         Choice of parameters from Database.param_list. Default is all.
    overlay : INT, optional
        0 = seperate plots, 1 = overlay on same plot. Default = 1.
    aggregate : INT, optional
        0 = individual sensors, 1 = aggregate sensors in same room. The default = 0.
    seperate : INT, optional
        0 = 1 sensors from different rooms on same plot, 1 = sensors from different
        rooms are plotted seperately. Only relevant if overlay = 1 and aggregate = 0.

    Returns
    -------
    Parameter choices.

    '''

    #%% establish sensor and room numbers and names
    if sensors == None and rooms == None:
        if input_choice == 'rooms':
            room_numbers, room_names = Scraper._choose_by_number(database.room_info, 'room_name')
            sensor_numbers, sensor_names, room_numbers, room_names = get_names_and_numbers(rooms=room_numbers)  
        elif input_choice == 'sensors':
            sensor_numbers, sensor_names = Scraper._choose_by_number(database.sensor_location_info, 'sensor_name')
            sensor_numbers, sensor_names, room_numbers, room_names = get_names_and_numbers(sensors=sensor_numbers)  
        else:
            print("Unknown input for variable 1: input_choice. Enter 'rooms' or 'sensors', including quotes.")
            return
    elif sensors:
        sensor_numbers, sensor_names, room_numbers, room_names = get_names_and_numbers(sensors=sensors)  
    elif rooms:
        sensor_numbers, sensor_names, room_numbers, room_names = get_names_and_numbers(rooms=rooms)  

    
    #%% find which variables are still empty and query whether user wants to use defaults    
    input_list = [time_from, time_to, parameters, overlay, aggregate, seperate]
    input_str_list = ['time_from', 'time_to', 'parameters', 'overlay', 'aggregate', 'seperate']
    default_settings = ['first available', 'most recent', 'all', 'overlay', 'do not aggregate', 'rooms on different plots']
    empty_input_str = []
    default_str = []
    
    for input_var, input_str, default in zip(input_list, input_str_list, default_settings):
        if input_var == None:
            empty_input_str.append(input_str)
            default_str.append(default)

    empty_input_str = str(', '.join(empty_input_str))
    default_str = str(', '.join(default_str))
    
    use_default = input('No preference specified for: {}. \n'\
                        'Default: {}. Use default settings? \n[y/n]: '
                        .format(empty_input_str, default_str))
    
    #%% use defaults or provide further choice based on user input
    if (not use_default) or (use_default == 'y'):
        print("Using defaults.")
        sensor_numbers, sensor_names, room_numbers, room_names, time_from, time_to, parameters, overlay, aggregate, seperate = \
            set_defaults(sensor_numbers, sensor_names, room_numbers, room_names, time_from, time_to, parameters, overlay, aggregate, seperate)
    else:
        if (time_from == None) and (time_to == None):            
            time_from, time_to = choose_time()
        elif time_from == None and time_to:
            time_from = input('Input start time to plot in ms epochs in format: \n')
            time_from = eval(time_from)
        elif time_from and time_to == None:
            time_to = input('Input end time to plot in ms epochs in format: \n')
            time_to = eval(time_to)
        if parameters == None:
            _, parameters = Scraper._choose_by_number(database.param_list, 'parameter')
        if overlay == None and len(sensor_numbers) > 1:
            overlay = input('Overlay plots on same graph? \n[y/n]: ')
            if (not overlay) or (overlay == 'y'):
                overlay = 1
            elif overlay == 'n':
                overlay = 0
            else:
                print('Unknown input.')
        elif overlay == None:
            overlay = 0
        if aggregate == None and len(sensor_numbers) > len(room_numbers):
            aggregate = input('Aggregate sensors from same room? \n[y/n]: ')
            if (not aggregate) or (aggregate == 'y'):
                aggregate = 1
            elif aggregate == 'n':
                aggregate = 0
            else:
                print('Unknown input.')
        elif aggregate == None:
            aggregate = 0
        if seperate == None and aggregate == 0 and overlay == 1:
            seperate = input('Plot sensors from different rooms on seperate plots? \n[y/n]: ')
            if (not seperate) or (seperate == 'y'):
                seperate = 1
            elif seperate == 'n':
                seperate = 0
            else:
                print('Unknown input.')            

    return(sensor_numbers, sensor_names, room_numbers, room_names, time_from, 
                 time_to, parameters, overlay, aggregate, seperate)


def get_names_and_numbers(sensors=None, rooms=None):
    '''Input list of sensor numbers, returns list of names of rooms that contain sensors.'''

    if isinstance(sensors, int) or isinstance(sensors, str):
        sensors = [sensors]
    if isinstance(rooms, int) or isinstance(rooms, str):
        rooms = [rooms]

    if sensors:
        if isinstance(sensors[0], int): # if sensor numbers, define sensor names and numbers
            sensor_numbers = sensors
            sensor_names = database.sensor_location_info['sensor_name'].loc[sensors].tolist()
        elif isinstance(sensors[0], str): # if sensor names, define sensor names and numbers
            sensor_names = sensors
            sensor_numbers = database.sensor_location_info.loc[ \
                           database.sensor_location_info['sensor_name'].isin(sensor_names)].index.tolist()

        # get a list of which room each sensor is in with no duplicates and get room numbers from these
        room_names = list(set(database.sensor_location_info['room_name'].loc[sensor_numbers]))
        room_numbers = database.room_info.loc[ \
                          database.room_info['room_name'].isin(room_names)].index.tolist()
    elif rooms:
        if isinstance(rooms[0], int): # if room numbers, define room names and numbers
            room_numbers = rooms
            room_names = database.room_info['room_name'].loc[rooms].tolist()
        elif isinstance(rooms[0], str): # if sensor names, define sensor names and numbers
            room_names = rooms
            room_numbers = database.room_info.loc[ \
                          database.room_info['room_name'].isin(room_names)].index.tolist()

        sensor_numbers = database.sensor_location_info.loc[ \
                          database.sensor_location_info['room_name'].isin(room_names)].index.tolist()
        # get a list of which room each sensor is in with no duplicates and get room numbers from these
        sensor_names = set(list(database.sensor_location_info['sensor_name'].loc[sensor_numbers]))

    else:
        sensor_numbers=None
        sensor_names=None
        room_numbers=None
        room_names=None

    return(sensor_numbers, sensor_names, room_numbers, room_names)


def plot_from_database(choose_by_input=None, sensors=None, rooms=None, time_from=None, \
                       time_to=None, parameters=None, overlay=None, aggregate=None, seperate=None):
    
    # first section of code deals with establishing the parameters
    
    # retrieve room and sensor names and numbers from the list of ints or str input in sensors or rooms
    sensor_numbers, sensor_names, room_numbers, room_names = get_names_and_numbers(sensors, rooms)

    #check if user wants to choose from command line and collect info this way if they do
    if choose_by_input != None:
        sensor_numbers, sensor_names, room_numbers, room_names, time_from, time_to, parameters, overlay, aggregate, seperate = \
            choose_from_command_line(choose_by_input, sensors, rooms, time_from, time_to, \
                                     parameters, overlay, aggregate, seperate)
    else: # set the unset variables to default
        sensor_numbers, sensor_names, room_numbers, room_names, time_from, time_to, parameters, overlay, aggregate, seperate = \
            set_defaults(sensor_numbers, sensor_names, room_numbers, room_names, time_from, time_to, parameters, overlay, aggregate, seperate)


    #%% AGGREGATE = 0 OVERLAY = 0
    if aggregate == 0 and overlay == 0:
        for sensor_number, sensor_name in zip(sensor_numbers, sensor_names):
            data_to_plot = retrieve_data(sensor_number, time_from, time_to, parameters)        
            if not data_to_plot.empty:
                print('Plotting data from sensor {}: {}.'.format(sensor_number, sensor_name))
                plot_from_dataframe(data_to_plot)
            else:
                continue
        return


    #%% AGGREGATE = 0 OVERLAY = 1
    elif aggregate == 0 and overlay ==1:
        if seperate == 1:
            for room_number, room_name in zip(room_numbers, room_names):
                sensors_in_current_room = sensors_in_room(sensor_numbers, room_name)
                data_to_plot = retrieve_data(sensors_in_current_room, time_from, time_to, parameters)
                if not data_to_plot.empty: 
                    print('Plotting overlaid data from {} sensors from room {}: {}.'
                          .format(len(sensors_in_current_room), room_number, room_name))
                    plot_from_dataframe(data_to_plot)
                else:
                    return
        else:
             data_to_plot = retrieve_data(sensor_numbers, time_from, time_to, parameters)
             if not data_to_plot.empty:
                 print('Plotting overlaid data from {} sensors from {} room(s).'
                        .format(len(sensor_numbers), len(room_numbers)))
                 plot_from_dataframe(data_to_plot)
                 return
             else:
                 return


    #%% AGGREGATE = 1 OVERLAY = 0                    
    elif aggregate ==1 and overlay ==0:
        for room_number, room_name in zip(room_numbers, room_names):
            sensors_in_current_room = sensors_in_room(sensor_numbers, room_name)
            data_to_plot = retrieve_data(sensors_in_current_room, time_from, time_to, parameters)
            if not data_to_plot.empty: 
                print('Aggregating data for {} sensors in room {}: {}...' 
                      .format(len(sensors_in_current_room), room_number, room_name))
                aggregated_data = aggregate_data(data_to_plot, parameters) 
                print('Plotting aggregated data from {} sensors from room {}: {}.'
                      .format(len(sensors_in_current_room), room_number, room_name))
                plot_from_dataframe(aggregated_data, aggregate = 1)
            else:
                continue
        return


    #%% AGGREGATE = 1 OVERLAY = 1                      
    elif aggregate == 1 and overlay==1:
        aggregated_dfs = pd.DataFrame
        for room_number, room_name in zip(room_numbers, room_names):
            sensors_in_current_room = sensors_in_room(sensor_numbers, room_name)
            data_to_plot = retrieve_data(sensors_in_current_room, time_from, time_to, parameters)
            if not data_to_plot.empty:
                print('Aggregating data for {} sensors in room {}: {}...' 
                      .format(len(sensors_in_current_room), room_number, room_name))
                aggregated_data = aggregate_data(data_to_plot, parameters) 
                if aggregated_dfs.empty:
                    aggregated_dfs = aggregated_data.copy()
                else:
                    aggregated_dfs = pd.concat([aggregated_dfs, aggregated_data], axis=0)
            else:
                continue
        print('Plotting avaialable data from {} sensors from {} rooms, aggregated and overlaid.'
              .format(len(sensor_numbers), len(room_numbers)))
        plot_from_dataframe(aggregated_dfs, aggregate=1)
        return


def sensors_in_room(sensor_numbers, room_name):
    ''' Returns all sensors in a list which are in a specified room. List does
    not have to be complete list of sensors.'''
    
    sensors_in_current_room = []
    for sensor_number in sensor_numbers:
        if database.sensor_location_info['room_name'].loc[sensor_number] == room_name:
            sensors_in_current_room.append(sensor_number)
    return(sensors_in_current_room)



#%% Program starts here

# Connect to the database (creates a Connection object)
conn = sqlite3.connect("./database.db")

# Create a cursor to operate on the database
c = conn.cursor()

# Create class instance to get info so scraper does not have to be called
database = Database()

# plot_from_data
# # run programbase()

#close the connection
conn.close()