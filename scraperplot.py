# -*- coding: utf-8 -*-
"""
scraperlot.py

For retreiving and plotting data using the 'scraper.py' module.

Created on Wed Oct 30 15:11:00 2019

@author: Thomas Richards
"""
# import scraper.py
import scraper as scrp

# Run functions in get module
scraper = scrp.Scraper()

choices = input('What do you want to plot? Press enter for all. \n1. Managed '
                'space data\n2. Sensor reading data\n')

if not choices:
    chosen_space_numbers, chosen_space_names = \
        scrp.choose_by_number(scraper.managed_space_info, 'Managed space')
    scrp.plot_managed_spaces(scraper_instance=scraper,
                            managed_spaces=chosen_space_numbers)

    chosen_location_numbers, chosen_location_names = \
        scrp.choose_by_number(scraper.sensor_location_info, 'Sensor location')
    scrp.plot_sensor_reading_after(scraper_instance=scraper,
                                  sensor_numbers=chosen_location_numbers)
    scrp.plot_sensor_reading_last(scraper_instance=scraper,
                                 sensor_numbers=chosen_location_numbers)
elif choices:

    choices = eval(choices)

    if choices == 1:
        chosen_space_numbers, chosen_space_names = \
            scrp.choose_by_number(scraper.managed_space_info, 'Managed space')

        # NEED TO UPDATE THESE FUNCTIONS TO ta
        scrp.plot_managed_spaces(scraper_instance=scraper,
                                managed_spaces=chosen_space_numbers)
    elif choices == 2:
        chosen_location_numbers, chosen_location_names = \
            scrp.choose_by_number(scraper.sensor_location_info,
                                 'Sensor location')

        scrp.plot_sensor_reading_after(scraper_instance=scraper,
                                      sensor_numbers=chosen_location_numbers)
        scrp.plot_sensor_reading_last(scraper_instance=scraper,
                                     sensor_numbers=chosen_location_numbers)
else:
    print('Unknown input.')
