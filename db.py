import mysql.connector

class db:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '1111',
            'database': 'diplom'
        }
        self.conn = mysql.connector.connect(**self.db_config)
        self.cursor = self.conn.cursor()

    def incert_data(self, relative_humidity, temperature_celsius, red, blue, white):
        insert_data_query = """
        INSERT INTO state (relative_humidity, temperature_celsius, red, blue, white) VALUES (%s, %s, %s, %s, %s)
        """
        data_to_insert = (temperature_celsius, relative_humidity, red, blue, white)
        self.cursor.execute(insert_data_query, data_to_insert)
        self.conn.commit()  
        self.cursor.close()
        self.conn.close()