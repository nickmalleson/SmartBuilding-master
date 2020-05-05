# SmartBuilding

This repository is for accessing the API for the Connected Places Catapult 'Smart Building', acquiring data, storing it in a batabase, and plotting. The assumption is made that you are familiar with the Beringar API functions, and the sensors and layout. In the 'docs' folder, you can check 'api v1.6.pdf' for the API documentation, and 'UIC All Floor Plans1.pdf' for the layout of the building. 

'[scraper.py](./scraper.py)' is a module which can be used to login and access the API, and to retreive data for storage in variables. It also includes functions for plotting data.

'[scraperplot.py](./scraperplot.py)' is a script which allows for data to be plotted through interaction with the console.

See '[scraper_notebook.ipynb](./scraper_notebook.ipynb)' for a demonstration of how to use 'scraper.py' and 'scraperplot.py'.

'[create_database.sql](./create_database.sql)' is script for creating a database called 'database.db' using sqlite3.

'[database.py](./database.py)' is a script is run from the command line to populate the file 'database.db' created using 'create_database.sql'.

'[databaseplot.py](./databaseplot.py)' is a tool for plotting from the database ('database.db').

See '[databaseplot_notebook.ipynb](./databaseplot_notebook.ipynb)' for a demonstration of how to use 'databaseplot_notebook.ipynb'.


## Installing and Running

### Initialise and run '[scraper.py](./scraper.py)' 

The script requires login detail for functions to access the API. IMPORTANT: to log in automatically, place a .txt file named 'SmartBuildingParameters.txt' in a folder named 'SmartBuildingParameters' in this diretory. The file should contain the login details in the following format:

"username = user138
password = letmein"

In Python, import the module:

    import scraper

You can then assign an instance of the Scraper() class:

    scraper_instance = Scraper()

Data can then be retrieved from a specific time point using:

    sensor_reading_after, sensor_numbers = scraper_instance.sensor_reading_after(sensor_numbers=list_of_sensor_numbers, 
    timestamp_epoch_millisec=input_time_in_ms_epoch_format)

Or the most recent sensor readings using:

    sensor_reading_latest, sensor_numbers = scraper_instance.sensor_reading_latest()

### Create 'database.db' and populate it using '[database.py](./database.py)' 

'database.db' must be created using sqlite3. Install sqlite3. Then, from the command line, enter:

    sqlite3 TARGET_DIRECTORY\database.db < PATH_TO_FILE\create_database.sql

Replace TARGET_DIRECTORY and PATH_TO_FILE the directory containing 'create_database.sql'.

You can then use 'database.py' to insert data into the empty 'database.db', using 'scraper.py' to collect the data. Depending on the flags when the file is run, you can populate the database from the time the sensors were turned on, from a specific time point, or just add the most recent readings.

Navigate to the directory containing 'database.db' and database.py.
To insert all available data enter:

    python database.py -a

To insert the most recent data:

    python database.py -r

To populate from a specific time point enter;

    python database.py -f TIME_IN_MS_EPOCH_FORMAT

Replace TIME_IN_MS_EPOCH_FORMAT with the time you want to populate from (e.g.: '1588590000000')

### Plotting from the database using '[databaseplot.py](./databaseplot.py)'

'databaseplot.py' is a tool for plotting from the database. You can select the sensors you want to plot by sensor number, sensor name, room number, or room name. You can also specify the time period you want to plot, as well as the the parameters. It has arguments for overlaying the data when plotting multiple sensors or rooms, and can overlay all on the same plot, or keep sensors from the same room together. It also has an option to aggregate the data by taking mean of all parameters (except occupancy, which is calculated as sum) from all sensors in a room per minute.

In python, import the plotting function:

    from databaseplot import DatabasePlotter

You can then plot using the 'DatabasePlotter()' class and the 'plot_from_database()' function. To plot using the default settings, use the format:

    DatabasePlotter().plot_from_database()

Specify sensor numbers, or sensor names with the 'sensors' argument:

    DatabasePlotter().plot_from_database(sensors = [1, 4, 10, 12])

    DatabasePlotter().plot_from_database(sensors = ['0-Café-1', '0-Exhibition-Area-1', '2-Desks:229-232', 
    '2-Desks:233-240', '2-Desks:241-244'])

Specify room numbers or room names with the 'rooms' argument:
    
    DatabasePlotter().plot_from_database(rooms = [1, 2, 3])

    DatabasePlotter().plot_from_database(rooms = ['0-Café', '0-Exhibition-Area', '2-Open-Office']

Other arguments can be set as inputs:

        time_from   Default: first available
        time_to     Default: time now
        parameters  Default: all ['occupancy', 'voc', 'co2', 'temperature', 'pressure', 'humidity', 'lux', 
                                  'noise']
        overlay     Default: 1 - overlay plots from the differnet sensors
        aggregate   Default: 0 - do not aggregate
        seperate    Default: 1 - different plots for different rooms

For example:

    time_from = Scraper._time_now() - 604800000 # previous 24 hours

    DatabasePlotter().plot_from_database(rooms=[1,2,3], time_from=1588062521008, parameters=['occupancy', 'noise'], 
    aggregate = 1, overlay = 0)

Unset inputs are set to default.

You can also plot from the command line using the arguments 'sensors', 'rooms', or 'parameters', depending on what you want to choose from:

    DatabasePlotter.plot_from_database('sensors')

If you need, you can still set the parameters in the 'plot_from_database' function, and this way you are not prompted about these inputs.

Please contact me if you are having any problems with the scripts.

Thomas Richards
tcrichards1990@gmail.com