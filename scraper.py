# -*- coding: utf-8 -*-
'''
scraper.py

Script for accesing the API of the Connected Places Smart Building using python
and the "requests" library.

Created on Thu Oct 17 16:11:16 2019

@author: Thomas Richards

'''
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


def make_empty_list(length):
    ''' Returns an empty list of length 'length'''
    list_for_output = []
    for index in range(0, length):
        list_for_output.append([])
    return(list_for_output)


def get_login_info():
    ''' Get login username and password from locally stored parameter file.'''

    # Look in the folder in the directory above the present working directory
    parameter_file_path = '../SmartBuildingParameters/'
    parameter_file_name = 'SmartBuildingParameters.txt'
    parameter_file = open(parameter_file_path + parameter_file_name)
    params = {}
    for line in parameter_file:
        line = line.strip()
        key_value = line.split(' = ')
        params[key_value[0].strip()] = key_value[1].strip()
    username = params['username']
    password = params['password']
    return(username, password)


def get_key_names_and_values(key_string, list_of_dicts):
    ''' Returns lists of values and corresponding numbers of given key.

    Parameters
    ----------
    key_string: str
        The desired key from a dictionary.
    list_of_dicts: dict
        Dictionary or list of dictionaries.

    Returns
    -------
    value_nums: list of ints
        Index in dictionary + 1
    value_strings: list of strings
        Corresponding names.
    '''

    value_nums = []
    value_strings = []

    for num, dictionary in enumerate(list_of_dicts):
        value_nums.append(num+1)
        value_strings.append(dictionary[key_string])
    return(value_nums, value_strings)


def print_key_names_and_values(key_string, key_nums, key_values):
    ''' Prints lists of values and corresponding numbers of given key.

    Parameters
    ----------
    key_string: str
        A short description of values (e.g. 'Building').
    value_nums: list of ints
        'value_nums' output from get_key_names_and_values().
    value_strings: list of strings
        Dictionary or list of dictionaries.

    Returns
    -------
    value_nums: list of ints
        Index in dictionary + 1
    '''

    for num, value in zip(key_nums, key_values):
        print('{} number {}: {}.'.format(key_string, num, value))


def get_lists_from_name_key(list_of_dicts):
    ''' Get lists of numbers and corresponding key 'names' from a list of 
    dicts.

    Parameters
    ----------
    list_of_dicts: list of dictionaries
        The list of dictionaries from the Scraper() object 
        (e.g. scraper.room_info) from which to obtain a list of 'name' keys.

    Returns
    -------
    list_of_numbers: list of ints
        List of numbers corresponding to the names in 'list_of_names'.
    list_of_names: list of strings
        List of names corresponding to the numbers in 'list_of_numbers.
    '''

    list_of_numbers, list_of_names = get_key_names_and_values('name',
                                                              list_of_dicts)
    return(list_of_numbers, list_of_names)


def choose_by_number(list_of_dicts, list_description):
    ''' Takes user input to choose from a list.

    Parameters
    ----------
    list_of_dicts: list of dictionaries
        The list of dictionaries from the Scraper() object 
        (e.g. scraper.room_info) from which to obtain a list using the key: 
        'name'.

    Returns
    -------
    chosen_numbers: list of ints
        List of numbers corresponding to chosen names.
    chosen_names: list of strings
        List of names corresponding to chosen numbers.
    '''

    list_of_numbers, list_of_names = get_lists_from_name_key(list_of_dicts)

    if len(list_of_numbers) == 1:
        chosen_numbers = list_of_numbers
        chosen_names = list_of_names
        print('Only one {} available, so number {}: \'{}\' was selected '
              'by default.' .format(list_description,
                                    chosen_numbers[0],
                                    list_of_names[0]))
        return(chosen_numbers, chosen_names)

    print("\nAvailable:")
    for number, name in zip(list_of_numbers,
                            list_of_names):
        print("{} {}: {}.".format(list_description, number, name))

    chosen_numbers = input(
        'Choose by number. Use the format:\n \'1\' for single, \'1, 2, 3\''
        'for multiple, or press enter for all.\n Use \'range()\' to return a'
        'list (e.g.\'range(3,6)\' returns \'3,4,5\'):')

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
                sys.exit('\nBad index number {}.' .format(number))
            else:
                chosen_names.append(list_of_names[number-1])

    print('\nChosen:')
    for (number, name) in zip(chosen_numbers, chosen_names):
        print('{} {}: {}.'.format(list_description, number, name))
    print('\n')

    return(chosen_numbers, chosen_names)


class Scraper():
    '''Obtains login details and stores data associated with the account in co-
    stant variables.
    '''

    def __init__(self):
        self.username, self.password, self.building_info = Scraper._login()

        # To get list of building numbers for 'get_managed_space_info()' input.
        building_numbers, _ = get_lists_from_name_key(self.building_info)

        # TODO: should all these functions also return a list of corresponding numbers?
        self.contract_info = self.get_contract_info()
        print("Contract data retrieved successfully")
        self.customer_info = self.get_customer_info()
        print("Customer data retrieved successfully")
        self.managed_space_info = self.get_managed_space_info(building_numbers)
        print("Managed space data retrieved successfully")
        self.sensor_location_info = self.get_sensor_location_info()
        print("Sensor locations retrieved successfully")
        self.room_info = self.get_room_info()
        print("Room information retrieved successfully")

    @staticmethod
    def _login():
        '''Obtain and check username and password for Smart Building API.

        Username and password are obtained by user input. These are then check-
        ed by using the 'building' function on the API, and if successful, use-
        rname, password, and the output of the API 'building' function are ret-
        urned.

        '''

        # Prompt to enter username or press enter to use saved details
        username = input(
            "Enter username or press enter to log in as 'yanjiedong':")

        # if enter was pressed use saved username and password
        if username == '':
            username, password = get_login_info()
        else:
            '''Enter password manually. Password is hidden but only in externa-
            l console if using Spyder.'''
            password = getpass.getpass(prompt='Password:')

        # Use 'building' API function to check username and password.
        response = r.get(
            'https://console.beringar.co.uk/api/building/',
            auth=(username, password))
        responsecheck = response.status_code

        # Sucess code = 200, Failed = 400 (simplified).
        if 200 <= responsecheck < 300:
            # Obtain building name from response
            building_info = response.json()
            print('\nLogin successful.\nBuilding info aquired successfully '
                  'from {}.' .format(building_info[0]['name']))
        else:
            print('Page not found or no building associated with account.')
        return(username, password, building_info)

    def _call_API(self, function_name):
        """Call the API, inserting 'function_name' into the URL. E.g.:
            https://console.beringar.co.uk/api/<function_name>/

        :param function_name: the name of the API function to call
        :return: the json returned by the response if successfull (a dict) or
            raise an IOError if the call failed.
        """
        url = 'https://console.beringar.co.uk/api/{}'.format(function_name)
        # print(url)
        response = r.get(url, auth=(self.username, self.password))
        status_code = response.status_code

        # Sucess code = 200, Failed = 400 (simplified).
        if 200 <= status_code < 300:
            # Response as OK.
            #print('\nAPI call successful')
            return response.json()
        # Failed if here
        print('API call failed with code: {}.'.format(status_code))
        raise IOError("Call to the API failed ({}) on url: '{}'".format(
            status_code, url))

    def get_contract_info(self):
        '''Get all contract info associated with account.'''
        return(self._call_API("contract"))

    def get_customer_info(self):
        '''Get all customer info associated with account.'''
        return(self._call_API("customer"))

    def get_sensor_location_info(self):
        '''Get all sensor location info associated with your account.'''
        return(self._call_API("sensorlocation"))

    def get_room_info(self):
        '''Get all room info associated with your account.'''
        return(self._call_API("room"))

    def get_managed_space_info(self, building_numbers=1):
        ''' Get all managed spaces associated with your account.

        Parameters
        ----------
        building_numbers: int, or list of ints
            Integer or list of integers corresponding to a building number
            from the output of:
            building_numbers, _ = get_lists_from_name_key(self.building_info)

        Returns
        -------
        managed_space_info: list of dictionaries (if one building in list), or
            list of list of dictionaries (if >1 building in list_of_building_n-
            umbers).
        '''

        if isinstance(building_numbers, int):
            building_numbers = [building_numbers]

        # To count successful and failed retrievals
        succ = 0
        fail = 0

        managed_space_info = []

        for i in building_numbers:
            # Construct the name of the function to be embedded into the
            # API URL
            building_id = self.building_info[i-1]['id']
            function_name = 'managedspace/building/{0}'.format(building_id)

            try:
                managed_space_info.append(self._call_API(function_name))
                if len(building_numbers) == 1:
                    print('Managed space info aquired successfully from: {}. '
                          'Output format is: \'managed_space_info'
                          '[a]\', where \'a\' is the first space.'
                          .format(self.building_info[i-1]['name']))
                    managed_space_info = managed_space_info[0]
                    return(managed_space_info)
                else:
                    print("'Aquired managed space info from building: '{}'."
                          .format(self.building_info[i-1]['name']))
                    succ += 1
            except Exception as e:
                print('Problem aquiring managed space info from: {}. Error: {}'
                      .format(self.building_info[i-1]['name']), str(e))
                fail += 1

        print('Managed space info aquired from {} building. Successful: {}. '
              'Failed: {}.\nOutput format is: \'managed_space_info[b][a]\', '
              'where \'b\' is the building and \"a\" is the space.' .format(
                  succ + fail, succ, fail))

        return(managed_space_info)

    def managed_space_after(self,
                            managed_space_numbers=None,
                            timestamp_epoch_millisec=None):
        ''' Get last ‘max_rows’ of managed space readings for a given managed
        space.

        Parameters
        ----------
        managed_space_numbers: int/list of ints
            Single number or list. Use:
            choose_by_number(self.managed_space_info, 'managed space')
            to get corresponding numbers.
        timestamp_epoch_millisec: int
            A time in ms epoch. Returns data from this time and includes up to
            1000 time points (one per minute). Default 1100 (will usually return 
            1000 rows of data for each available sensor).

        Returns
        -------
        managed_space_after_data: list of list of dictionaries. Each index will co-
            rrelate to the managed space number in the same index in 'managed_spac-
            e_list'.
        managed_spaces: list of ints
            The same as 'managed_space_numbers'.

        '''
        all_managed_spaces_numbers = \
            list(range(1, len(self.managed_space_info)+1))

        if isinstance(managed_space_numbers, int):
            managed_space_numbers = [managed_space_numbers]

        if managed_space_numbers is None:
            managed_space_numbers = \
                all_managed_spaces_numbers

        if not any(i in managed_space_numbers
                   for i in all_managed_spaces_numbers):
            sys.exit('\nBad index in input list.')

        """ Default time is 1100 minutes from when call was made. This is usually
        enough to get 1000 data points for each sensor. """
        if timestamp_epoch_millisec is None:
            timestamp_epoch_millisec = time_now()-66000000

        # Convert input time to ISO format
        input_time = \
            dt.datetime.utcfromtimestamp(
                int(timestamp_epoch_millisec/1000)).isoformat()

        print('Ms time epoch used for input: {}. Input in ISO format: {}'
              .format(timestamp_epoch_millisec, input_time))

        managed_space_after_data = []
        fail = 0
        succ = 0

        for num, i in enumerate(managed_space_numbers, start=0):
            space = self.managed_space_info[i-1]
            function_name = "beta/managedspace/spacelocation/{}/after/{}".format(
                space['id'], timestamp_epoch_millisec)

            try:
                response = self._call_API(function_name)
                managed_space_after_data.append(response)

                if not managed_space_after_data[num]:
                    print('Managed space location number {}: {}. NO DATA RETURNED.'
                          .format(i, space['name']))
                    fail += 1
                else:
                    print('Managed space location number {}: {}. Successfully aquired'
                          ' {} rows of data.'
                          .format(i, space['name'], len(managed_space_after_data[num])))
                    succ += 1
            except Exception as e:
                print('Managed space location number {}: {}. PROBLEM AQUIRING '
                      'DATA. Error: {}' .format(i, space['name'], str(e)))
                fail += 1

            managed_spaces = managed_space_numbers.copy()

        print('Data aquired from {} managed space location(s). Succesful: {}. Failed: {}.\n'
              .format(succ + fail, succ, fail))

        return(managed_space_after_data, managed_spaces)

    def managed_space_latest(self, building_numbers=1):
        ''' Get latest sensor reading from managed spaces readings for a given building. 
        Since the API call returns a list which excludes non-responsive sensors, this 
        function builds a list of all sensors from self.managed_space_info and leaves empty
        indexes when sensors are unresponsive.

        Parameters
        ----------
        building_numbers: int/list of ints
            Single number or list. Use:
            managed_space_numbers, _ = choose_by_number(self.building_info, 'managed space')
            to get corresponding numbers.

        Returns
        -------
        managed_space_latest_data: list of list of dictionaries. Output format depends on
            number of indicies in 'building_numbers' input. 

            If building_numbers has only one index or default is used, format is:
            'managed_space_latest_data[a]', where 'a' is the first space.'

            If building_numbers has multiple indicies, format is:         
            'managed_space_latest_data[b][a]', where 'b' is the building number 
            and 'a' is the space.

        all_space_numbers: list of ints
            Complete list of managed space numbers associated with building number.

        '''
        # if only one building is input, put it in list so the function can deal with it
        if isinstance(building_numbers, int):
            building_numbers = [building_numbers]

        # empty lists for outputs and counters for success/failed data retrieval from BUILDINGS
        managed_space_latest_data = []
        all_space_numbers = []
        fail = 0
        succ = 0

        # loop through building numbers listed in input
        for i in building_numbers:
            # Construct the name of the function to be embedded into the
            # API URL
            current_building_id = self.building_info[i-1]['id']
            current_building_name = self.building_info[i-1]['name']
            current_space_numbers, _ = get_lists_from_name_key(
                self.managed_space_info)

            function_name = "managedspace/latest/building/{}".format(
                current_building_id)

            ''' API call only returns working sensors. Following variables are needed
            to populate a list including ALL sensors for output current_space_numbers'''
            _, all_space_ids = get_key_names_and_values(
                'id', self.managed_space_info)
            _, all_space_names = get_key_names_and_values(
                'name', self.managed_space_info)

            # this is used to store data for current building
            output_for_current_building = make_empty_list(
                len(current_space_numbers))

            # try the API call for the current building, except if fails
            try:
                ''' the 'response' variable will not include non-responsive sensors so will 
                return a list shorter than total number of sensors in self.managed_space_info'''
                response = self._call_API(function_name)

                ''' take the output and put it into 'output_for_current_building', which has 
                empty indices for non-responsive sensors'''
                for space in response:
                    space_index = all_space_ids.index(space['managedspace'])
                    ''' put output in index which corresponds to id and number from 
                    self.managed_space_info'''
                    output_for_current_building[space_index] = space

                ''' check for empty indices and throw an error showing the corresponding name if
                one is found'''
                for check in current_space_numbers:
                    if not output_for_current_building[check-1]:
                        space_name = all_space_names[check-1]
                        print('Managed space location number {}: {}. NO DATA RETURNED.'
                              .format(check, space_name))

                # for the current building, fill the relevant output variables
                managed_space_latest_data.append(output_for_current_building)
                all_space_numbers.append(current_space_numbers)

                # if there is only one building, explain output format, return variables and end here
                if len(building_numbers) == 1:
                    print('Latest managed space readings aquired successfully from: {}. '
                          'Output format is: \'managed_space_latest_data[a]\', where \'a\' is the first space.'
                          .format(self.building_info[i-1]['name']))
                    return(managed_space_latest_data[i-1], all_space_numbers[i-1])
                # or continue to the next building...
                else:
                    print('Successfully aquired latest managed space data from building number {}: {}.'
                          .format(i, current_building_name))
                    succ += 1
                    managed_space_latest_data[i -
                                              1] = output_for_current_building
                    all_space_numbers[i-1] = current_space_numbers

            # if the API call fails, state this and move to next
            except Exception as e:
                print('Could not aquire latest managed space data from building number {}: {}.'
                      ' PROBLEM AQUIRING DATA. Error: {}' .format(i, current_building_name, str(e)))
                fail += 1

        # print summary if there were multiple buildings
        print('Latest managed space readings aquired from {} buildings. Successful: {}.'
              ' Failed: {}.\nOutput format is: \'managed_space_latest_data[b][a]\', where \'b\''
              ' is the building number and \'a\' is the space.'
              .format(succ + fail, succ, fail))

        return(managed_space_latest_data, all_space_numbers)

    def sensor_reading_after(self,
                             sensor_numbers=None,
                             timestamp_epoch_millisec=None):
        ''' Get last ‘max_rows’ of sensor readings for a given sensor location.

        Parameters
        ----------
        sensor_numbers: int/list of ints
            Single number or list. Use:
            choose_by_number(self.sensor_location_info, 'sensor')
            to get corresponding numbers.
        timestamp_epoch_millisec: int
            A time in ms epoch. Returns data from this time and includes up to
            1000 time points (one per minute). Default 1100 (will usually return 
            1000 rows of data for each available sensor).

        Returns
        -------
        sensor_reading_after_data: list of list of dictionaries.
            Each index will correspond with the sensor location number in the same
            index in 'sensor_numbers'.
        sensor_list: list of ints
            The same as 'sensor_numbers'.
        '''

        all_sensor_numbers = \
            list(range(1, len(self.sensor_location_info)+1))

        # Converts int to dict if only one sensor is inputted.
        if isinstance(sensor_numbers, int):
            sensor_numbers = [sensor_numbers]

        if sensor_numbers is None:
            sensor_numbers = \
                list(range(1, len(self.sensor_location_info)+1))

        if not any(i in sensor_numbers for i in all_sensor_numbers):
            sys.exit('\nBad index in input list.')

        """ Default time is 1100 minutes before call was made. This is usually
        enough to get 1000 data points for each sensor. """
        if timestamp_epoch_millisec is None:
            timestamp_epoch_millisec = time_now()-66000000

        # Convert input time to ISO format
        input_time = \
            dt.datetime.utcfromtimestamp(
                int(timestamp_epoch_millisec/1000)).isoformat()

        print('Ms time epoch used for input: {}. Input in ISO format: {}'
              .format(timestamp_epoch_millisec, input_time))

        sensor_reading_after_data = []
        succ = 0
        fail = 0

        ''' Loop through all locations saving the the last nrows of each. Print wh-
        ether each location is successful.
        '''
        for num, i in enumerate(sensor_numbers, start=0):
            sensor = self.sensor_location_info[i-1]
            function_name = "beta/sensorreading/sensorlocation/{}/after/{}".format(
                            sensor['id'], timestamp_epoch_millisec)

            try:
                response = self._call_API(function_name)
                sensor_reading_after_data.append(response)

                # Check whether data were returned.
                if not sensor_reading_after_data[num]:
                    print('Sensor number {}: {}. NO DATA RETURNED.' .format(
                          sensor_numbers[num], sensor['name']))
                    fail += 1
                else:
                    print('Sensor number {}: {}. Successfully aquired {} readings. '
                          .format(sensor_numbers[num], sensor['name'],
                                  len(sensor_reading_after_data[num])))
                    succ += 1
            except Exception as e:
                print('Sensor number {}: {}. PROBLEM AQUIRING READING FROM '
                      'SENSOR. Error: {}' .format(sensor_reading_after_data[num],
                                                  sensor['name'], str(e)))
                fail += 1

        if isinstance(sensor_numbers, range):
            sensor_numbers = list(sensor_numbers)
        sensor_list = sensor_numbers.copy()

        print("Aquired data from {} sensor(s). Succsessful: {}. Failed: {}.\n"
              .format(num+1, succ, fail))

        return(sensor_reading_after_data, sensor_list)

    def sensor_reading_latest(self, building_numbers=1):
        ''' Get latest sensor reading from sensors of a given building. Since the 
        API call returns a list which excludes non-responsive sensors, this function 
        builds a list of all sensors from self.sensor_location_info and leaves empty
        indexes when sensors are unresponsive.

        Parameters
        ----------
        building_numbers: int/list of ints
            Single number or list. Use:
            sensor_reading_numbers, _ = choose_by_number(self.building_info, 'name')
            to get corresponding numbers.

        Returns
        -------
        sensor_reading_latest_data: list of list of dictionaries. Output format depends on
            number of indicies in 'building_numbers' input. 

            If building_numbers has only one index or default is used, format is:
            'sensor_reading_latest_data[a]', where 'a' is the first sensor.'

            If building_numbers has multiple indicies, format is:         
            'sensor_reading_latest_data[b][a]', where 'b' is the building number 
            and 'a' is the sensor.

        all_sensor_numbers: list of ints
            Complete list of sensor numbers associated with building number.

        '''
        # if only one building is input, put it in list so the function can deal with it
        if isinstance(building_numbers, int):
            building_numbers = [building_numbers]

        # empty lists for outputs and counters for success/failed data retrieval from BUILDINGS
        sensor_reading_latest_data = []
        all_sensor_numbers = []
        fail = 0
        succ = 0

        # loop through building numbers listed in input
        for i in building_numbers:
            # Construct the name of the function to be embedded into the
            # API URL
            current_building_id = self.building_info[i-1]['id']
            current_building_name = self.building_info[i-1]['name']
            current_sensor_numbers, _ = get_lists_from_name_key(
                self.sensor_location_info)

            function_name = "sensorreading/latest/building/{}".format(
                current_building_id)

            ''' API call only returns working sensors. Following variables are needed
            to populate a list including ALL sensors for output current_sensor_numbers'''
            _, all_sensor_ids = get_key_names_and_values(
                'id', self.sensor_location_info)
            _, all_sensor_names = get_key_names_and_values(
                'name', self.sensor_location_info)

            # this is used to store data for current building
            output_for_current_building = make_empty_list(
                len(current_sensor_numbers))

            # try the API call for the current building, except if fails
            try:
                ''' the 'response' variable will not include non-responsive sensors so will 
                return a list shorter than total number of sensors in self.sensor_reading_info'''
                response = self._call_API(function_name)

                ''' take the output and put it into 'output_for_current_building', which has 
                empty indices for non-responsive sensors'''
                for sensor in response:
                    sensor_index = all_sensor_ids.index(
                        sensor['sensorlocation'])
                    ''' put output in index which corresponds to id and number from 
                    self.sensor_location_info'''
                    output_for_current_building[sensor_index] = sensor

                ''' check for empty indices and throw an error showing the corresponding name if
                one is found'''
                for check in current_sensor_numbers:
                    if not output_for_current_building[check-1]:
                        sensor_name = all_sensor_names[check-1]
                        print('Sensor location number {}: {}. NO DATA RETURNED.'
                              .format(check, sensor_name))

                # for the current building, fill the relevant output variables
                sensor_reading_latest_data.append(output_for_current_building)
                all_sensor_numbers.append(current_sensor_numbers)

                # if there is only one building, explain output format, return variables and end here
                if len(building_numbers) == 1:
                    print('Latest sensor readings aquired successfully from: {}. '
                          'Output format is: \'sensor_reading_latest_data[a]\', where \'a\' is the first sensor.'
                          .format(self.building_info[i-1]['name']))
                    return(sensor_reading_latest_data[i-1], all_sensor_numbers[i-1])
                # or continue to the next building...
                else:
                    print('Successfully aquired latest sensor data from building number {}: {}.'
                          .format(i, current_building_name))
                    succ += 1
                    sensor_reading_latest_data[i -
                                               1] = output_for_current_building
                    all_sensor_numbers[i-1] = current_sensor_numbers

            # if the API call fails, state this and move to next
            except Exception as e:
                print('Could not aquire latest sensor data from building number {}: {}.'
                      ' PROBLEM AQUIRING DATA. Error: {}' .format(i, current_building_name, str(e)))
                fail += 1

        # print summary if there were multiple buildings
        print('Latest sensor readings aquired from {} buildings. Successful: {}.'
              ' Failed: {}.\nOutput format is: \'sensor_reading_latest_data[b][a]\', where \'b\''
              ' is the building number and \'a\' is the sensor.'
              .format(succ + fail, succ, fail))

        return(sensor_reading_latest_data, all_sensor_numbers)

    def plot_managed_spaces(self, managed_spaces=None,
                            managed_space_after_data=None):
        ''' Plot managed space data. Data from all managed spaces plotted onto one
        axis. If 'managed_space_after_data' is included, historical data can be
        plotted, else, API is called to retrieve real-time data to plot.

        Parameters
        ----------
        managed_space_numbers: int/list of ints
            Single number or list. Use:
            choose_by_number(self.managed_space_info, 'managed space')
            to get corresponding numbers.

        managed_space_after_data: list of list of dictionaries.
            Corresponds to 'managed_space_after_data' output from
            managed_space_after()'.

        Returns
        -------
        Plots overlays of occupancy of managed spaces on a single axis.
        '''

        if managed_space_after_data is None and \
           managed_spaces is None:
            managed_space_after_data, managed_spaces = \
                self.managed_space_after()
        elif managed_space_after_data is None:
            managed_space_after_data, _ = \
                self.managed_space_after(managed_space_numbers=managed_spaces)
        else:
            print('To plot directly from data, a list of managed space numbers '
                  'must also be provided.')

        if isinstance(managed_spaces, int):
            managed_spaces = [managed_spaces]

        legendlabels = []

        for data, space_number in zip(managed_space_after_data,
                                      managed_spaces):
            if not data:
                print('Managed space number {}: {}. NO DATA RETURNED'.format(
                    space_number, self.managed_space_info[space_number-1]['name']))
                continue
            else:
                legendlabels.append(
                    self.managed_space_info[space_number-1]['name'])
                print('Managed space number {}: {}. Data Available. '
                      'Plotting chart.'
                      .format(space_number,
                              self.managed_space_info[space_number-1]
                              ['name']))

            currentdataframe = pd.DataFrame(data)
            currentdataframe['rxtimestamputc'] = \
                pd.to_datetime(currentdataframe['rxtimestamputc'])
            currentdataframe = currentdataframe.set_index('rxtimestamputc')
            axes = currentdataframe['occupancy'].plot(marker='.',
                                                      alpha=0.5, figsize=(12, 18),
                                                      linewidth=1, markersize=2.5)

        try:
            axes
            axes.legend(legendlabels, loc='upper right')
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
            sys.exit('Could not plot - faulty sensor or not data returned')
        print('\n')

    def plot_sensor_reading_after(self, sensor_numbers=None,
                                  sensor_reading_after_data=None):
        ''' Plot sensor data (after). Data from each sensor are plotted on
        seperate axes. If 'sensor_reading_after_data' is included, historical data
        can be plotted, else, API is called to retrieve real-time data to plot.

        Parameters
        ----------
        sensor_numbers: int/list of ints
            Single number or list. Use:
            choose_by_number(self.get_sensor_location_info, 'sensor')
            to get corresponding numbers.

        sensor_reading_after_data: list of list of dictionaries.
            Corresponds to 'sensor_reading_after_data' output from
            sensor_reading_after()'.

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
            print('To plot directly from data, a list of sensor location numbers '
                  'must also be provided.')

        if isinstance(sensor_numbers, int):
            sensor_numbers = [sensor_numbers]

        labelsdone = 0
        for data, sensor_number in zip(sensor_reading_after_data,
                                       sensor_numbers):
            if not data:
                print('Sensor number {}: {}. NO DATA RETURNED'
                      .format(sensor_number,
                              self.sensor_location_info[sensor_number-1]['name']))
                continue
            else:
                print('Sensor number {}: {}. Data Available. Plotting chart.'
                      .format(sensor_number,
                              self.sensor_location_info[sensor_number-1]["name"]))
                # this section to obtain plot
                if labelsdone == 0:
                    paramlabels = []
                    for label in data[0].keys():
                        if isinstance(data[0][label], int)\
                                or isinstance(data[0][label], float):
                            paramlabels.append(label)
                    del paramlabels[10], paramlabels[9], paramlabels[0]
                    plotlabels = ['Occupancy\n(n)', 'VOC\n(ppm?)', 'CO2\n(ppm?)',
                                  'Temperature\n(°C)', 'Pressure\n(mBar)',
                                  'Humidity\n(RH)', 'Light Intensity\n(lux)',
                                  'Noise Levels\n(dB)']

                current_dataframe = pd.DataFrame(data)
                current_dataframe['rxtimestamputc'] =\
                    pd.to_datetime(current_dataframe['rxtimestamputc'])
                current_dataframe = current_dataframe.set_index(
                    'rxtimestamputc')

                axtitle = str('Sensor readings (after) from sensor number {}: {}.'
                              .format(sensor_number,
                                      self.sensor_location_info[sensor_number-1]['name']))
                axes = current_dataframe[paramlabels].plot(marker='.', alpha=0.5,
                                                           figsize=(12, 26),
                                                           subplots=True,
                                                           linewidth=1,
                                                           markersize=2.5,
                                                           title=axtitle)

                for i, ax in enumerate(axes, start=0):
                    ax.set_ylabel(plotlabels[i], rotation='horizontal',
                                  fontsize=10, ha='right', va='baseline')

                plt.xlabel('Time')
                ''' ax.set_title("Sensor readings from sensor number {}: {}."
                .format(sensorno, sensorlocationdata[sensorno-1]['name']),
                loc='center') # set formatter '''
                locator = mdates.AutoDateLocator(minticks=8, maxticks=14)
                formatter = mdates.ConciseDateFormatter(locator)
                ax.xaxis.set_major_locator(locator)
                ax.xaxis.set_major_formatter(formatter)
                plt.show()
        print('\n')


def print_attributes(obj):
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
        print("{}: {}\n" .format(attr, getattr(obj, attr)))
