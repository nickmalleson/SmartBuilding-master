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


def get_login_info():
    ''' Get login username and password from locally stored parameter file.'''


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
        building_numbers, _ = get_lists_from_name_key(
            self.building_info)

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
            'https://console.beringar.co.uk/api/beta/building/',
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
            https://console.beringar.co.uk/api/beta/<function_name>/
        
        :param function_name: the name of the API function to call
        :return: the json returned by the response if successfull (a dict) or
            raise an IOError if the call failed.
        """
        url = 'https://console.beringar.co.uk/api/beta/{}/'.format(function_name)
        #print(url)
        response = r.get(url,auth=(self.username, self.password))
        status_code = response.status_code

        # Sucess code = 200, Failed = 400 (simplified).
        if 200 <= status_code < 300:
            # Response as OK.
            #print('\nAPI call successful')
            return response.json()
        # Failed if here
        print('API call failed with code: {}.'.format(status_code ))
        raise IOError("Call to the API failed ({})".format(status_code))
        

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



    def get_managed_space_info(self, building_numbers):
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
            managed_space_info.append(self._call_API(function_name))
            
            try:
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


    def managed_space_nrows(self,
                            managed_space_numbers=None,
                            timestamp_epoch_millisec=1000):
        ''' Get last ‘max_rows’ of managed space readings for a given managed
        space.

        Parameters
        ----------
        managed_space_numbers: int/list of ints
            Single number or list. Use:
            choose_by_number(self.managed_space_info, 'managed space')
            to get corresponding numbers.
        timestamp_epoch_millisec: int
            Desired number of rows.

        Returns
        -------
        managed_space_nrows_data: list of list of dictionaries. Each index will co-
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

        managed_space_nrows_data = []
        fail = 0
        succ = 0

        for num, i in enumerate(managed_space_numbers, start=0):
            space = self.managed_space_info[i-1]
            urlstr = str('https://console.beringar.co.uk/api/beta/managedspace/'
                         'spacelocation/{}/after/{}'
                         .format(space['id'], timestamp_epoch_millisec))
            response = r.get(urlstr, auth=(self.username,
                                           self.password))
            responsecheck = response.status_code
            managed_space_nrows_data.append(response.json())

            if not managed_space_nrows_data[num]:
                print('Managed space location number {}: {}. NO DATA RETURNED.'
                      .format(i, space['name']))
                fail += 1
            elif 200 >= responsecheck < 400:
                print('Managed space location number {}: {}. Successfully aquired'
                      ' {} rows of data. Input max_rows value: {}.'
                      .format(i, space['name'], len(managed_space_nrows_data[num]),
                              timestamp_epoch_millisec))
                succ += 1
            else:
                print('Managed space location number {}: {}. PROBLEM AQUIRING '
                      'DATA.' .format(i, space['name']))
                fail += 1

            managed_spaces = managed_space_numbers.copy()

        print('Data aquired from', succ + fail,
              'managed space locations. Succesful: {}. Failed: {}.\n'
              .format(succ, fail))

        return(managed_space_nrows_data, managed_spaces)


    def sensor_reading_after(self,
                             sensor_numbers=None,
                             timestamp_epoch_millisec=1000):
        ''' Get last ‘max_rows’ of sensor readings for a given sensor location.

        Parameters
        ----------
        sensor_numbers: int/list of ints
            Single number or list. Use:
            choose_by_number(self.sensor_location_info, 'sensor')
            to get corresponding numbers.
        timestamp_epoch_millisec: int
            Desired number of rows. Max = 1000.

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

        sensor_reading_after_data = []
        succ = 0
        fail = 0

        ''' Loop through all locations saving the the last nrows of each. Print wh-
        ether each location is successful.
        '''
        for num, i in enumerate(sensor_numbers, start=0):
            sensor = self.sensor_location_info[i-1]
            urlstr = str('https://console.beringar.co.uk/api/beta/sensorreading/'
                         'sensorlocation/{}/after/{}'
                         .format(sensor['id'], timestamp_epoch_millisec))
            response = r.get(urlstr, auth=(self.username,
                                           self.password))
            responsecheck = response.status_code
            sensor_reading_after_data.append(response.json())

            # Check whether data were returned.
            if not sensor_reading_after_data[num]:
                print('Sensor number {}: {}. NO DATA RETURNED.' .format(
                      sensor_numbers[num], sensor['name']))
                fail += 1
            elif 200 >= responsecheck < 400 and sensor_reading_after_data[num]:
                print('Sensor number {}: {}. Successfully aquired {} readings. '
                      'Input timestamp_epoch_millisec value: {}.' .format(
                          sensor_numbers[num], sensor['name'],
                          len(sensor_reading_after_data[num]),
                          timestamp_epoch_millisec))
                succ += 1
            else:
                print('Sensor number {}: {}. PROBLEM AQUIRING READING FROM '
                      'SENSOR.' .format(sensor_reading_after_data[num],
                                        sensor['name']))
                fail += 1

        if isinstance(sensor_numbers, range):
            sensor_numbers = list(sensor_numbers)
        sensor_list = sensor_numbers.copy()

        print("Aquired data from {} sensors. Succsessful: {}. Failed: {}.\n"
              .format(num+1, succ, fail))

        return(sensor_reading_after_data, sensor_list)


    def sensor_reading_last(self,
                            sensor_numbers=None,
                            timestamp_epoch_millisec=1000):
        ''' Get last ‘max_rows’ of sensor readings for a given sensor location.

        Parameters
        ----------
        sensor_numbers: int/list of ints
            Single number or list. Use:
            choose_by_number(self.sensor_location_info, 'sensor')
            to get corresponding numbers.
        timestamp_epoch_millisec: int
            Desired number of rows. Max = 1000.

        Returns
        -------
        sensor_reading_last_data: list of list of dictionaries.
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

        sensor_reading_last_data = []
        succ = 0
        fail = 0

        ''' Loop through all locations saving the the last nrows of each. Print wh-
        ether each location is successful.
        '''
        for num, i in enumerate(sensor_numbers, start=0):
            sensor = self.sensor_location_info[i-1]
            urlstr = str('https://console.beringar.co.uk/api/beta/sensorreading/'
                         'sensorlocation/{}/last/{}'
                         .format(sensor['id'], timestamp_epoch_millisec))
            response = r.get(urlstr, auth=(self.username,
                                           self.password))
            responsecheck = response.status_code
            sensor_reading_last_data.append(response.json())

            # Check whether data were returned.
            if not sensor_reading_last_data[num]:
                print('Sensor number {}: {}. NO DATA RETURNED.' .format(
                      sensor_numbers[num], sensor['name']))
                fail += 1
            elif 200 >= responsecheck < 400 and sensor_reading_last_data[num]:
                print('Sensor number {}: {}. Successfully aquired {} readings. '
                      'Input timestamp_epoch_millisec value: {}.' .format(
                          sensor_numbers[num], sensor['name'],
                          len(sensor_reading_last_data[num]),
                          timestamp_epoch_millisec))
                succ += 1
            else:
                print('Sensor number {}: {}. PROBLEM AQUIRING READING FROM '
                      'SENSOR.' .format(sensor_reading_last_data[num],
                                        sensor['name']))
                fail += 1

        if isinstance(sensor_numbers, range):
            sensor_numbers = list(sensor_numbers)
        sensor_list = sensor_numbers.copy()

        print("Aquired data from {} sensors. Succsessful: {}. Failed: {}.\n"
              .format(num+1, succ, fail))

        return(sensor_reading_last_data, sensor_list)


    def plot_managed_spaces(self, managed_spaces=None,
                            managed_space_nrows_data=None):
        ''' Plot managed space data. Data from all managed spaces plotted onto one
        axis. If 'managed_space_nrows_data' is included, historical data can be
        plotted, else, API is called to retrieve real-time data to plot.

        Parameters
        ----------
        managed_space_numbers: int/list of ints
            Single number or list. Use:
            choose_by_number(self.managed_space_info, 'managed space')
            to get corresponding numbers.

        managed_space_nrows_data: list of list of dictionaries.
            Corresponds to 'managed_space_nrows_data' output from
            managed_space_nrows()'.

        Returns
        -------
        Plots overlays of occupancy of managed spaces on a single axis.
        '''

        if managed_space_nrows_data is None and \
           managed_spaces is None:
            managed_space_nrows_data, managed_spaces = \
                self.managed_space_nrows()
        elif managed_space_nrows_data is None:
            managed_space_nrows_data, _ = \
                self.managed_space_nrows(managed_space_numbers=managed_spaces)
        else:
            print('To plot directly from data, a list of managed space numbers '
                  'must also be provided.')

        legendlabels = []

        for data, space_number in zip(managed_space_nrows_data,
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
                                  'Temperature\n(°C)', 'Pressure\n(mbars??)',
                                  'Humidity\n(RH??)', 'Light Intensity\n(lux)',
                                  'Noise Levels\n(dB??)']

                current_dataframe = pd.DataFrame(data)
                current_dataframe['rxtimestamputc'] =\
                    pd.to_datetime(current_dataframe['rxtimestamputc'])
                current_dataframe = current_dataframe.set_index('rxtimestamputc')

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


    def plot_sensor_reading_last(self, sensor_numbers=None,
                                 sensor_reading_last_data=None):
        ''' Plot sensor data (last). Data from each sensor are plotted on
        seperate axes. If 'sensor_reading_last_data' is included, historical data
        can be plotted, else, API is called to retrieve real-time data to plot.

        Parameters
        ----------
        sensor_numbers: int/list of ints
            Single number or list. Use:
            choose_by_number(self.get_sensor_location_info, 'sensor')
            to get corresponding numbers.
        sensor_reading_last_data: list of list of dictionaries.
            Corresponds to 'sensor_reading_last_data' output from
            sensor_reading_last()'.

        Returns
        -------
        A plot for each sensor displaying Occupancy, VOC, CO2, Temperature,
        Pressure, Humidity, Light Intensity, and Noise Levels.
        '''

        if sensor_reading_last_data is None and sensor_numbers is None:
            sensor_reading_last_data, sensor_numbers = \
                self.sensor_reading_last()
        elif sensor_reading_last_data is None:
            sensor_reading_last_data, _ = \
                 self.sensor_reading_last(sensor_numbers=sensor_numbers)
        elif sensor_reading_last_data and sensor_numbers is None:
            print('To plot directly from data, a list of sensor location numbers '
                  'must also be provided.')

        labelsdone = 0
        for data, sensor_number in zip(sensor_reading_last_data,
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
                                  'Temperature\n(°C)', 'Pressure\n(mbars??)',
                                  'Humidity\n(RH??)', 'Light Intensity\n(lux)',
                                  'Noise Levels\n(dB??)']

                current_dataframe = pd.DataFrame(data)
                current_dataframe['rxtimestamputc'] =\
                    pd.to_datetime(current_dataframe['rxtimestamputc'])
                current_dataframe = current_dataframe.set_index('rxtimestamputc')

                axtitle = str('Sensor readings (last) from sensor number {}: {}.'
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