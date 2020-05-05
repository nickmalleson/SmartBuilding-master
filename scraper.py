# -*- coding: utf-8 -*-
"""
scraper.py

Script for accessing the API of the Connected Places Smart Building using 
python and the "requests" library.

IMPORTANT: to log in automatically, place a .txt file named 
'SmartBuildingParameters.txt' in a folder named 'SmartBuildingParameters' 
in the same diretory as scraper.py. The file should contain the login details 
in the following format:

"username = user138
password = letmein"

Created on Thu Oct 17 16:11:16 2019

@author: Thomas Richards

"""
import getpass  # required to keep password invisible
from matplotlib.ticker import MaxNLocator
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import requests as r  # required to access API
import sys
import time
import datetime as dt
from dateutil.parser import parse


class Scraper():
    '''Obtains login details and stores data associated with the account in
    constant variables.
    '''

    def __init__(self, login=True):

        self.username, self.password, self.building_info = \
            Scraper._login(login)

        self.contract_info = self.get_contract_info()
        print("Contract data retrieved successfully.")
        self.customer_info = self.get_customer_info()
        print("Customer data retrieved successfully.")
        self.managed_space_info = self.get_managed_space_info()
        print("Managed space data retrieved successfully.")
        self.sensor_location_info = self.get_sensor_location_info()
        print("Sensor locations retrieved successfully.")
        self.room_info = self.get_room_info()
        print("Room information retrieved successfully.")

    @staticmethod
    def _login(auto=True):
        '''Obtain and check username and password for Smart Building API.

        Username and password can be obtained by user input, or by reading a
        parameters file (see the 'auto' parameter). The credentials are then
        checked by using the 'building' function on the API, and if successful,
        username, password, and the output of the API 'building' function are 
        returned.

        Parameters
        ----------
        auto: bool (default true)
            If true then automatically get the credentials from a parameters 
            file.
            Otherwise ask for them from user input.

        '''

        username = ""
        password = ""

        if auto:
            username, password = Scraper._get_login_info()

        else:  # prompt to enter username or press enter to use saved details
            username = input(
                "Enter username or press enter to log in as 'yanjiedong':")
            # if enter was pressed use saved username and password
            if username == '':
                username, password = Scraper._get_login_info()
            else:
                # Enter password manually. Password is hidden (external only)
                # console if using Spyder.'''
                password = getpass.getpass(prompt='Password:')

        # Use 'building' API function to check username and password.
        response = r.get(
            'https://console.beringar.co.uk/api/building/',
            auth=(username, password))
        responsecheck = response.status_code

        # Sucess code = 200, Failed = 400 (simplified).
        if 200 <= responsecheck < 300:
            # Obtain building name from response
            building_info = pd.DataFrame(response.json())
            building_info['buildingnumber'] = list(
                range(1, len(building_info) + 1))
            building_info = building_info.set_index('buildingnumber')

            print('Login successful.\nBuilding info aquired successfully '
                  'from {} building(s). First building: {}.'
                  .format(len(building_info), building_info['name'].loc[1]))
            return (username, password, building_info)

        # If here then we weren't able to log on.
        raise Exception(
            'Problem logging in. Response code: {} (success = 200).'
            .format(responsecheck))

    @staticmethod
    def _get_login_info():
        ''' Get login username and password from locally stored parameter 
        file.'''

        # Look in folder in directory above the present working directory
        parameter_file_path = './SmartBuildingParameters/'
        parameter_file_name = 'SmartBuildingParameters.txt'
        parameter_file = open(parameter_file_path + parameter_file_name)
        params = {}
        for line in parameter_file:
            line = line.strip()
            key_value = line.split(' = ')
            params[key_value[0].strip()] = key_value[1].strip()
        username = params['username']
        password = params['password']
        return (username, password)

    def _call_API(self, function_name):
        """Call the API, inserting 'function_name' into the URL. E.g.:
            https://console.beringar.co.uk/api/<function_name>/

        :param function_name: the name of the API function to call
        :return: the json returned by the response if successful (converted
        from a dict to a dataframe) or raise an IOError if the call failed.
        """
        url = 'https://console.beringar.co.uk/api/{}'.format(function_name)
        # print(url)
        response = r.get(url, auth=(self.username, self.password))
        status_code = response.status_code

        # Success code = 200, Failed = 400 (simplified).
        if 200 <= status_code < 300:
            # Response as OK.
            if response.json():
                response_df = pd.DataFrame(pd.DataFrame(response.json()))
                response_df['number'] = list(range(1, len(response_df) + 1))
                response_df = response_df.set_index('number')
            else:
                response_df = response.json()
        return (response_df)

        # Failed if here
        print('API call failed with code: {}.'.format(status_code))
        raise IOError("Call to the API failed ({}) on url: '{}'".format(
            status_code, url))

    def get_contract_info(self):
        '''Get all contract info associated with account.'''
        contract_info = self._call_API("contract")
        contract_info.index.name = "contractnumber"
        return (contract_info)

    def get_customer_info(self):
        '''Get all customer info associated with account.'''
        customer_info = self._call_API("customer")
        customer_info.index.name = "customernumber"
        return (customer_info)

    def get_sensor_location_info(self):
        '''Get all sensor location info associated with your account.'''
        sensor_location_info = self._call_API("sensorlocation")
        sensor_location_info.index.name = "sensornumber"
        return (sensor_location_info)

    def get_room_info(self):
        '''Get all room info associated with your account.'''
        room_info = self._call_API("room")
        room_info.index.name = "roomnumber"
        return (room_info)

    def get_managed_space_info(self, building_number=1):
        ''' Get all managed spaces associated with your account. Requires 
        building number from self.building_info - default = 1.
        '''

        building_id = self.building_info['id'].loc[building_number]
        function_name = 'managedspace/building/{0}'.format(building_id)
        managed_space_info = self._call_API(function_name)
        managed_space_info.index.name = "spacenumber"
        return (managed_space_info)

    # %%

    def managed_space_after(self,
                            managed_space_numbers=None,
                            timestamp_epoch_millisec=None):
        ''' Get sensor readings (max 1000) for all, or a given managed space, 
        after a specified time point. No inputs returns data from all using 
        timestamp from 1100 minutes ago.

        Parameters
        ----------
        managed_space_numbers: int/list of ints
            Single number or list of numbers corresponding to managed spaces. 
            Use: 
            'chosen_numbers, chosen_names = \
                _choose_by_number(self.managed_space_info)'
            to get a list of numbers corresponding to space names.
        timestamp_epoch_millisec: int
            A time in ms epoch. Returns data from this time and includes up to 
            1000 time points (one per minute). Default 1100 (usually returns 
            1000 rows for each available sensor).

        Returns
        -------
        managed_space_after_data: list of dataframes
            Data from responding sensors. Non-responding sensors are not 
            included. Data in managed_space_after_data[x] is from the space 
            number in managed_spaces[x]. The 'spacenumber' column in each 
            managed_space_after_data index also corresponds to the relevant 
            index in self.managed_space_info.
        managed_spaces: list of ints
            List of responding sensors that returned data. The number in each 
            element corresponds to a spacenumber index in 
            self.managed_space_info.

        '''
        all_managed_space_numbers = list(self.managed_space_info.index)

        if isinstance(managed_space_numbers, int):
            managed_space_numbers = [managed_space_numbers]

        if managed_space_numbers is None:
            managed_space_numbers = all_managed_space_numbers

        for i in managed_space_numbers:
            if i not in all_managed_space_numbers:
                sys.exit('\nBad index in input list: {}. Check '
                         'self.managed_space_info for list.'
                         .format(str(i)))

        ''' Default time is 1100 minutes from when call was made. This is 
        usually enough to get 1000 data points for each sensor. '''
        if timestamp_epoch_millisec is None:
            timestamp_epoch_millisec = Scraper._time_now()-66000000

        # Convert input time to ISO format
        input_time = dt.datetime.utcfromtimestamp(
            int(timestamp_epoch_millisec / 1000)).isoformat()

        print('\nGetting managed space after data from API.\nMs time epoch '
              'used for input: {}. Input in ISO format: {}.'
              .format(timestamp_epoch_millisec, input_time))

        managed_space_after_data = []
        managed_spaces = []
        fail = 0
        succ = 0

        # enumerate because input_num and i are not necessarily related
        for input_num, space_num in enumerate(managed_space_numbers, start=0):
            space = self.managed_space_info.loc[space_num]
            function_name = "beta/managedspace/spacelocation/{}/after/{}" \
                .format(space['id'], timestamp_epoch_millisec)

            try:
                response = self._call_API(function_name)
            except Exception as e:
                print('Managed space number {}: {}. PROBLEM AQUIRING '
                      'DATA. Error: {}'.format(space_num, space['name'],
                                               str(e)))
                fail += 1

            if not isinstance(response, pd.core.frame.DataFrame):
                print('Managed space number {}: {}. NO DATA RETURNED.'
                      .format(space_num, space['name']))
                fail += 1
            else:
                response['spacenumber'] = space_num
                managed_space_after_data.append(response)
                managed_spaces.append(space_num)
                print('Managed space number {}: {}. Successfully aquired'
                      ' {} rows of data.'
                      .format(space_num, space['name'],
                              len(managed_space_after_data[-1])))
                succ += 1
        print('Data successfully aquired from {} of {} possible managed '
              'space(s).'
              .format(succ, succ + fail))

        return (managed_space_after_data, managed_spaces)

    # %%
    def managed_space_latest(self, building_number=1):
        ''' Get latest managed space readings from managed spaces of (default) 
        building number 1. Since the API call returns a list which excludes 
        non-responsive sensors, the output from this function may be shorter 
        than the total number of sensors.

        Returns
        -------
        managed_space_latest_data: dataframe containing one row for each 
        responsive sensor. The 'spacenumber' column match indices in 
        'self.managed_space_info'.

        '''

        all_possible_space_numbers = list(self.managed_space_info.index)

        # Construct the name of the function to be embedded into the
        # API URL
        function_name = "managedspace/latest/building/{}".format(
            self.building_info['id'].loc[building_number])

        print('\nGetting latest managed space data from API.')

        # try the API call for the current building, except if fails
        try:
            """ the 'managed_space_latest_data' variable will not include 
            non-responsive sensors so will return a list shorter than total 
            number of sensors in self.managed_space_info"""
            managed_space_latest_data = self._call_API(function_name)
            # if the API call fails, state this and move to next
        except Exception as e:
            print('Could not acquire latest managed space data from building '
                  'number {}: {}. PROBLEM ACQUIRING DATA. Error: {}'
                  .format(1, self.building_info['name'].loc[building_number],
                          str(e)))

        """ Check the ids of the returned managed spaces against all those 
        available and return a list of corresponding indices from 'self'"""
        returned_space_numbers = []
        for space_id in managed_space_latest_data['managedspace']:
            returned_space_numbers.append(int(
                self.managed_space_info[
                    self.managed_space_info['id'] == space_id].index.values))

        """ add new column in response which corresponds with indices from 
        self, sort, and make it the index column"""
        managed_space_latest_data['spacenumber'] = returned_space_numbers
        managed_space_latest_data = managed_space_latest_data.sort_values(
            by=['spacenumber'], inplace=False)
        managed_space_latest_data = managed_space_latest_data.set_index([
            'spacenumber'])

        # check for missing spaces and print names and numbers if one is found
        for i in all_possible_space_numbers:
            if i not in returned_space_numbers:
                print('Managed space location number {}: {}. NO DATA RETURNED.'
                      .format(i, self.managed_space_info['name'].loc[i]))

        print('Latest managed space readings acquired successfully from: {} '
              'of {} possible sensors.'
              .format(len(returned_space_numbers),
                      len(all_possible_space_numbers)))

        return (managed_space_latest_data, returned_space_numbers)

    # %%
    def sensor_reading_after(self,
                             sensor_numbers=None,
                             timestamp_epoch_millisec=None):
        ''' Get sensor readings (max 1000) for all, or a given sensor location,
        after a specified time point. No inputs returns data from all using 
        timestamp from 1100 minutes ago.

        Parameters
        ----------
        sensor_numbers: int/list of ints
            Single number or list of numbers corresponding to sensor location 
            numbers. Use: 
            'chosen_numbers, chosen_names = \
                _choose_by_number(self.sensor_location_info)'
            to get a list of numbers corresponding to sensor location names.
        timestamp_epoch_millisec: int
            A time in ms epoch. Returns data from this time and includes up to
            1000 time points (one per minute). Default 1100 (usually returns 
             1000 rows for each available sensor).

        Returns
        -------
        sensor_reading_after_data: list of dataframes
            Data from responding sensors. Non-responding sensors are not 
            included. Data in sensor_reading_after_data[x] is from the sensor 
            location number in sensor_locations[x]. The 'sensornumber' column 
            in each sensor_reading_after_data index also corresponds to the 
            relevant index in self.sensor_location_info.
        sensor_locations: list of ints
            List of responding sensors that returned data. The number in each 
            element corresponds to a sensornumber index in 
            self.sensor_location_info.

        '''

        all_sensor_numbers = list(self.sensor_location_info.index)

        if isinstance(sensor_numbers, int):
            sensor_numbers = [sensor_numbers]

        if sensor_numbers is None:
            sensor_numbers = all_sensor_numbers

        for i in sensor_numbers:
            if i not in all_sensor_numbers:
                sys.exit(
                    '\nBad index in input list: {}. '
                    'Check self.sensor_location_info for list.'.format(str(i)))

        # Default time is 1100 minutes from when call was made. This is usually
        # enough to get 1000 data points for each sensor.
        if timestamp_epoch_millisec is None:
            timestamp_epoch_millisec = Scraper._time_now()-66000000

        # Convert input time to ISO format
        input_time = dt.datetime.utcfromtimestamp(
            int(timestamp_epoch_millisec / 1000)).isoformat()

        print('\nGetting sensor reading after data from API.\nMs time epoch '
              'used for input: {}. Input in ISO format: {}.'
              .format(timestamp_epoch_millisec, input_time))

        sensor_reading_after_data = []
        sensor_locations = []
        fail = 0
        succ = 0

        # enumerate because input_num and i are not necessarily related
        for input_num, sensor_num in enumerate(sensor_numbers, start=0):
            sensor = self.sensor_location_info.loc[sensor_num]
            function_name = "beta/sensorreading/sensorlocation/{}/after/{}" \
                .format(sensor['id'], timestamp_epoch_millisec)

            try:
                response = self._call_API(function_name)
            except Exception as e:
                print("Sensor number {}: {}. PROBLEM AQUIRING "
                      "DATA. Error: {}".format(sensor_num, sensor['name'],
                                               str(e)))
                fail += 1

            if not isinstance(response, pd.core.frame.DataFrame):
                print('Sensor number {}: {}. NO DATA RETURNED.'
                      .format(sensor_num, sensor['name']))
                fail += 1
            else:

                # Sort timestamp columns to match other functions
                response = \
                    response.rename(columns={'rxtimestamputc': 'timestamputc',
                                             'rxepochmillisec': 'timestampms',
                                             'sensorlocationcurrent':
                                                 'sensorlocation'})
                response['timestamputc'] = response['timestamputc'].apply(
                    parse)

                # add 'sensornumber' column
                # TODO: Make sure sensornumber is correct.
                response['sensornumber'] = sensor_num

                # add 'name' column for room name
                response['name'] = list(
                    self.sensor_location_info['name']
                    .loc[response['sensornumber']])

                sensor_reading_after_data.append(response)
                sensor_locations.append(sensor_num)

                print('Sensor number {}: {}. Successfully aquired'
                      ' {} rows of data.'
                      .format(sensor_num, sensor['name'],
                              len(sensor_reading_after_data[-1])))
                succ += 1

        print('Data successfully aquired from {} of {} possible sensor '
              'location(s).'
              .format(succ, succ + fail))

        return (sensor_reading_after_data, sensor_locations)

    def sensor_reading_latest(self, building_number=1):
        ''' Get latest sensor readings from sensor locations of (default) 
        building number 1. Since the API call returns a list which excludes 
        non-responsive sensors, the output from this function may be shorter 
        than the total number of sensors.

        Returns
        -------
        sensor_reading_latest_data: dataframe containing one row for each 
        responsive sensor. The 'sensornumbers' column match indices in 
        'self.sensor_location_info'.

        '''

        all_possible_sensor_numbers = list(self.sensor_location_info.index)

        # Construct the name of the function to be embedded into the
        # API URL
        function_name = "sensorreading/latest/building/{}".format(
            self.building_info['id'].loc[building_number])

        print('\nGetting latest sensor reading data from API.')

        # try the API call for the current building, except if fails
        try:
            ''' the 'sensor_reading_latest_data' variable will not include 
            non-responsive sensors so will return a list shorter than total 
            number of sensors in self.sensor_location_info'''
            sensor_reading_latest_data = self._call_API(function_name)
            # if the API call fails, state this and move to next
        except Exception as e:
            print('Could not acquire latest sensor reading data from building '
                  'number {}: {}. PROBLEM ACQUIRING DATA. Error: {}'
                  .format(1, self.building_info['name'].loc[building_number],
                          str(e)))

        """ Check the ids of the returned sensor locations against all those 
        available and return a list of corresponding indices from 'self'"""
        returned_sensor_numbers = []
        for sensor_id in sensor_reading_latest_data['sensorlocation']:
            # TODO: check this is correct:
            returned_sensor_numbers.append(int(
                self.sensor_location_info[self.sensor_location_info['id'] ==
                                          sensor_id].index.values))

        # Sort timestamp columns to match other functions
        sensor_reading_latest_data['timestamputc'] = \
            sensor_reading_latest_data['timestamputc'].apply(parse)
        sensor_reading_latest_data['timestampms'] = sensor_reading_latest_data[[
            'timestamputc']].apply(lambda x: x[0].timestamp(), axis=1)\
            .astype('int64') * 1000

        """ add new column in response which corresponds with indices from 
        self, sort, and make it the index column"""
        sensor_reading_latest_data['sensornumber'] = returned_sensor_numbers
        sensor_reading_latest_data = sensor_reading_latest_data.sort_values(
            by=['sensornumber'], inplace=False)
        sensor_reading_latest_data = sensor_reading_latest_data.set_index(
            ['sensornumber'])

        # add 'sensornumber' as a series AS WELL AS the index
        sensor_reading_latest_data['sensornumber'] = \
            sensor_reading_latest_data.index

        # add 'name' column for room name
        sensor_reading_latest_data['name'] = self.sensor_location_info['name']\
            .loc[sensor_reading_latest_data['sensornumber']]

        # Check for missing spaces and print names and numbers if one is found
        for i in all_possible_sensor_numbers:
            if i not in returned_sensor_numbers:
                print('Sensor number {}: {}. NO DATA RETURNED.'
                      .format(i, self.sensor_location_info['name'].loc[i]))

        print('Latest sensor readings acquired successfully from: {} of {} '
              'possible sensors.' .format(len(returned_sensor_numbers),
                                          len(all_possible_sensor_numbers)))

        return (sensor_reading_latest_data, returned_sensor_numbers)

    def plot_managed_spaces(self, managed_spaces=None,
                            managed_space_after_data=None):
        ''' Plot managed space data. Data from all managed spaces plotted onto 
        one axis. If 'managed_space_after_data' is included, historical data 
        can be plotted, else, API is called to retrieve real-time data to plot.

        Parameters
        ----------
        managed_spaces: int/list of ints
            Single number or list. Use:
            'chosen_numbers, chosen_names = \
                _choose_by_number(self.managed_space_info)'
            to get corresponding numbers.

        managed_space_after_data: list of dataframes.
            Corresponds to 'managed_space_after_data' output from
            self.managed_space_after()'.

        Returns
        -------
        Plots overlays of occupancy of managed spaces on a single axis.
        '''

        if managed_space_after_data is None and managed_spaces is None:
            managed_space_after_data, managed_spaces = \
                self.managed_space_after()
        elif managed_space_after_data is None:
            managed_space_after_data, _ = \
                self.managed_space_after(managed_space_numbers=managed_spaces)
        else:
            print('To plot directly from data, a list of managed space '
                  'numbers must also be provided.')

        if isinstance(managed_spaces, int):
            managed_spaces = [managed_spaces]

        print('\nPlotting managed space sensor data.')

        legend_labels = []

        for data, space_number in zip(managed_space_after_data,
                                      managed_spaces):
            if not any(data):
                print('Managed space number {}: {}. NO DATA RETURNED'.format(
                    space_number, self.managed_space_info['name']
                    .loc[space_number]))
                continue
            else:
                legend_labels.append(
                    self.managed_space_info['name'].loc[space_number])
                print('Managed space number {}: {}. Data Available. '
                      'Plotting chart.'
                      .format(space_number,
                              self.managed_space_info['name']
                                  .loc[space_number]))

            current_dataframe = data
            current_dataframe['rxtimestamputc'] = \
                pd.to_datetime(current_dataframe['rxtimestamputc'])
            current_dataframe = current_dataframe.set_index('rxtimestamputc')
            axes = current_dataframe['occupancy'].plot(marker='.',
                                                       alpha=0.5,
                                                       figsize=(12, 18),
                                                       linewidth=1,
                                                       markersize=2.5)

        try:
            axes
            axes.legend(legend_labels, loc='upper right')
            axes.yaxis.set_major_locator(MaxNLocator(integer=True))
            plt.xlabel('Time')
            plt.title('Occupancy of managed spaces')
            plt.ylabel('Occupancy')

            # Set formatter
            locator = mdates.AutoDateLocator(minticks=8, maxticks=14)
            formatter = mdates.ConciseDateFormatter(locator)
            axes.xaxis.set_major_locator(locator)
            axes.xaxis.set_major_formatter(formatter)
            plt.show()
        except:
            sys.exit('Could not plot - faulty sensor or no data returned')

    def plot_sensor_reading_after(self, sensor_numbers=None,
                                  sensor_reading_after_data=None):
        ''' Plot sensor data (after). Data from each sensor are plotted on
        separate axes. If 'sensor_reading_after_data' is included, historical 
        data can be plotted, else, API is called to retrieve real-time data to 
        plot.

        Parameters
        ----------
        sensor_numbers: int/list of ints
            Single number or list. Use:
            'chosen_numbers, chosen_names = \
                _choose_by_number(self.sensor_location_info)'
            to get corresponding numbers.

        sensor_reading_after_data: list dataframes.
            Corresponds to 'sensor_reading_after_data' output from
            self.sensor_reading_after()'.

        Returns
        -------
        A plot for each sensor displaying Occupancy, VOC, CO2, Temperature,
        Pressure, Humidity, Light Intensity, and Noise Levels.
        '''

        if sensor_reading_after_data is None and sensor_numbers is None:
            sensor_reading_after_data, sensor_numbers = \
                self.sensor_reading_after()
        elif sensor_reading_after_data is None:
            sensor_reading_after_data, _ = \
                self.sensor_reading_after(sensor_numbers=sensor_numbers)
        elif sensor_reading_after_data and sensor_numbers is None:
            print('To plot directly from data, a list of sensor numbers '
                  'must also be provided.')

        if isinstance(sensor_numbers, int):
            sensor_numbers = [sensor_numbers]

        print('\nPlotting sensor data.')

        labels_done = 0
        for data, sensor_number in zip(sensor_reading_after_data,
                                       sensor_numbers):
            if not any(data):
                print('Sensor number {}: {}. NO DATA RETURNED'
                      .format(sensor_number,
                              self.sensor_location_info['name']
                                  .loc[sensor_number]))
                continue
            else:
                print('Sensor number {}: {}. Data Available. Plotting chart.'
                      .format(sensor_number,
                              self.sensor_location_info['name']
                                  .loc[sensor_number]))
                # this section to obtain plot
                if labels_done == 0:
                    param_labels = ['occupancy', 'voc', 'co2', 'temperature',
                                    'pressure', 'humid', 'lux', 'noise']

                    plot_labels = ['Occupancy\n(n)', 'VOC\n(ppm?)',
                                   'CO2\n(ppm?)', 'Temperature\n(°C)',
                                   'Pressure\n(mBar)', 'Humidity\n(RH)',
                                   'Light Intensity\n(lux)',
                                   'Noise Levels\n(dB)']

                current_dataframe = data
                current_dataframe['timestamputc'] = \
                    pd.to_datetime(current_dataframe['timestamputc'])
                current_dataframe = current_dataframe.set_index(
                    'timestamputc')

                plot_title = str('Sensor readings (after) from sensor number '
                                 '{}: {}.'.format(sensor_number,
                                                  self.sensor_location_info['name']
                                                  .loc[sensor_number]))
                axes = current_dataframe[param_labels].plot(marker='.',
                                                            alpha=0.5,
                                                            figsize=(12, 26),
                                                            subplots=True,
                                                            linewidth=1,
                                                            markersize=2.5,
                                                            title=plot_title)

                for i, ax in enumerate(axes, start=0):
                    ax.set_ylabel(plot_labels[i], rotation='horizontal',
                                  fontsize=10, ha='right', va='baseline')

                plt.xlabel('Time')
                locator = mdates.AutoDateLocator(minticks=8, maxticks=14)
                formatter = mdates.ConciseDateFormatter(locator)
                ax.xaxis.set_major_locator(locator)
                ax.xaxis.set_major_formatter(formatter)
                plt.show()

    @staticmethod
    def _time_now():
        ''' Get the current time as ms time epoch'''
        return (int(round(time.time() * 1000)))

    @staticmethod
    def _make_empty_list(length):
        ''' Returns an empty list of length 'length'''
        list_for_output = []
        for index in range(0, length):
            list_for_output.append([])
        return (list_for_output)

    @staticmethod
    def _get_values_and_indexes(dataframe, column_name='name'):
        ''' Returns lists of values from column_name in dataframe and 
        corresponding index numbers.'''

        value_nums = list(dataframe.index)
        value_strings = list(dataframe[column_name])
        return (value_nums, value_strings)

    @staticmethod
    def _choose_by_number(dataframe_or_list, column_name='name'):
        ''' Takes user input to choose from a list using the index column name.

        Parameters
        ----------
        dataframe_or_list: panda dataframe or list
            The dataframe from the Scraper() object (e.g. scraper.room_info) 
            from which to choose, or a list. For lists, case column_name must 
            also be included.
        column_name: str, optional
            The index of the column in the dataframe, or description of the 
            list.

        Returns
        -------
        chosen_numbers: list of ints
            List of numbers corresponding to chosen names.
        chosen_names: list of strings
            List of names corresponding to chosen numbers.
        '''
        if isinstance(dataframe_or_list, list):
            if not column_name:
                print('To choose from list, column name variable must be '
                      'defined.')
            else:
                list_description = column_name
            list_of_numbers = list(range(1, len(dataframe_or_list) + 1))
            list_of_names = dataframe_or_list
        else:
            list_description = dataframe_or_list.index.name
            list_of_numbers, list_of_names = Scraper._get_values_and_indexes(
                dataframe_or_list, column_name)

        if len(list_of_numbers) == 1:
            chosen_numbers = list_of_numbers
            chosen_names = list_of_names
            print('Only one {} available, so number {}: \'{}\' was selected '
                  'by default.'.format(list_description,
                                       chosen_numbers[0],
                                       list_of_names[0]))
            return (chosen_numbers, chosen_names)

        print("\nAvailable:")
        for number, name in zip(list_of_numbers, list_of_names):
            print("{} {}: {}.".format(list_description, number, name))

        chosen_numbers = input(
            'Choose by number. Use the format:\n \'1\' for single, \'1, 2, 3\''
            'for multiple, or press enter for all.\n Use \'range()\' to return'
            ' a list (e.g.\'range(3,6)\' returns \'3,4,5\'):\n>>')

        if not chosen_numbers:
            chosen_numbers = list_of_numbers
            chosen_names = list_of_names
        else:
            chosen_names = []
            chosen_numbers = eval(chosen_numbers)

            if isinstance(chosen_numbers, int):
                chosen_numbers = [chosen_numbers]
            elif isinstance(chosen_numbers, range) or \
                    isinstance(chosen_numbers, tuple):
                chosen_numbers = list(chosen_numbers)

            for number in chosen_numbers:
                if number not in list_of_numbers or number <= 0:
                    sys.exit('\nBad index number {}.'.format(number))
                else:
                    chosen_names.append(
                        list_of_names[list_of_numbers.index(number)])

        print('\nChosen:')
        for (number, name) in zip(chosen_numbers, chosen_names):
            print('{} {}: {}.'.format(list_description, number, name))

        return (chosen_numbers, chosen_names)

    @staticmethod
    def _print_attributes(obj):
        ''' Print attributes of class object 'obj'.

        Parameters
        ----------
        ojb: class object

        Returns
        -------
        Prints attributes of 'obj'
        '''

        print('\nAttributes:\n')
        for attr in vars(obj):
            print("{}: {}\n".format(attr, getattr(obj, attr)))
