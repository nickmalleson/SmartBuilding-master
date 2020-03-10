--Create the database used for the real-time building data analysis

-- First turn foreign key constraints on (this is SQLite specific, in most RDMS's this is on by default)
PRAGMA foreign_keys = ON;

CREATE TABLE buildings (
	building_id VARCHAR(255) PRIMARY KEY,
	building_number INTEGER,
	building_name VARCHAR(255)
);

-- A table for rooms

CREATE TABLE rooms (
	room_id VARCHAR(255) PRIMARY KEY,
	room_number INTEGER,
	room_name VARCHAR(255),
	building_id VARCHAR(255) NOT NULL, --(maybe this isn't necessary?)
	building_number INTEGER,
	building_name VARCHAR(255),
	FOREIGN KEY (building_id) REFERENCES buildings(building_id)
	FOREIGN KEY (building_number) REFERENCES buildings(building_number)
	FOREIGN KEY (building_name) REFERENCES buildings(building_name)
);

--A table for sensors

CREATE TABLE sensors (
	sensor_id VARCHAR(255) PRIMARY KEY,
	sensor_number INTEGER,
	sensor_name VARCHAR(255),
	room_id VARCHAR(255),
	room_name VARCHAR(255),
	FOREIGN KEY (room_id) REFERENCES rooms(room_id),
	FOREIGN KEY (room_name) REFERENCES rooms(room_name)
);

-- A table for sensor readings

CREATE TABLE sensor_readings(
	sensor_reading_id INTEGER PRIMARY KEY AUTOINCREMENT, -- we always need a PK, but in this case we don't actually care what it is
	sensor_number INTEGER,
	sensor_name VARCHAR(255),
	co2 INTEGER,
	humidity FLOAT,
	lux INTEGER,
	noise INTEGER,
	occupancy INTEGER,
	pressure INTEGER,
	sensorlocation VARCHAR(255),
	temperature FLOAT,
	timestamputc VARCHAR(255),
	voc INTEGER,
	time INT NOT NULL, --the time of the reading is stored as an INT (unix epoch) and cannot be empty
	FOREIGN KEY (sensorlocation) REFERENCES sensors(sensor_id)
);




