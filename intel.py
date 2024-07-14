import mysql.connector
from mysql.connector import Error
import simpy
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
import geopy.distance
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime, timedelta
from tkinter import simpledialog


mysql_config = {
    'host': 'localhost',
    'user': 'username',
    'password': 'password',
    'database': 'toll_simulation'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**mysql_config)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

def setup_database():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("CREATE DATABASE IF NOT EXISTS toll_simulation")
            conn.database = 'toll_simulation'

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                balance DECIMAL(10, 2) DEFAULT 0.00
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS journeys (
                journey_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                vehicle_id VARCHAR(255),
                start_time DATETIME,
                end_time DATETIME,
                start_point POINT,
                end_point POINT,
                fare DECIMAL(10, 2),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """)

            print("Database and tables created or already exist")
        except Error as e:
            print(f"Error creating database or tables: {e}")
        finally:
            cursor.close()
            conn.close()
    else:
        print("Failed to connect to MySQL server")

vehicles = pd.DataFrame(columns=['id', 'start', 'end'])

class TollSimulationApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Toll Simulation")
        self.geometry("800x600")

        self.create_widgets()
        self.env = simpy.Environment()

    def create_widgets(self):
        self.login_frame = tk.Frame(self)
        self.signup_frame = tk.Frame(self)
        self.main_frame = tk.Frame(self)

        self.show_login()

    def show_login(self):
        self.clear_frames()
        self.login_frame.pack(fill='both', expand=True)

        ttk.Label(self.login_frame, text="Username:").pack(pady=5)
        self.login_username_entry = ttk.Entry(self.login_frame)
        self.login_username_entry.pack()

        ttk.Label(self.login_frame, text="Password:").pack(pady=5)
        self.login_password_entry = ttk.Entry(self.login_frame, show="*")
        self.login_password_entry.pack()

        self.login_button = ttk.Button(self.login_frame, text="Login", command=self.login)
        self.login_button.pack(pady=20)

        self.go_to_signup_button = ttk.Button(self.login_frame, text="Sign Up", command=self.show_signup)
        self.go_to_signup_button.pack()

    def show_signup(self):
        self.clear_frames()
        self.signup_frame.pack(fill='both', expand=True)

        ttk.Label(self.signup_frame, text="Username:").pack(pady=5)
        self.signup_username_entry = ttk.Entry(self.signup_frame)
        self.signup_username_entry.pack()

        ttk.Label(self.signup_frame, text="Password:").pack(pady=5)
        self.signup_password_entry = ttk.Entry(self.signup_frame, show="*")
        self.signup_password_entry.pack()

        self.signup_button = ttk.Button(self.signup_frame, text="Sign Up", command=self.signup)
        self.signup_button.pack(pady=20)

        self.go_to_login_button = ttk.Button(self.signup_frame, text="Back to Login", command=self.show_login)
        self.go_to_login_button.pack()

    def show_main(self):
        self.clear_frames()
        self.main_frame.pack(fill='both', expand=True)

        ttk.Button(self.main_frame, text="View Balance").pack(pady=5)
        ttk.Button(self.main_frame, text="View Trip History").pack(pady=5)

        self.start_simulation_button = ttk.Button(self.main_frame, text="Start Simulation", command=self.start_simulation)
        self.start_simulation_button.pack(pady=20)

        self.canvas = tk.Canvas(self.main_frame, width=200, height=100, bg="white")
        self.canvas.pack()

        self.vehicle_positions = {}

        ttk.Label(self.main_frame, text="Vehicle ID:").pack()
        self.vehicle_id_entry = ttk.Entry(self.main_frame)
        self.vehicle_id_entry.pack()

        ttk.Label(self.main_frame, text="Start Latitude:").pack()
        self.start_latitude_entry = ttk.Entry(self.main_frame)
        self.start_latitude_entry.pack()

        ttk.Label(self.main_frame, text="Start Longitude:").pack()
        self.start_longitude_entry = ttk.Entry(self.main_frame)
        self.start_longitude_entry.pack()

        ttk.Label(self.main_frame, text="End Latitude:").pack()
        self.end_latitude_entry = ttk.Entry(self.main_frame)
        self.end_latitude_entry.pack()

        ttk.Label(self.main_frame, text="End Longitude:").pack()
        self.end_longitude_entry = ttk.Entry(self.main_frame)
        self.end_longitude_entry.pack()

        self.add_vehicle_button = ttk.Button(self.main_frame, text="Add Vehicle", command=self.add_vehicle)
        self.add_vehicle_button.pack(pady=10)

        self.fare_label = ttk.Label(self.main_frame, text="")
        self.fare_label.pack(pady=10)

        self.trip_history_text = scrolledtext.ScrolledText(self.main_frame, width=80, height=10, wrap=tk.WORD)
        self.trip_history_text.pack(pady=10)

    def clear_frames(self):
        for frame in [self.login_frame, self.signup_frame, self.main_frame]:
            frame.pack_forget()

    def signup(self):
        username = self.signup_username_entry.get()
        password = self.signup_password_entry.get()

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
                conn.commit()
                messagebox.showinfo("Sign Up Successful", "You can now log in with your new account.")
                self.show_login()
            except Error as e:
                print(f"Error creating user: {e}")
                messagebox.showerror("Sign Up Failed", "Username already exists. Please choose another.")
            finally:
                cursor.close()
                conn.close()
        else:
            messagebox.showerror("Error", "Failed to connect to the database. Please try again later.")

    def login(self):
        username = self.login_username_entry.get()
        password = self.login_password_entry.get()

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT user_id, balance FROM users WHERE username = %s AND password = %s", (username, password))
                user_record = cursor.fetchone()

                if user_record:
                    self.user_id = user_record[0]
                    self.user_balance = user_record[1]
                    messagebox.showinfo("Login Successful", f"Welcome, {username}!")
                    self.show_main()
                else:
                    messagebox.showerror("Login Failed", "Invalid username or password.")
            except Error as e:
                print(f"Error fetching user details: {e}")
                messagebox.showerror("Error", "Failed to login. Please try again later.")
            finally:
                cursor.close()
                conn.close()
        else:
            messagebox.showerror("Error", "Failed to connect to the database. Please try again later.")

    def add_vehicle(self):
        vehicle_id = self.vehicle_id_entry.get()
        try:
            start_latitude = float(self.start_latitude_entry.get())
            start_longitude = float(self.start_longitude_entry.get())
            end_latitude = float(self.end_latitude_entry.get())
            end_longitude = float(self.end_longitude_entry.get())

            if not (-90 <= start_latitude <= 90 and -180 <= start_longitude <= 180 and -90 <= end_latitude <= 90 and -180 <= end_longitude <= 180):
                raise ValueError("Coordinates out of range")

            start_point = Point(start_latitude, start_longitude)
            end_point = Point(end_latitude, end_longitude)

            global vehicles
            new_vehicle = pd.DataFrame({'id': [vehicle_id], 'start': [start_point], 'end': [end_point]})
            vehicles = pd.concat([vehicles, new_vehicle], ignore_index=True)

            messagebox.showinfo("Success", f"Vehicle {vehicle_id} added successfully!")
            self.add_vehicle_button.config(state=tk.DISABLED)  

        except ValueError:
            messagebox.showerror("Error", "Invalid coordinates. Please enter valid numerical values within the correct ranges.")

    def start_simulation(self):
        self.start_simulation_button.config(state=tk.DISABLED)
        vehicles_list = [Vehicle(self.env, row['id'], row['start'], row['end'], self.update_vehicle_position, self.calculate_fare, self.user_id) for index, row in vehicles.iterrows()]
        
        for vehicle in vehicles_list:
            self.env.process(vehicle.move())

        self.env.run()

        self.display_fare_details()
        self.display_trip_history()

    def update_vehicle_position(self, vehicle_id, position):
        if vehicle_id in self.vehicle_positions:
            self.canvas.coords(self.vehicle_positions[vehicle_id], position.x - 5, position.y - 5, position.x + 5, position.y + 5)
        else:
            self.vehicle_positions[vehicle_id] = self.canvas.create_oval(position.x - 5, position.y - 5, position.x + 5, position.y + 5, fill="blue")

    def calculate_fare(self, vehicle_id, start_time, end_time, start, end):
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                user_id = self.user_id
                total_distance = geopy.distance.distance((start.y, start.x), (end.y, end.x)).km
                normal_fare = total_distance * 0.5
                discounted_fare = normal_fare * 0.5
                vacation_fare = normal_fare * 1.2

                selected_fare = normal_fare

                cursor.execute("""
                SELECT end_time FROM journeys 
                WHERE user_id = %s AND ST_X(start_point) = %s AND ST_Y(start_point) = %s AND ST_X(end_point) = %s AND ST_Y(end_point) = %s
                ORDER BY end_time DESC LIMIT 1
                """, (user_id, end.x, end.y, start.x, start.y))
                last_journey = cursor.fetchone()

                if last_journey and (start_time - last_journey[0]).total_seconds() < 86400:
                    selected_fare = discounted_fare

                if start_time.month in [6, 7, 8]:  
                    selected_fare = vacation_fare

                cursor.execute("UPDATE users SET balance = balance - %s WHERE user_id = %s", (selected_fare, user_id))
                conn.commit()

                cursor.execute("""
                INSERT INTO journeys (user_id, vehicle_id, start_time, end_time, start_point, end_point, fare)
                VALUES (%s, %s, %s, %s, ST_GeomFromText(%s), ST_GeomFromText(%s), %s)
                """, (user_id, vehicle_id, start_time, end_time, start.wkt, end.wkt, selected_fare))
                conn.commit()

                cursor.close()
                conn.close()

                return {
                    'total_distance': total_distance,
                    'normal_fare': normal_fare,
                    'discounted_fare': discounted_fare,
                    'vacation_fare': vacation_fare,
                    'selected_fare': selected_fare
                }

        except ValueError as e:
            print(f"Error processing vehicle {vehicle_id}: {e}")

    def display_fare_details(self):
        self.fare_label.config(text=f"Current Balance: ${self.user_balance:.2f}\n\nFare details displayed here after journey.")

    def display_trip_history(self):
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT start_time, end_time, fare FROM journeys WHERE user_id = %s ORDER BY start_time DESC", (self.user_id,))
                trip_history = cursor.fetchall()
                trip_history_text = ""
                for trip in trip_history:
                    trip_history_text += f"Start Time: {trip[0]}, End Time: {trip[1]}, Fare: ${trip[2]:.2f}\n\n"
                self.trip_history_text.delete(1.0, tk.END)
                self.trip_history_text.insert(tk.INSERT, trip_history_text)
                cursor.close()
                conn.close()
        except Error as e:
            print(f"Error fetching trip history: {e}")
    def view_add_balance(self):
        AddBalanceWindow(self)

    def view_trip_history(self):
        TripHistoryWindow(self)

class Vehicle:
    def __init__(self, env, vehicle_id, start, end, update_position_callback, fare_calculator, user_id):
        self.env = env
        self.id = vehicle_id
        self.start = start
        self.end = end
        self.update_position_callback = update_position_callback
        self.fare_calculator = fare_calculator
        self.user_id = user_id
        self.current_location = self.start

    def move(self):
        try:
            start_time = datetime.now()

            path = LineString([self.start, self.end])
            distance = path.length
            travel_time = distance / 60.0  

            while self.env.now < travel_time:
                yield self.env.timeout(1)
                self.current_location = path.interpolate(self.env.now / travel_time)
                self.update_position_callback(self.id, self.current_location)

            end_time = datetime.now()
            fare_details = self.fare_calculator(self.id, start_time, end_time, self.start, self.end)
            print(f"Fare details for vehicle {self.id}: {fare_details}")

        except ValueError as e:
            print(f"Error processing vehicle {self.id}: {e}")

if __name__ == "__main__":
    setup_database()
    app = TollSimulationApp()
    app.mainloop()

