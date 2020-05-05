# -*- coding: utf-8 -*-
"""
databaseplot.py

This script is for plotting from the SQL database file named 'database.db'. 
This happens by running methods of the DatabasePlotter() class.

Created on Thu Mar 12 18:04:38 2020

@author: medtcri
"""
import datetime as dt
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from pandas.plotting import register_matplotlib_converters
import pandas as pd
from scraper import Scraper
import sqlite3
import sys
register_matplotlib_converters()


class DatabasePlotter():
    """Tool for plotting from the SQL database file named 'database.db'. 
    Obtains login details and stores data associated with the account as
    class attributes. Also includes the parameters for how the plot is 
    created.
    """

    def __init__(self):

        # connect to database
        self.conn, self.c = self.connect_to_database()
        
        # get sensor info
        self.sensor_location_info = \
            self.get_table_info('sensors', 'sensor_number')
        self.all_sensor_numbers = self.sensor_location_info.index.tolist()
        self.all_sensor_names = \
            self.sensor_location_info['sensor_name'].tolist()
        print("Sensor locations retrieved successfully.")

        # get room info
        self.room_info = self.get_table_info('rooms', 'room_number')
        self.all_room_numbers = self.room_info.index.tolist()
        self.all_room_names = self.room_info['room_name'].tolist()
        print("Room information retrieved successfully.")

        # lists of plot parameters and plot labels
        self.param_list = ['occupancy', 'voc', 'co2', 'temperature',
                           'pressure', 'humidity', 'lux', 'noise']

        self.plot_labels = ['Occupancy\n(n)', 'VOC\n(ppm)', 'CO2\n(ppm)',
                            'Temperature\n(°C)', 'Pressure\n(mBar)',
                            'Humidity\n(RH)', 'Light Intensity\n(lux)',
                            'Noise Levels\n(dB)']

        self.plot_labels_aggregated = ['Occupancy\n(n, sum)', 
                                       'VOC\n(ppm, mean)', 'CO2\n(ppm, mean)',
                                       'Temperature\n(°C, mean)', 
                                       'Pressure\n(mBar, mean)',
                                       'Humidity\n(RH, mean)', 
                                       'Light Intensity\n(lux, mean)',
                                       'Noise Levels\n(dB, mean)']

        # plotting parameters
        self.sensor_numbers = None
        self.sensor_names = None
        self.room_numbers = None
        self.room_names = None
        self.time_from = None
        self.time_to = None
        self.parameters = None
        self.overlay = None
        self.aggregate = None
        self.seperate = None

    def connect_to_database(self):
        # connect to database
        self.conn = sqlite3.connect("./database.db")

        # Create a cursor to operate on the database
        self.c = self.conn.cursor()
        return (self.conn, self.c)

    def get_table_info(self, table, index_col):
        dataframe = pd.read_sql('select * from {};'.format(table), self.conn)
        dataframe = dataframe.set_index(index_col)
        return (dataframe)

    @staticmethod
    def _choose_time():
        ''' Take user input to choose a time in ms time epoch. 
        Times are equivalent to those at https://currentmillis.com/ '''

        # time before the earliest sensor reading in ms format
        earliest_time_ms = 1580920305102

        # same time in utc format (/1000 as utcfromtimestamp takes input in s)
        earliest_time_utc = dt.datetime.utcfromtimestamp(
            int(earliest_time_ms / 1000)).isoformat()

        # get time now
        time_now_ms = Scraper._time_now()
        time_now_utc = dt.datetime.utcfromtimestamp(
            int(time_now_ms / 1000)).isoformat()

        chosen_times = input('Choose start and end time to plot in ms epochs '
                             'in format "[start, end]". or press enter full '
                             'time range. For example for 1st to 2nd March, '
                             'enter: [1583020800000, 1583107200000].'
                             '\nEarliest:\n    ms:  {}\n    UTC: {}'
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
            time_from_utc = dt.datetime.utcfromtimestamp(
                int(time_from_ms / 1000)).isoformat()
            time_to_utc = dt.datetime.utcfromtimestamp(
                int(time_to_ms / 1000)).isoformat()

            # print what the chosen time range.
        print('Chosen time range from {} to {}.'.format(
            time_from_utc, time_to_utc))
        return (time_from_ms, time_to_ms)

    @staticmethod
    def _build_param_string(parameters):
        ''' Builds string of parameters for use in pd.read_sql. '''

        param_string = parameters[0]
        for i in range(1, len(parameters)):
            param_string = param_string + ', ' + parameters[i]

        return (param_string)

    @staticmethod
    def _build_values_string(values):
        ''' Builds string of sensor numbers for use in pd.read_sql. '''

        values_string = ('WHERE timestampms BETWEEN ? AND ? AND \
                         sensor_number = ? ')

        if isinstance(values, int):
            return (values_string)
        else:
            for i in range(1, len(values)):
                values_string = values_string + \
                    'OR timestampms BETWEEN ? AND ? AND sensor_number = ? '

            return (values_string)

    def retrieve_data(self, sensor_numbers=None, time_from=None, time_to=None, 
                      parameters=None):
        ''' Retrieve data from the database based on sensor number and 
        timeframe using pd.read_sql.
        https://stackoverflow.com/questions/24408557/pandas-read-sql-with-
        parameters/24418294 

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

        # build string for paramteres to input into pd.read_sql
        if isinstance(parameters, list):
            param_string = DatabasePlotter._build_param_string(parameters)
        elif isinstance(parameters, str):
            param_string = parameters
        else:
            print('Format of input variable "parameters" not recognised.')

        # string for parameter input to pd.read_sql
        if isinstance(sensor_numbers, int):
            sql_params = [time_from, time_to, sensor_numbers]
        elif isinstance(sensor_numbers, list):
            sql_params = []
            for i in sensor_numbers:
                sql_params = sql_params + [time_from, time_to, i]

        # build string for input
        value_string = DatabasePlotter._build_values_string(sensor_numbers)

        # retrieve from database
        data_to_plot = pd.read_sql('SELECT time, timestampms, timestamputc, '
                                   'sensor_name, sensor_number, '
                                   'sensorlocation, {} '
                                   'FROM sensor_readings '
                                   '{}'
                                   'ORDER BY timestamputc;'
                                   .format(param_string, value_string),
                                   self.conn, params=sql_params)

        # error message if no data returned
        if data_to_plot.empty:
            sensor_numbers, sensor_names, room_numbers, room_names = \
                self.get_names_and_numbers(sensors=sensor_numbers)

            sensor_numbers_str = str(', '.join(str(x) 
                                               for x in sensor_numbers))
            
            room_names_str = str(', '.join(str(x) for x in room_names))

            print('No data from one of the following:\n    Room name(s): {}. '
                  '\n    Sensor number(s): {}.'.format(room_names_str, 
                                                       sensor_numbers_str))

        return (data_to_plot)

    def plot_setup(self, data_to_plot, aggregate=0):
        ''' Initialise dataframe and return variables required by 
        DatabasePlotter.plot_from_dataframe()'''

        # %% get plot title, axes labels, and legend labels, and organize 
        # dataframe for plotting

        # get parameters from columns headings
        column_headings = data_to_plot.columns.tolist()

        data_to_plot.index.name = None
        if aggregate == 0:

            # get sensor_numbers and sensor names from dataframe
            sensor_numbers = data_to_plot['sensor_number'].unique().tolist()

            # get the reset of the details
            sensor_numbers, sensor_names, room_numbers, room_names = \
                self.get_names_and_numbers(sensors=sensor_numbers)

            # set plot labels
            all_plot_labels = self.plot_labels

            # sort dataframe
            data_to_plot = data_to_plot.sort_values(
                by=['sensor_number', 'timestampms'])

            # generate plot title
            if len(room_numbers) == 1:
                total_sensors_in_room = len(self.sensors_in_room(
                    self.all_sensor_numbers, room_names[0]))
                plot_title = str('Data from {}/{} sensors in {}'
                                 .format(len(sensor_numbers), 
                                         total_sensors_in_room, 
                                         room_names[0]))
            else:
                total_num_sensors = 0
                for room_name in room_names:
                    total_num_sensors += len(self.sensors_in_room(
                        self.all_sensor_numbers, room_name))

                plot_title = str('Data from {}/{} sensors in {} rooms'
                                 .format(len(sensor_numbers), 
                                         total_num_sensors, 
                                         len(room_numbers)))

            # define legend keys
            legend_series = sensor_names

        elif aggregate == 1:

            # get room names
            room_names = \
                data_to_plot['room_name'].unique().tolist()

            # sensor numbers are converted to strings in aggregated dfs
            # so gets sensor_numbers AS STRINGS
            # this is used later for plotting so must be same length as when
            # it comes in
            sensor_numbers = \
                data_to_plot['sensor_number'].unique().tolist()

            # get sensor numbers as list of ints
            sensor_numbers_ints = []
            for sensor_string in sensor_numbers:
                for i in sensor_string.split(', '):
                    sensor_numbers_ints.append(i)
            sensor_numbers_ints = list(map(int, sensor_numbers_ints))

            # then get the the reset of the details from this
            sensor_numbers_ints, sensor_names, room_numbers, room_names = \
                self.get_names_and_numbers(sensors=sensor_numbers_ints)

            # set plot labels
            all_plot_labels = self.plot_labels_aggregated

            # sort dataframe
            data_to_plot = data_to_plot.sort_values(
                by=['room_number', 'timestampms'])

            # generate plot title and legend series
            if len(room_numbers) == 1:
                total_sensors_in_room = len(self.sensors_in_room(
                    self.all_sensor_numbers, room_names[0]))
                plot_title = str('Aggregated data from {}/{} sensors in {}'
                                 .format(len(sensor_numbers_ints), 
                                         total_sensors_in_room, 
                                         room_names[0]))
                legend_series = [str('Room number {}:\n        {}'
                                     .format(room_numbers[0], room_names[0]))]

            else:
                total_in_all_rooms = 0
                legend_series = []

                for room_number, room_name in zip(self.room_numbers,
                                                  self.room_names):
                    total_in_room = len(self.sensors_in_room(
                        self.all_sensor_numbers, room_name))
                    included_from_room = len(
                        self.sensors_in_room(sensor_numbers_ints, room_name))
                    total_in_all_rooms += total_in_room
                    legend_str = str(
                        'Room number {}:\n        {} (n={}/{})'
                        .format(room_number, room_name, included_from_room,
                                total_in_room))
                    legend_series.append(legend_str)

                plot_title = str('Aggregated data from {}/{} sensors in {} '
                                 'rooms'.format(len(sensor_numbers_ints), 
                                                total_in_all_rooms, 
                                                len(room_numbers)))

        # convert times to datetime format and set timestamputc as index 
        # (required to plot)
        data_to_plot['timestamputc'] = pd.to_datetime(
            data_to_plot['timestamputc'])
        data_to_plot = data_to_plot.set_index('timestamputc')

        # generate lists for the labels to plot on the graph
        param_labels = []
        plot_labels = []

        # find which parameters are included in dataframe and make lists
        for parameter in column_headings:
            if parameter in self.param_list:
                param_labels.append(
                    self.param_list[self.param_list.index(parameter)])
                plot_labels.append(
                    all_plot_labels[self.param_list.index(parameter)])

        # %% generate file name
        figtime = str(data_to_plot.index.min().floor(
            'Min').replace(tzinfo=None))
        if aggregate == 1:
            numstr = str('_'.join(str(x) for x in room_numbers))
            fig_name = str(figtime + '_rooms_' + numstr + '_AG')
        else:
            numstr = str('_'.join(str(x) for x in sensor_numbers))
            fig_name = str(figtime + '_sensors_' + numstr)

        if len(sensor_numbers) > 1:
            fig_name = str(fig_name + '_OL')

        fig_name = fig_name.replace(" ", "_")
        fig_name = fig_name.replace(":", "-")
        file_name = str('./Plots/{}.png'.format(fig_name))

        return (data_to_plot, sensor_numbers, sensor_names, room_numbers,
                room_names, param_labels, plot_labels, legend_series, 
                plot_title, file_name)

    def plot_from_dataframe(self, data_to_plot, aggregate=0):
        ''' Plot sensor data retrieved from database with 
        DatabasePlotter.retrieve_data(). Plots all types of data from one 
        sensor number. No upper limit on how many datapoints. This is called 
        for each plot generated.

        data_to_plot = dataframe from DatabasePlotter.retrieve_data()
        sensor_number = int which corresponds to index in 
            'scraper.sensor_location_info'.
        '''

        # check there is data to plot and warn if none.
        if data_to_plot.empty:
            print('No data to plot.')
            return

        # retrieve variables required to plot and organise dataframe in 
        # preparation
        data_to_plot, sensor_numbers, sensor_names, room_numbers, room_names,\
        param_labels, plot_labels, legend_series, plot_title, file_name = \
            self.plot_setup(data_to_plot, aggregate)

        # size of small and large text
        fontsizeL = 18
        fontsizeS = 16

        # initialise axes
        fig, axes = plt.subplots(
            len(param_labels), figsize=(20, 15), sharex=True)

        if len(param_labels) == 1:
            axes = [axes]

        # loops for plotting
        for j in range(0, len(param_labels)):
            for i, sensor_number in enumerate(sensor_numbers, start=0):
                current_data = data_to_plot[param_labels[j]].loc[
                    data_to_plot['sensor_number'] == sensor_number]

                axes[j].plot(current_data, label=legend_series[i],
                             marker='.', alpha=0.5,
                             linewidth=1.5,
                             markersize=6)

                axes[j].set_ylabel(plot_labels[j], rotation='horizontal',
                                   ha='right', va='baseline', 
                                   fontsize=fontsizeL, wrap=True)

        # get handles and labels for legend
        handles, labels = axes[-1].get_legend_handles_labels()

        # adjust position of plots so there is room for text in legend. 
        # defaults: left = 0.125  right = 0.9
        plt.subplots_adjust(left=0.125, right=0.75)

        # set legend
        leg = axes[0].legend(handles, labels, frameon=False, 
                             fontsize=fontsizeL, markerscale=3, 
                             bbox_to_anchor=(1, 1))

        # set plot title
        fig.suptitle(plot_title, y=.95, fontsize=fontsizeL * 2)

        # set line thickness in legend
        for line in leg.get_lines():
            line.set_linewidth(3)

        # label x axis
        plt.xlabel('Time', fontsize=fontsizeL)
        plt.rcParams.update({'font.size': fontsizeS + 2})

        # conifgure the x axis for the optimal time range
        locator = mdates.AutoDateLocator(minticks=4, maxticks=8)
        formatter = mdates.ConciseDateFormatter(locator)
        axes[-1].xaxis.set_major_locator(locator)
        axes[-1].xaxis.set_major_formatter(formatter)

        # save the plot
        fig.savefig(file_name, dpi=500)

        # show the plot
        plt.show()

        return

    def aggregate_data(self, data_to_aggregate, parameters):
        ''' Aggregates the data from all sensors in the dataframe providing 
        they are from the same room. Can aggregate data from any number of 
        sensors in a room, but not sensors in different rooms. 
        Process:
        - Sorts dataframes and creates strings for the fields in output 
            dataframe
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
        data_to_aggregate = data_to_aggregate.sort_values(
            by=['sensor_number', 'timestampms'])

        # get lists of sensor_numbers and sensor names from dataframe
        sensor_numbers = data_to_aggregate['sensor_number'].unique().tolist()
        sensor_names = data_to_aggregate['sensor_name'].unique().tolist()

        # convert list to str for use in field in output dataframe
        sensor_numbers_str = str(', '.join(str(x) for x in sensor_numbers))
        sensor_names_str = str(', '.join(sensor_names))

        # find the room name and number from the sensor numbers
        sensor_numbers, sensor_names, room_number, room_name = \
            self.get_names_and_numbers(sensors=sensor_numbers)

        # round times in data_to_aggregate to the nearest minute
        data_to_aggregate['timestamputc'] = \
            pd.to_datetime(data_to_aggregate['timestampms'], unit='ms')
        data_to_aggregate['timestamputc'] = \
            data_to_aggregate['timestamputc'].dt.floor('Min')
        data_to_aggregate['timestampms'] = \
            data_to_aggregate[['timestamputc']].apply(
                lambda x: x[0].timestamp(), axis=1).astype('int64') * 1000

        # aggregate to get mean reading per sensor per minute
        mean_per_minute_per_sensor = data_to_aggregate.groupby(
            ['timestampms', 'sensor_number'], 
            as_index=False)[parameters].mean()

        # generate mean of mean (all parameters)
        mean_per_minute_total = mean_per_minute_per_sensor.groupby(
            ['timestampms']).mean()

        # collect data for output 
        aggregated_data = mean_per_minute_total

        # if it exists, get sum of occupancy and replace the mean with it
        if 'occupancy' in aggregated_data.columns:            
            occupancy_sum = mean_per_minute_per_sensor.groupby(
                ['timestampms']).sum()
            aggregated_data['occupancy'] = occupancy_sum['occupancy']

        # set the index to timestampms
        aggregated_data['timestampms'] = aggregated_data.index

        # add 1 ns to preserve time format. (could be better way to do this).
        aggregated_data['timestamputc'] = aggregated_data['timestampms'] \
            .apply(lambda t: dt.datetime.utcfromtimestamp(int(t / 1000))
                   .isoformat() + '.000001+00:00')

        #  set columns for the ouput dataframe from strings made earlier.
        aggregated_data['room_name'] = room_name[0]
        aggregated_data['room_number'] = room_number[0]
        aggregated_data['sensor_name'] = sensor_names_str
        aggregated_data['sensor_number'] = sensor_numbers_str

        return (aggregated_data)

    def set_defaults(self):
        '''
        Sets plotting parameters of DatabasePlotter() class. Sets only those
        set to None to default. Takes no input but checks and changes the 
        parameters of the class.

        Parameters
        ----------
        sensor_numbers : LIST of INT, optional
            List of INT corresponding to sensor numbers from 
            DatabasePlotter.sensor_numbers. Default = all.
        sensor_names : LIST of STR, optional
            List of STR corresponding to sensor names 
            DatabasePlotter.sensor_names. Default = all.
        room_numbers : LIST of STR, optional
            List of INT corresponding to room numbers from 
            DatabasePlotter.room_numbers. Default = all.
        room_names : LIST of STR, optional
            List of STR corresponding to room names from 
            DatabasePlotter.room_names. Default = all.
        time_from : INT, optional
            First time to plot in ms timestamp format. 
            Default = first available.
        time_to : INT, optional
            Last time to plot in ms timestamp format. 
            Default = most recent available.
        parameters : LIST of STR, optional
             Choice of parameters from DatabasePlotter.param_list. 
             Default = all.
        overlay : INT, optional
            0 = seperate plots, 1 = overlay on same plot. Default = 1.
        aggregate : INT, optional
            0 = individual sensors, 1 = aggregate sensors in same room. 
            Default = 0.
        seperate : INT, optional
            0 = 1 sensors from different rooms on same plot, 1 = sensors 
            from different rooms are plotted seperately. Only relevant if 
            overlay = 1 and aggregate = 0.
            Default = 1.

        Returns
        -------
        No returns - sets plot parmaters as attributes of DatabasePlotter() 
        class.

        '''

        # get sensor numbers and names. Only requires uses sensors number
        # as if there is input, others are there from early in
        # plot_from_database()
        self.sensor_numbers, self.sensor_names, self.room_numbers, \
            self.room_names = \
                self.get_names_and_numbers(sensors=self.sensor_numbers)

        if self.sensor_numbers == None:
            self.sensor_numbers = self.all_sensor_numbers
        if self.sensor_names == None:
            self.sensor_names = self.all_sensor_names
        if self.room_numbers == None:
            self.room_numbers = self.all_room_numbers
        if self.room_names == None:
            self.room_names = self.all_room_names
        if self.time_from == None:
            # time_from = Scraper._time_now() - 86400000 # previous 24 hours
            # time_from = Scraper._time_now() - 604800000 # previous week
            self.time_from = 1580920305102  # from first sensor reading
        if self.time_to == None:
            self.time_to = Scraper._time_now()
        if self.parameters == None:
            self.parameters = self.param_list
        if self.overlay == None and len(self.sensor_numbers) > 1:
            self.overlay = 1
        elif self.overlay == None:
            self.overlay = 0
        if self.aggregate == None:
            self.aggregate = 0
        if self.seperate == None:
            self.seperate = 1

        return 

    def choose_from_command_line(self, input_choice):
        '''
        Takes user input to generate plot from command line. Minimum 
        requirement is entering either 'sensors' or 'rooms' to choose from. 
        All other parameters are provided as they can be set in command line 
        so that the user is only prompted to change unset parameters.

        Parameters
        ----------
        input_choice : STR
            Enter 'sensors', 'rooms', or 'parameters'. Prompts will adjust 
            accordingly. For parameters, sensors or rooms inputs must be set
            for plot_from_database()
        sensors : single/LIST of INT or STR, optional
            If ints: [1, 2, 3] 
            If str: ['0-Café-1', '0-Café-2', '0-Cafe-3']
            Can also read individual values not in lists. Default collects 
            all available.
        rooms : single/LIST of INT or STR, optional
            If ints: [1, 2, 3] 
            If str: ['0-Café', '0-Exhibition-Area', '2-Open-Office']
            Can also read individual values not in lists. Default collects 
            all available.

        See DatabasePlotter.set_defaults() docstring for further information 
        on parameters.

        Returns
        -------
        Parameters set depending non user input.

        '''

        # %% establish sensor and room numbers and names
        if self.sensor_numbers == None and self.room_numbers == None:
            if input_choice == 'rooms':
                self.room_numbers, self.room_names = \
                    Scraper._choose_by_number(self.room_info, 'room_name')
            elif input_choice == 'sensors':
                self.sensor_numbers, self.sensor_names = \
                    Scraper._choose_by_number(self.sensor_location_info, 
                                              'sensor_name')
            elif input_choice == 'parameters':
                print("Using all sensors.")
                self.sensor_numbers = self.all_sensor_numbers
            else:
                print("Unknown input for variable 1: input_choice. Enter "
                      "'rooms' or 'sensors', including quotes.")
                return

        self.sensor_numbers, self.sensor_names, self.room_numbers, \
            self.room_names = \
                self.get_names_and_numbers(sensors=self.sensor_numbers,
                                               rooms=self.room_numbers)

        # %% find which variables are still empty and query whether 
        # user wants to use defaults
        input_list = [self.time_from, self.time_to, self.parameters, 
                      self.overlay, self.aggregate, self.seperate]
        input_str_list = ['time_from', 'time_to', 'parameters', 
                          'overlay', 'aggregate', 'seperate']
        default_settings = ['first available', 'most recent', 'all', 
                            'overlay', 'do not aggregate', 
                            'rooms on different plots']
        empty_input_str = []
        default_str = []

        for input_var, input_str, default in zip(input_list, input_str_list, 
                                                 default_settings):
            if input_var == None:
                empty_input_str.append(input_str)
                default_str.append(default)

        empty_input_str = str(', '.join(empty_input_str))
        default_str = str(', '.join(default_str))

        use_default = input('No preference specified for: {}. \n'
                            'Default: {}. \nUse default settings? \n[y/n]: '
                            .format(empty_input_str, default_str))

        # %% use defaults or provide further choice based on user input
        if (not use_default) or (use_default == 'y'):
            print("Using defaults.")
            self.set_defaults()
        else:
            if (self.time_from == None) and (self.time_to == None):
                self.time_from, self.time_to = DatabasePlotter._choose_time()
            elif self.time_from == None and self.time_to:
                self.time_from = input(
                    'Input start time to plot in ms epochs in format (enter '
                    '= use default): \n')
                if len(self.time_from) > 0:
                    self.time_from = eval(self.time_from)
                else:
                    self.time_from = None
            elif self.time_from and self.time_to == None:
                self.time_to = input(
                    'Input end time to plot in ms epochs in format (enter = '
                    'use default): \n')
                if len(self.time_to) > 0:
                    self.time_to = eval(self.time_to)
                else:
                    self.time_to = None
            if self.parameters == None:
                _, self.parameters = Scraper._choose_by_number(
                    self.param_list, 'parameter')
            if self.overlay == None and len(self.sensor_numbers) > 1:
                self.overlay = input('Overlay plots on same graph? \n[y/n]: ')
                if (not self.overlay) or (self.overlay == 'y'):
                    self.overlay = 1
                elif self.overlay == 'n':
                    self.overlay = 0
                else:
                    print('Unknown input.')
            elif self.overlay == None:
                self.overlay = 0
            if self.aggregate == None and len(self.sensor_numbers) > \
                len(self.room_numbers):
                self.aggregate = input(
                    'Aggregate sensors from same room? \n[y/n]: ')
                if (not self.aggregate) or (self.aggregate == 'y'):
                    self.aggregate = 1
                elif self.aggregate == 'n':
                    self.aggregate = 0
                else:
                    print('Unknown input.')
            elif self.aggregate == None:
                self.aggregate = 0
            if self.seperate == None and self.aggregate == 0 and \
                self.overlay == 1 and len(self.room_numbers) >1:
                self.seperate = input(
                    'Plot sensors from different rooms on seperate plots? '
                    '\n[y/n]: ')
                if (not self.seperate) or (self.seperate == 'y'):
                    self.seperate = 1
                elif self.seperate == 'n':
                    self.seperate = 0
                else:
                    print('Unknown input.')
            
            # for any that the user skipped
            self.set_defaults()

        return 

    def get_names_and_numbers(self, sensors=None, rooms=None):
        '''Input a list of one the following: sensor numbers, sensor names, 
        room numbers, or room names. Returns lists of the others that 
        correspond to the input. For example: input list of sensor numbers, 
        receive a corresponding list of sensor names, a list of the room 
        numbers which contain these sensors, and a list of room names which 
        corresponds to the room numbers. 

        Important to specify 'rooms' or 'sensors'.

        Duplicates are removed from the lists, and all lists are sorted 
        according to their corresponding number in the DatabasePlotter() 
        class. Therefore recommended to assign an output variable for the 
        same as the input:

        e.g. if input is sensors=[3,3,2,1], output for sensor_numbers 
        will be [1,2,3]).        

        '''

        # use these to simplify code in the following sections
        sensor_info = self.sensor_location_info
        room_info = self.room_info

        # put into a list if not already so function can deal with it
        if isinstance(sensors, int) or isinstance(sensors, str):
            sensors = [sensors]
        if isinstance(rooms, int) or isinstance(rooms, str):
            rooms = [rooms]

        if sensors != None:
            # if sensor numbers, define sensor names and numbers
            if isinstance(sensors[0], int):
                sensor_numbers = sensor_info.loc[sensors].sort_index(
                ).index.unique().tolist()
                sensor_names = sensor_info['sensor_name']\
                    .loc[sensor_numbers].tolist()
            # if sensor names, define sensor names and numbers
            elif isinstance(sensors[0], str):
                sensor_names = \
                    sensor_info.loc[sensor_info['sensor_name'].isin(
                    sensors)]['sensor_name'].tolist()
                sensor_numbers = \
                    sensor_info.loc[sensor_info['sensor_name'].isin(
                    sensor_names)].index.tolist()

            # get a list of which room each sensor is in with no duplicates
            room_names = sensor_info['room_name'].loc[sensor_numbers].unique(
            ).tolist()
            # sort these so they are in order of room number
            room_names = room_info.loc[room_info['room_name'].isin(
                room_names)]['room_name'].tolist()
            # get corresponding numbers
            room_numbers = room_info.loc[room_info['room_name'].isin(
                room_names)].index.tolist()
        elif rooms != None:
            # if room numbers, define room names and numbers
            if isinstance(rooms[0], int):
                room_numbers = room_info.loc[rooms].sort_index(
                ).index.unique().tolist()
                room_names = room_info['room_name'].loc[room_numbers].tolist()
            # if sensor names, define sensor names and numbers
            elif isinstance(rooms[0], str):
                room_names = room_info.loc[room_info['room_name'].isin(
                    rooms)]['room_name'].tolist()
                room_numbers = room_info.loc[room_info['room_name'].isin(
                    room_names)].index.tolist()

            sensor_numbers = sensor_info.loc[sensor_info['room_name'].isin(
                room_names)].index.tolist()
            # get a list of which room each sensor is in with no duplicates 
            # and get room numbers from these
            sensor_names = \
                sensor_info['sensor_name'].loc[sensor_numbers].unique(
                    ).tolist()
        elif sensors == None and rooms == None:
            sensor_numbers = None
            sensor_names = None
            room_numbers = None
            room_names = None
            return (sensor_numbers, sensor_names, room_numbers, room_names)

        # this means it has failed
        if len(sensor_numbers) + len(room_names) < 2:
            sys.exit("Sensor/room input not recongised. Check inputs - e.g. "
                     "plot_from_database('rooms'=['0-Café', "
                     "'0-Exhibition-Area'])")

        return (sensor_numbers, sensor_names, room_numbers, room_names)

    def plot_from_database(self, choose_by_input=None, sensors=None, 
                           rooms=None, time_from=None, 
                           time_to=None, parameters=None, 
                           overlay=None, aggregate=None, 
                           seperate=None):
        '''
        Evaluates inputs to plot from database. Determines whether user 
        to take user input to from command line, and if not, plots using the 
        parameters set in the input with all others set to default. With no 
        inputs, all are set to default. To choose from command line, minimum 
        required input is 'sensors' or 'rooms'. Other parameters are can be 
        set and they will not be prompted for in command line.

        Parameters
        ----------
        choose_by_input_ : STR
            Enter either 'sensors' or 'rooms'. Prompts will adjust accordingly.
        sensors : single/LIST of INT or STR, optional
            If ints: [1, 2, 3] 
            If str: ['0-Café-1', '0-Café-2', '0-Cafe-3']
            Can also read individual values not in lists. 
            Default collects all available.
        rooms : single/LIST of INT or STR, optional
            If ints: [1, 2, 3] 
            If str: ['0-Café', '0-Exhibition-Area', '2-Open-Office']
            Can also read individual values not in lists. 
            Default collects all available.

        See DatabasePlotter.set_defaults() docstring for further information 
        on parameters.

        Returns
        -------
        None
        '''
        # %% first, establish the parameters for plotting
        
        # update the class parameters to plot based on input
        self.time_from = time_from
        self.time_to = time_to 
        self.parameters = parameters
        self.overlay = overlay
        self.aggregate = aggregate
        self.seperate = seperate

        # retrieve room and sensor names and numbers from the list of ints 
        # or str input in sensors or rooms
        self.sensor_numbers, self.sensor_names, self.room_numbers, \
            self.room_names = self.get_names_and_numbers(sensors=sensors,
                                                         rooms=rooms)

        # choose from command line depending on user choice
        if choose_by_input != None:
            self.choose_from_command_line(choose_by_input)
        else:  # set the unset variables to default
            if self.sensor_numbers == None:        
                print('No sensors or rooms entered, setting to default '
                      '(all).')
            self.set_defaults()

        # %% aggregate = 0 overlay = 0
        if self.aggregate == 0 and self.overlay == 0:
            for sensor_number, sensor_name in zip(self.sensor_numbers, 
                                                  self.sensor_names):
                data_to_plot = self.retrieve_data(sensor_number, 
                                                  self.time_from, 
                                                  self.time_to, 
                                                  self.parameters)
                if not data_to_plot.empty:
                    print('Plotting data from sensor {}: {}...'.format(
                        sensor_number, sensor_name))
                    self.plot_from_dataframe(data_to_plot)
                else:
                    continue
            return

        # %% aggregate = 0 overlay = 1
        elif self.aggregate == 0 and self.overlay == 1:
            if self.seperate == 1:
                for room_number, room_name in zip(self.room_numbers, 
                                                  self.room_names):
                    sensors_in_current_room = self.sensors_in_room(
                        self.sensor_numbers, room_name)
                    data_to_plot = self.retrieve_data(sensors_in_current_room, 
                                                      self.time_from, 
                                                      self.time_to, 
                                                      self.parameters)
                    if not data_to_plot.empty:
                        print('Plotting overlaid data from {} sensors from '
                              'room {}: {}...'
                             .format(len(sensors_in_current_room), 
                                     room_number, room_name))
                        self.plot_from_dataframe(data_to_plot)
                    else:
                        continue
            else:
                data_to_plot = self.retrieve_data(self.sensor_numbers, 
                                                  self.time_from, 
                                                  self.time_to, 
                                                  self.parameters)
                if not data_to_plot.empty:
                    print('Plotting overlaid data from {} sensors from {} '
                          'room(s)...'
                          .format(len(self.sensor_numbers), 
                                  len(self.room_numbers)))
                    self.plot_from_dataframe(data_to_plot)
                    return
                else:
                    return

        # %% aggregate = 1 overlay = 0
        elif self.aggregate == 1 and self.overlay == 0:
            for room_number, room_name in zip(self.room_numbers, 
                                              self.room_names):
                sensors_in_current_room = self.sensors_in_room(
                    self.sensor_numbers, room_name)
                data_to_plot = self.retrieve_data(sensors_in_current_room, 
                                                  self.time_from, 
                                                  self.time_to, 
                                                  self.parameters)
                if not data_to_plot.empty:
                    print('Aggregating data for {} sensors in room {}: {}...'
                          .format(len(sensors_in_current_room), room_number, 
                                  room_name))
                    aggregated_data = self.aggregate_data(
                        data_to_plot, self.parameters)
                    print('Plotting aggregated data from {} sensors from '
                          'room {}: {}...'
                          .format(len(sensors_in_current_room), room_number, 
                                  room_name))
                    self.plot_from_dataframe(aggregated_data, aggregate=1)
                else:
                    continue
            return

        # %% aggregate = 1 overlay = 1
        elif self.aggregate == 1 and self.overlay == 1:
            aggregated_dfs = pd.DataFrame
            for room_number, room_name in zip(self.room_numbers, 
                                              self.room_names):
                sensors_in_current_room = self.sensors_in_room(
                    self.sensor_numbers, room_name)
                data_to_plot = self.retrieve_data(sensors_in_current_room, 
                                                  self.time_from, 
                                                  self.time_to, 
                                                  self.parameters)
                if not data_to_plot.empty:
                    print('Aggregating data for {} sensors in room {}: {}...'
                          .format(len(sensors_in_current_room), room_number, 
                                  room_name))
                    aggregated_data = self.aggregate_data(
                        data_to_plot, self.parameters)
                    if aggregated_dfs.empty:
                        aggregated_dfs = aggregated_data.copy()
                    else:
                        aggregated_dfs = pd.concat(
                            [aggregated_dfs, aggregated_data], axis=0)
                else:
                    continue
            print('Plotting available data from {} sensors from {} rooms, '
                  'aggregated and overlaid...'
                  .format(len(self.sensor_numbers), len(self.room_numbers)))
            self.plot_from_dataframe(aggregated_dfs, aggregate=1)
            return

    def sensors_in_room(self, sensor_numbers, room_name):
        ''' Returns all sensors in a list which are in a specified room. List 
        does not have to be complete list of sensors.'''

        sensor_numbers.sort()
        sensors_in_current_room = []
        for sensor_number in sensor_numbers:
            if self.sensor_location_info['room_name'].loc[sensor_number] \
                == room_name: 
                    sensors_in_current_room.append(sensor_number)
        return (sensors_in_current_room)

    def __del__(self):
        '''Destructor commits any remaining data to the database and closes 
        the connection'''
        print("Closing connection to the database")
        self.conn.close()
