import psutil
import mysql.connector
import time
import pandas as pd
from db_details import CON_DATA

# CON_DATA = {
#     "host": "localhost",
#     "user": "",
#     "password": "",
#     "database": "mydb",
#     "collation": "utf8mb4_general_ci"
# }

mydb = mysql.connector.connect(**CON_DATA)


mycursor = mydb.cursor(buffered=True)

mycursor.execute(
    "CREATE OR REPLACE TABLE specs"
    "(id int auto_increment, cpu_percent varchar(10), "
    "cpu_frequency_desc varchar(10), cpu_frequency varchar(40), "
    "cpu_loads_avg_desc varchar(10), cpu_loads_avg varchar(40), "
    "memory_usage_desc varchar(10), memory_usage varchar(40), "
    "net_io_desc varchar(20), net_io varchar(40), "
    "temps_desc varchar(10), ssd_temps varchar(10), cpu_temps varchar(10), "
    "fan_label varchar(20), fan_speed varchar(20), "
    "primary key (id))")


psutil.cpu_percent()
init_list = [(None, )] * psutil.cpu_count(logical=True)
mycursor.executemany(
    "INSERT INTO specs (cpu_percent) VALUES (%s)", init_list)


def mem_convert(value):
    if (type(value) is float):
        return round(value, 3)
    else:
        return value // 1024 // 1024
        # bytes // 1024 // 1024 = MB


cpu_frequency_desc = ['current', 'min', 'max']
cpu_loads_avg_desc = ['1_min', '5_min', '15_min']
memory_usage_desc = ['total', 'available', 'percent', 'used']
net_io_desc = ['Mbytes_sent', 'Mbytes_recv', 'packets_sent',
               'packets_recv', 'errin', 'errout', 'dropin', 'dropout']
temps_desc = ['current', 'high', 'critical']


def main():
    percents = []
    freqs = []
    loads = []
    mem = []
    net = []
    temps = []
    fans = []

    time.sleep(3)
    cpu_percent = psutil.cpu_percent(percpu=True)
    cpu_frequency = psutil.cpu_freq()
    cpu_loads_avg = psutil.getloadavg()
    memory_usage = psutil.virtual_memory()
    net_io = psutil.net_io_counters()
    sensors_temps = psutil.sensors_temperatures()
    sensors_fans = psutil.sensors_fans()

    for i in range(len(cpu_percent)):
        percents.append((cpu_percent[i], i + 1))

    for i in range(3):
        freqs.append(
            (cpu_frequency_desc[i], round(cpu_frequency[i], 3), i + 1))
        loads.append((cpu_loads_avg_desc[i],
                      round(cpu_loads_avg[i] /
                            psutil.cpu_count() * 100, 3), i + 1))
        mem.append(
            (memory_usage_desc[i], mem_convert(memory_usage[i]), i + 1))
    mem.append((memory_usage_desc[3], mem_convert(
        memory_usage[0] - memory_usage[1]), 4))

    for i in range(2):
        net.append((net_io_desc[i], mem_convert(net_io[i]), i + 1))
    for i in range(2, 8):
        net.append((net_io_desc[i], net_io[i], i + 1))

    for i in range(3):
        temps.append((temps_desc[i], sensors_temps['nvme'][0][i + 1],
                      sensors_temps['k10temp'][0][i + 1], i + 1))

    for fan_list in sensors_fans.values():
        for id, fan in enumerate(fan_list):
            fans.append((fan.label, fan.current, id + 1))

    mycursor.executemany(
        "UPDATE specs SET cpu_percent=%s WHERE id=%s", percents)
    mycursor.executemany(
        "UPDATE specs SET cpu_frequency_desc=%s, cpu_frequency=%s "
        "WHERE id=%s", freqs)
    mycursor.executemany(
        "UPDATE specs SET cpu_loads_avg_desc=%s, cpu_loads_avg=%s "
        "WHERE id=%s", loads)
    mycursor.executemany(
        "UPDATE specs SET memory_usage_desc=%s, memory_usage=%s "
        "WHERE id=%s", mem)
    mycursor.executemany(
        "UPDATE specs SET net_io_desc=%s, net_io=%s "
        "WHERE id=%s", net)
    mycursor.executemany(
        "UPDATE specs SET temps_desc=%s, ssd_temps=%s, "
        "cpu_temps=%s WHERE id=%s", temps)
    mycursor.executemany(
        "UPDATE specs SET fan_label=%s, fan_speed=%s "
        "WHERE id=%s", fans)

    mycursor.execute("SELECT * FROM specs LIMIT 0")
    column_names = mycursor.column_names

    mycursor.execute("SELECT * FROM specs")
    full_info = []
    for i in mycursor:
        full_info.append(i)

    df = pd.DataFrame.from_records(
        full_info, index=[x[0] for x in full_info], columns=column_names)
    df = df.drop('id', axis=1)
    df['fan_label'] = df['fan_label'].replace('', None)
    print(df.fillna(value="-"), "\n")


if __name__ == '__main__':
    while True:
        try:
            main()
        except KeyboardInterrupt:
            print("\nExiting...")
            break
    print("Exited successfully")
